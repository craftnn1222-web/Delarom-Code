"""Tests for the Law / Guard / Jail overhaul (2026-02).

Covers:
- JailService creates a city-scoped jail when none exists, and re-uses an
  existing one when one is already present.
- LawService._refresh_bounty now exposes `has_active_warrant` and
  `petty_count` and escalates correctly.
- LawService.format_record_for_prompt mentions the new physical-touch and
  hostile-first-strike rules.
- LawService.get_bounty_board now surfaces minor crimes (previously hidden).
"""
import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from law_service import (
    LawService,
    WARRANT_TRIGGER_SEVERITIES,
    PETTY_WARRANT_COUNT,
)
from jail_service import (
    ensure_jail_for_city,
    resolve_city_for_location,
    JAIL_LOCATION_TYPE,
)


# ---------------------------------------------------------------------------
# In-memory Mongo stub. We only need find_one / find / insert_one / update_one
# with the small subset of operators the services actually use. Good enough
# for unit tests without spinning up Mongo.
# ---------------------------------------------------------------------------


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, _n):
        return self

    async def to_list(self, _limit=None):
        return list(self._docs)

    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d
        return _gen()


class FakeCollection:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _match(doc, query):
        for k, v in query.items():
            if k == "$or":
                if not any(FakeCollection._match(doc, sub) for sub in v):
                    return False
                continue
            if isinstance(v, dict):
                if "$exists" in v:
                    has = k in doc
                    if v["$exists"] is not has:
                        return False
                if "$in" in v:
                    doc_val = doc.get(k)
                    candidates = v["$in"]
                    if isinstance(doc_val, list):
                        # Mongo semantics: match if any element of doc list
                        # appears in the candidate list.
                        if not any(item in candidates for item in doc_val):
                            return False
                    else:
                        if doc_val not in candidates:
                            return False
                if "$nin" in v:
                    if doc.get(k) in v["$nin"]:
                        return False
                if "$ne" in v:
                    if doc.get(k) == v["$ne"]:
                        return False
                if "$gt" in v:
                    if not (doc.get(k) is not None and doc[k] > v["$gt"]):
                        return False
                if "$gte" in v:
                    if not (doc.get(k) is not None and doc[k] >= v["$gte"]):
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if self._match(d, query):
                return dict(d)
        return None

    def find(self, query, projection=None):
        return FakeCursor([dict(d) for d in self.docs if self._match(d, query)])

    async def count_documents(self, query):
        return sum(1 for d in self.docs if self._match(d, query))

    async def insert_one(self, doc):
        self.docs.append(dict(doc))
        return type("Res", (), {"inserted_id": doc.get("id")})

    async def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._match(d, query):
                self.docs.pop(i)
                return type("Res", (), {"deleted_count": 1})
        return type("Res", (), {"deleted_count": 0})

    async def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._match(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        d.setdefault(k, []).append(v)
                return type("Res", (), {"matched_count": 1, "modified_count": 1})
        if upsert:
            new_doc = {}
            for k, v in query.items():
                if not isinstance(v, dict):
                    new_doc[k] = v
            if "$set" in update:
                new_doc.update(update["$set"])
            self.docs.append(new_doc)
            return type("Res", (), {"matched_count": 0, "modified_count": 0, "upserted_id": "x"})
        return type("Res", (), {"matched_count": 0, "modified_count": 0})


class FakeDB:
    def __init__(self):
        self.crimes = FakeCollection()
        self.bounties = FakeCollection()
        self.imprisonments = FakeCollection()
        self.locations = FakeCollection()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine in a fresh event loop each call so tests don't
    leak across the pytest run."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# JailService
# ---------------------------------------------------------------------------


def test_jail_service_creates_jail_when_missing():
    db = FakeDB()
    jail = _run(ensure_jail_for_city(db, nation="ammeonon", city="astra-lun"))
    assert jail["slug"] == "astra-lun-jail"
    assert jail["location_type"] == JAIL_LOCATION_TYPE
    assert jail["city"] == "astra-lun"
    assert jail["nation"] == "ammeonon"
    assert jail["is_active"] is True
    assert "Jail" in jail["name"]


def test_jail_service_is_idempotent():
    db = FakeDB()
    a = _run(ensure_jail_for_city(db, nation="ammeonon", city="astra-lun"))
    b = _run(ensure_jail_for_city(db, nation="ammeonon", city="astra-lun"))
    assert a["id"] == b["id"]
    assert len(db.locations.docs) == 1


def test_jail_service_nation_fallback():
    db = FakeDB()
    jail = _run(ensure_jail_for_city(db, nation="aigraels", city=None,
                                      fallback_location_slug="wymroost"))
    assert jail["nation"] == "aigraels"
    assert jail["location_type"] == JAIL_LOCATION_TYPE
    assert jail["city"] is None
    # Subsequent call returns the same nation-level prison.
    again = _run(ensure_jail_for_city(db, nation="aigraels", city=None))
    assert again["id"] == jail["id"]


def test_resolve_city_for_location():
    db = FakeDB()
    db.locations.docs.append({
        "nation": "ammeonon", "slug": "market-square", "city": "astra-lun",
    })
    city = _run(resolve_city_for_location(db, nation="ammeonon", location_slug="market-square"))
    assert city == "astra-lun"
    none_city = _run(resolve_city_for_location(db, nation="ammeonon", location_slug="ghost"))
    assert none_city is None


# ---------------------------------------------------------------------------
# Warrant escalation
# ---------------------------------------------------------------------------


def test_minor_crime_triggers_active_warrant():
    """A single minor crime now graduates straight to a warrant (was: major+)."""
    db = FakeDB()
    law = LawService(db)
    _run(law.record_crime(
        character_id="char-1",
        character_name="Test",
        user_id="u1",
        nation="ammeonon",
        location="market-square",
        crime_type="theft",
        severity="minor",
        victim_name="A merchant",
        victim_importance="commoner",
    ))
    bounty = _run(law.get_bounty("char-1", "ammeonon"))
    assert bounty is not None
    assert bounty["has_active_warrant"] is True
    assert bounty["worst_severity"] == "minor"
    assert bounty["petty_count"] == 0


def test_two_petty_crimes_escalates_to_warrant():
    """Two petties = wanted; one petty stays under the threshold."""
    db = FakeDB()
    law = LawService(db)
    _run(law.record_crime(
        character_id="char-2", character_name="Test", user_id="u1",
        nation="ammeonon", location="market", crime_type="pickpocket",
        severity="petty",
    ))
    bounty = _run(law.get_bounty("char-2", "ammeonon"))
    assert bounty["has_active_warrant"] is False
    assert bounty["petty_count"] == 1

    _run(law.record_crime(
        character_id="char-2", character_name="Test", user_id="u1",
        nation="ammeonon", location="market", crime_type="vandalism",
        severity="petty",
    ))
    bounty = _run(law.get_bounty("char-2", "ammeonon"))
    assert bounty["petty_count"] == PETTY_WARRANT_COUNT
    assert bounty["has_active_warrant"] is True


def test_capital_crime_warrant():
    db = FakeDB()
    law = LawService(db)
    _run(law.record_crime(
        character_id="char-3", character_name="Test", user_id="u1",
        nation="ammeonon", location="palace", crime_type="murder",
        severity="capital", victim_name="Noble", victim_importance="noble",
    ))
    bounty = _run(law.get_bounty("char-3", "ammeonon"))
    assert bounty["has_active_warrant"] is True
    assert bounty["worst_severity"] == "capital"


# ---------------------------------------------------------------------------
# Bounty board visibility
# ---------------------------------------------------------------------------


def test_bounty_board_now_includes_minor_crimes():
    """Used to require major+. Now ANY active-warrant character is listed."""
    db = FakeDB()
    law = LawService(db)
    _run(law.record_crime(
        character_id="hunted-1", character_name="Thief", user_id="u1",
        nation="ammeonon", location="market", crime_type="theft",
        severity="minor",
    ))
    board = _run(law.get_bounty_board(nation="ammeonon"))
    assert any(b.get("perpetrator_id") == "hunted-1" for b in board)


def test_bounty_board_excludes_lone_petty():
    db = FakeDB()
    law = LawService(db)
    _run(law.record_crime(
        character_id="hunted-2", character_name="Crook", user_id="u1",
        nation="ammeonon", location="market", crime_type="loiter",
        severity="petty",
    ))
    board = _run(law.get_bounty_board(nation="ammeonon"))
    assert all(b.get("perpetrator_id") != "hunted-2" for b in board)


# ---------------------------------------------------------------------------
# Prompt block: physical-touch + hostile first-strike rules
# ---------------------------------------------------------------------------


def test_prompt_block_mentions_touch_rule_clean_record():
    txt = LawService.format_record_for_prompt([], None)
    assert "PHYSICAL-TOUCH" in txt.upper()
    # Even a clean character must trigger arrest if they grab a guard.
    assert "GUARD" in txt.upper()


def test_prompt_block_mentions_first_strike_rule():
    crime = {
        "id": "c1", "severity": "minor", "crime_type": "assault",
        "victim_name": "Watchman", "victim_importance": "notable",
        "description": "Shoved a guard", "bounty": 50,
    }
    bounty = {"total_bounty": 50, "worst_severity": "minor",
              "has_active_warrant": True}
    txt = LawService.format_record_for_prompt([crime], bounty)
    assert "PHYSICAL-TOUCH" in txt.upper()
    assert "HOSTILE" in txt.upper()
    assert "FIRST-STRIKE" in txt.upper() or "FIRST STRIKE" in txt.upper()
    assert "ACTIVE WARRANT: YES" in txt.upper()


def test_warrant_trigger_severities_are_broadened():
    """Regression guard — keep the threshold inclusive of `minor`."""
    assert "minor" in WARRANT_TRIGGER_SEVERITIES
    assert "major" in WARRANT_TRIGGER_SEVERITIES
    assert "petty" not in WARRANT_TRIGGER_SEVERITIES  # petty needs the count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
