"""
Whispered Rumors (Phase 5, 2026-05-30).

Players plant rumors about characters or NPCs. The AI judges each rumor
as true / partly-true / false based on world state context. Active rumors
are scoped per nation, expire after 7 days, and are injected into the
Quest Master scene prompt so NPCs may reference them ("they say the
miller's daughter has been seen at the docks at midnight…").
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage


JUDGEMENTS = {"true", "partly-true", "false"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _judge_rumor(
    rumor_text: str,
    subject_kind: str,
    subject_data: Dict,
) -> Dict:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"judgement": "false", "note": "(no oracle available)"}

    bio = subject_data.get("backstory") or subject_data.get("personality") or ""
    motivation = subject_data.get("motivation") or ""
    public_facts = {
        "name": subject_data.get("name", "?"),
        "race": subject_data.get("race", ""),
        "nation": subject_data.get("nation", ""),
        "bio_excerpt": bio[:400],
        "motivation_excerpt": motivation[:200],
    }
    system = (
        "You are the World's Truth — a quiet observer who knows what really is. "
        "Given public facts about a subject and a rumor someone is spreading, "
        "you classify the rumor as one of three labels EXACTLY: true | partly-true | false. "
        "Be lenient on poetic licence and tone. Be strict on factual claims. "
        "Output ONLY the label, on its own line, followed by a 1-sentence note explaining "
        "your reasoning. Format strictly:\n"
        "LABEL: <true|partly-true|false>\nNOTE: <one sentence>"
    )
    prompt = (
        f"SUBJECT KIND: {subject_kind}\n"
        f"SUBJECT FACTS (public knowledge):\n"
        f"  name: {public_facts['name']}\n"
        f"  race: {public_facts['race']}\n"
        f"  nation: {public_facts['nation']}\n"
        f"  bio: {public_facts['bio_excerpt']}\n"
        f"  motivation: {public_facts['motivation_excerpt']}\n\n"
        f"RUMOR BEING SPREAD: \"{rumor_text}\"\n\n"
        "Judge: how true is this rumor against what is publicly known?"
    )
    chat = LlmChat(
        api_key=api_key,
        session_id=f"rumor-{uuid.uuid4()}",
        system_message=system,
    ).with_model("openai", "gpt-4o")
    try:
        raw = (await chat.send_message(UserMessage(text=prompt))).strip()
    except Exception:
        return {"judgement": "false", "note": "(the oracle is unsure)"}

    label = "false"
    note = ""
    for line in raw.splitlines():
        s = line.strip()
        upper = s.upper()
        if upper.startswith("LABEL:"):
            val = s.split(":", 1)[1].strip().lower().replace(" ", "-")
            if val in JUDGEMENTS:
                label = val
        elif upper.startswith("NOTE:"):
            note = s.split(":", 1)[1].strip()
    return {"judgement": label, "note": note}


class RumorPlant(BaseModel):
    planter_character_id: str
    nation: str = Field(min_length=2, max_length=60)
    subject_kind: str = Field(description="'character' or 'npc'")
    subject_id: str
    text: str = Field(min_length=10, max_length=400, description="The rumor being whispered.")


def attach_rumor_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    resolve_character_for_user,
):
    @api_router.post("/rumors")
    async def plant_rumor(
        payload: RumorPlant,
        current_user: User = Depends(get_current_user),
    ):
        """Plant a whispered rumor about a target character or NPC. The AI
        will privately label the rumor true / partly-true / false at the
        moment it is sown — but the label is HIDDEN from the public listing.
        Only the planter and admin can see it. The world will spread it
        anyway."""
        planter = await resolve_character_for_user(payload.planter_character_id, current_user)
        if payload.subject_kind not in ("character", "npc"):
            raise HTTPException(status_code=400, detail="subject_kind must be 'character' or 'npc'")
        if payload.subject_kind == "character":
            subject = await db.characters.find_one({"id": payload.subject_id}, {"_id": 0})
            if subject and subject["id"] == planter["id"]:
                raise HTTPException(status_code=400, detail="You cannot start a rumor about yourself")
        else:
            subject = await db.npcs.find_one({"id": payload.subject_id}, {"_id": 0})
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        # Rate limit: 5 rumors per character per real-world day
        since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        recent = await db.rumors.count_documents({
            "planter_character_id": planter["id"],
            "planted_at": {"$gte": since},
        })
        if recent >= 5:
            raise HTTPException(status_code=429, detail="Your character has whispered too many rumors today. The taverns need a rest.")

        verdict = await _judge_rumor(payload.text, payload.subject_kind, subject)
        now = datetime.now(timezone.utc)
        doc = {
            "id": str(uuid.uuid4()),
            "planter_character_id": planter["id"],
            "planter_character_name": planter.get("name", "Unknown"),
            "planter_user_id": current_user.id,
            "subject_kind": payload.subject_kind,
            "subject_id": payload.subject_id,
            "subject_name": subject.get("name", "?"),
            "nation": payload.nation,
            "text": payload.text,
            "judgement": verdict.get("judgement", "false"),
            "judgement_note": verdict.get("note", ""),
            "planted_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
        }
        await db.rumors.insert_one(doc)
        doc.pop("_id", None)
        # Return WITHOUT the judgement to enforce that even the planter can't be 100% sure.
        # Their UI gets it via the /mine endpoint instead.
        public_view = {k: v for k, v in doc.items() if k not in ("judgement", "judgement_note")}
        return public_view

    @api_router.get("/rumors")
    async def list_active_rumors(
        nation: Optional[str] = None,
        subject_id: Optional[str] = None,
        limit: int = 50,
    ):
        """Public — list currently-active rumors. Judgement labels are NOT included."""
        now_iso = _now_iso()
        q: Dict = {"expires_at": {"$gt": now_iso}}
        if nation:
            q["nation"] = nation
        if subject_id:
            q["subject_id"] = subject_id
        cursor = db.rumors.find(q, {"_id": 0, "judgement": 0, "judgement_note": 0}).sort("planted_at", -1)
        return await cursor.to_list(min(max(limit, 1), 200))

    @api_router.get("/characters/{character_id}/rumors/mine")
    async def list_my_rumors(
        character_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Rumors planted by THIS character. The judgement label is included
        so the planter knows whether their gossip is true, half-true, or a lie."""
        await resolve_character_for_user(character_id, current_user)
        cursor = db.rumors.find(
            {"planter_character_id": character_id},
            {"_id": 0},
        ).sort("planted_at", -1)
        return await cursor.to_list(200)
