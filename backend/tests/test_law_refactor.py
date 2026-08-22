"""Direct unit test for the law_service.record_crime refactor.

Verifies that both the character and NPC perpetrator paths produce a
correctly-shaped crime document (post-refactor: _resolve_perpetrator +
_build_crime_doc helpers).
"""
import asyncio
import os
import uuid

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from law_service import LawService


@pytest.fixture
def db():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name]


@pytest.fixture
def svc(db):
    return LawService(db)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# Test _resolve_perpetrator helper directly
class TestResolvePerpetrator:
    def test_character_default(self):
        t, pid, name = LawService._resolve_perpetrator(
            "character", None, "", "char-123", "Hero"
        )
        assert t == "character"
        assert pid == "char-123"
        assert name == "Hero"

    def test_character_explicit_id_overrides(self):
        t, pid, name = LawService._resolve_perpetrator(
            "character", "explicit-id", "Custom", "char-123", "Hero"
        )
        assert t == "character"
        assert pid == "explicit-id"
        assert name == "Custom"

    def test_npc_path(self):
        t, pid, name = LawService._resolve_perpetrator(
            "npc", "npc-7", "Goblin", None, ""
        )
        assert t == "npc"
        assert pid == "npc-7"
        assert name == "Goblin"

    def test_npc_missing_id_raises(self):
        with pytest.raises(ValueError):
            LawService._resolve_perpetrator("npc", None, "X", None, "")

    def test_character_missing_id_raises(self):
        with pytest.raises(ValueError):
            LawService._resolve_perpetrator("character", None, "", None, "")


# Test _build_crime_doc shape
class TestBuildCrimeDoc:
    def test_character_doc_shape(self):
        doc = LawService._build_crime_doc(
            perpetrator_type="character",
            perp_id="c1",
            perp_name="Hero",
            character_id="c1",
            character_name="Hero",
            user_id="u1",
            nation="ammeonon",
            location="wymroost",
            crime_type="theft",
            severity="minor",
            victim_name="Merchant",
            victim_importance="commoner",
            description="stole bread",
            bounty_amount=125,
        )
        # Required keys
        for k in ("id", "perpetrator_type", "perpetrator_id", "perpetrator_name",
                  "character_id", "character_name", "user_id", "nation",
                  "location", "crime_type", "severity", "victim_name",
                  "victim_importance", "description", "bounty", "status",
                  "created_at", "resolved_at", "resolved_reason"):
            assert k in doc, f"missing {k}"
        assert doc["perpetrator_type"] == "character"
        assert doc["character_id"] == "c1"
        assert doc["character_name"] == "Hero"
        assert doc["status"] == "open"
        assert doc["bounty"] == 125

    def test_npc_doc_shape(self):
        doc = LawService._build_crime_doc(
            perpetrator_type="npc",
            perp_id="npc-9",
            perp_name="Brigand",
            character_id=None,
            character_name="",
            user_id=None,
            nation="ammeonon",
            location="wymroost",
            crime_type="murder",
            severity="capital",
            victim_name="Lord X",
            victim_importance="noble",
            description="killed lord",
            bounty_amount=75000,
        )
        # For NPC perpetrators, character_* must be cleared
        assert doc["perpetrator_type"] == "npc"
        assert doc["perpetrator_id"] == "npc-9"
        assert doc["character_id"] is None
        assert doc["character_name"] == ""
        assert doc["status"] == "open"


# Integration test: record_crime end-to-end against mongo
class TestRecordCrimeIntegration:
    def test_character_crime_persists(self, svc):
        asyncio.run(self._character_crime_persists(svc))

    async def _character_crime_persists(self, svc):
        cid = f"TEST_char_{uuid.uuid4().hex[:6]}"
        doc = await svc.record_crime(
            character_id=cid,
            character_name="TestHero",
            user_id="TEST_user",
            nation="TEST_nation",
            location="TEST_loc",
            crime_type="theft",
            severity="minor",
            victim_name="V",
            victim_importance="commoner",
            description="TEST",
        )
        assert doc["perpetrator_type"] == "character"
        assert doc["perpetrator_id"] == cid
        assert doc["character_id"] == cid
        # Verify persisted
        fetched = await svc.crimes.find_one({"id": doc["id"]}, {"_id": 0})
        assert fetched is not None
        assert fetched["character_name"] == "TestHero"
        # Cleanup
        await svc.crimes.delete_one({"id": doc["id"]})
        await svc.bounties.delete_one(
            {"perpetrator_type": "character", "perpetrator_id": cid, "nation": "TEST_nation"}
        )

    def test_npc_crime_persists(self, svc):
        asyncio.run(self._npc_crime_persists(svc))

    async def _npc_crime_persists(self, svc):
        npc_id = f"TEST_npc_{uuid.uuid4().hex[:6]}"
        doc = await svc.record_crime(
            nation="TEST_nation",
            location="TEST_loc",
            crime_type="murder",
            severity="capital",
            victim_name="V",
            victim_importance="noble",
            description="TEST",
            perpetrator_type="npc",
            perpetrator_id=npc_id,
            perpetrator_name="Goblin",
        )
        assert doc["perpetrator_type"] == "npc"
        assert doc["perpetrator_id"] == npc_id
        assert doc["character_id"] is None
        fetched = await svc.crimes.find_one({"id": doc["id"]}, {"_id": 0})
        assert fetched is not None
        await svc.crimes.delete_one({"id": doc["id"]})
        await svc.bounties.delete_one(
            {"perpetrator_type": "npc", "perpetrator_id": npc_id, "nation": "TEST_nation"}
        )
