"""Tests for the Courtroom / Trial system.

Covers:
- ensure_courthouse_for_city creates / re-uses courthouse locations.
- ensure_judge_and_prosecutor creates persistent NPCs once per courthouse.
- CourtroomService.start_trial / append_defence_turn / finalize_trial flow.
- gather_victim_witnesses pulls named victims from open crimes.
- _baseline_sentence_for_crimes mirrors the magistrate's old logic.
- Leniency clamp at +/- 100.
"""
import os
import sys
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from courtroom_service import (
    CourtroomService,
    ensure_courthouse_for_city,
    ensure_judge_and_prosecutor,
    gather_victim_witnesses,
    _baseline_sentence_for_crimes,
    COURTHOUSE_LOCATION_TYPE,
    MAX_DEFENCE_TURNS,
)


# ---------------------------------------------------------------------------
# Re-use the same FakeDB stub from the law-jail overhaul test (subset of Mongo).
# ---------------------------------------------------------------------------
from tests.test_law_jail_overhaul import FakeDB, _run  # noqa: E402


# ---------------------------------------------------------------------------
# Courthouse location
# ---------------------------------------------------------------------------


def test_courthouse_created_when_missing():
    db = FakeDB()
    ch = _run(ensure_courthouse_for_city(db, nation="ammeonon", city="astra-lun"))
    assert ch["slug"] == "astra-lun-courthouse"
    assert ch["location_type"] == COURTHOUSE_LOCATION_TYPE
    assert ch["city"] == "astra-lun"
    assert ch["nation"] == "ammeonon"


def test_courthouse_is_idempotent():
    db = FakeDB()
    a = _run(ensure_courthouse_for_city(db, nation="ammeonon", city="astra-lun"))
    b = _run(ensure_courthouse_for_city(db, nation="ammeonon", city="astra-lun"))
    assert a["id"] == b["id"]
    assert len(db.locations.docs) == 1


def test_courthouse_nation_fallback():
    db = FakeDB()
    ch = _run(ensure_courthouse_for_city(db, nation="aigraels", city=None,
                                          fallback_location_slug="wymroost"))
    assert ch["nation"] == "aigraels"
    assert ch["location_type"] == COURTHOUSE_LOCATION_TYPE
    assert ch["city"] is None


# ---------------------------------------------------------------------------
# Court NPCs
# ---------------------------------------------------------------------------


def test_judge_and_prosecutor_created_once():
    db = FakeDB()
    db.npcs = type(db.locations)()  # FakeCollection
    ch = _run(ensure_courthouse_for_city(db, nation="ammeonon", city="astra-lun"))
    npcs = _run(ensure_judge_and_prosecutor(
        db, nation="ammeonon", courthouse_slug=ch["slug"], city="astra-lun"
    ))
    assert "judge" in npcs and "prosecutor" in npcs
    assert npcs["judge"]["role"] == "judge"
    assert npcs["prosecutor"]["role"] == "prosecutor"
    assert "Astra Lun" in npcs["judge"]["name"]
    assert npcs["judge"]["nation"] == "ammeonon"
    assert npcs["judge"]["location"] == ch["slug"]
    # Idempotent
    again = _run(ensure_judge_and_prosecutor(
        db, nation="ammeonon", courthouse_slug=ch["slug"], city="astra-lun"
    ))
    assert again["judge"]["id"] == npcs["judge"]["id"]
    assert again["prosecutor"]["id"] == npcs["prosecutor"]["id"]
    assert len(db.npcs.docs) == 2


# ---------------------------------------------------------------------------
# Witness gathering
# ---------------------------------------------------------------------------


def test_gather_witnesses_deduplicates_by_name():
    db = FakeDB()
    db.npcs = type(db.locations)()
    db.npcs.docs.append({
        "id": "n1", "name": "Captain Aldric", "race": "Human",
        "nation": "ammeonon", "personality": "Stoic", "importance": "notable",
    })
    crimes = [
        {"victim_name": "Captain Aldric", "victim_importance": "notable",
         "nation": "ammeonon", "crime_type": "assault", "severity": "minor"},
        {"victim_name": "Captain Aldric", "victim_importance": "notable",
         "nation": "ammeonon", "crime_type": "intimidation", "severity": "petty"},
        {"victim_name": "", "victim_importance": "commoner",
         "nation": "ammeonon", "crime_type": "vagrancy", "severity": "petty"},
    ]
    witnesses = _run(gather_victim_witnesses(db, open_crimes=crimes))
    assert len(witnesses) == 1  # deduped
    w = witnesses[0]
    assert w["name"] == "Captain Aldric"
    assert w["npc_id"] == "n1"
    assert w["personality"] == "Stoic"


def test_gather_witnesses_handles_unknown_victims():
    db = FakeDB()
    db.npcs = type(db.locations)()
    crimes = [
        {"victim_name": "Unnamed Smith", "victim_importance": "commoner",
         "nation": "ammeonon", "crime_type": "theft", "severity": "minor"},
    ]
    w = _run(gather_victim_witnesses(db, open_crimes=crimes))
    assert len(w) == 1
    assert w[0]["name"] == "Unnamed Smith"
    assert w[0]["npc_id"] is None  # no matching NPC in db


# ---------------------------------------------------------------------------
# Baseline sentencing
# ---------------------------------------------------------------------------


def test_baseline_sentence_petty():
    s = _baseline_sentence_for_crimes([{"severity": "petty"}])
    assert s["sentence_type"] == "fine"


def test_baseline_sentence_minor():
    s = _baseline_sentence_for_crimes([{"severity": "minor"}])
    assert s["sentence_type"] == "imprison"
    assert s["imprison_turns"] == 3


def test_baseline_sentence_major():
    s = _baseline_sentence_for_crimes([{"severity": "major"}])
    assert s["imprison_turns"] == 10


def test_baseline_sentence_regicide_executes():
    s = _baseline_sentence_for_crimes([{"severity": "regicide"}])
    assert s["sentence_type"] == "execute"


def test_baseline_sentence_picks_worst():
    s = _baseline_sentence_for_crimes([{"severity": "petty"}, {"severity": "major"}])
    assert s["sentence_type"] == "imprison"
    assert s["imprison_turns"] == 10


# ---------------------------------------------------------------------------
# CourtroomService trial state
# ---------------------------------------------------------------------------


def _seed_trial(crt):
    return _run(crt.start_trial(
        character_id="char-1",
        character_name="Test",
        user_id="u1",
        nation="ammeonon",
        origin_location="market-square",
        courthouse_location="astra-lun-courthouse",
        city="astra-lun",
        crime_ids=["c1"],
        open_crimes_snapshot=[{"id": "c1", "severity": "minor", "crime_type": "theft"}],
        judge_npc_id="j1",
        prosecutor_npc_id="p1",
        victim_npc_ids=["w1"],
        total_bounty=100,
    ))


def test_start_trial_is_idempotent_for_active_trial():
    db = FakeDB()
    db.trials = type(db.locations)()
    crt = CourtroomService(db)
    t1 = _seed_trial(crt)
    t2 = _seed_trial(crt)
    assert t1["id"] == t2["id"]


def test_append_defence_updates_leniency_and_turns():
    db = FakeDB()
    db.trials = type(db.locations)()
    crt = CourtroomService(db)
    trial = _seed_trial(crt)
    updated = _run(crt.append_defence_turn(
        trial["id"], defence_text="I am innocent", ai_narration="The court listens.",
        leniency_delta=15, judge_remark="A bold claim.", judge_cut_off=False,
    ))
    assert updated["defense_turns_used"] == 1
    assert updated["leniency_score"] == 15
    assert len(updated["defense_history"]) == 1
    assert updated["defense_history"][0]["defence_text"] == "I am innocent"


def test_leniency_clamps_at_100():
    db = FakeDB()
    db.trials = type(db.locations)()
    crt = CourtroomService(db)
    trial = _seed_trial(crt)
    # 5 turns of +25 each = +125 raw, clamp to +100
    for _ in range(5):
        trial = _run(crt.append_defence_turn(
            trial["id"], defence_text="bribe", ai_narration="ok",
            leniency_delta=25,
        ))
    assert trial["leniency_score"] == 100


def test_leniency_clamps_at_minus_100():
    db = FakeDB()
    db.trials = type(db.locations)()
    crt = CourtroomService(db)
    trial = _seed_trial(crt)
    for _ in range(5):
        trial = _run(crt.append_defence_turn(
            trial["id"], defence_text="insult", ai_narration="ok",
            leniency_delta=-25,
        ))
    assert trial["leniency_score"] == -100


def test_finalize_trial_sets_verdict_and_status():
    db = FakeDB()
    db.trials = type(db.locations)()
    crt = CourtroomService(db)
    trial = _seed_trial(crt)
    verdict = {
        "sentence_type": "imprison", "imprison_turns": 3,
        "verdict_summary": "Guilty of theft.",
    }
    final = _run(crt.finalize_trial(trial["id"], verdict=verdict))
    assert final["status"] == "verdict_delivered"
    assert final["verdict"]["sentence_type"] == "imprison"
    assert final["ended_at"] is not None


def test_get_active_trial_excludes_finalized():
    db = FakeDB()
    db.trials = type(db.locations)()
    crt = CourtroomService(db)
    trial = _seed_trial(crt)
    _run(crt.finalize_trial(trial["id"], verdict={"sentence_type": "fine"}))
    none_active = _run(crt.get_active_trial("char-1"))
    assert none_active is None


def test_max_defence_turns_constant_is_5():
    assert MAX_DEFENCE_TURNS == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
