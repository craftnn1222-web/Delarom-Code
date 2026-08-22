"""
Ballads & Folk Tales (Phase 3, 2026-05-30).

Players commission short, AI-generated ballads about dramatic in-world
events. Each ballad is attributed to a fictional bard and tagged with
the characters and nations involved, so they can be browsed and quoted
by NPCs later.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage


BARDS = [
    "Old Calenwyn the Hollow-Eyed",
    "Mistress Vellareth of the Salt Coast",
    "Wandering Iorin",
    "The Veiled Singer of Aigraels",
    "Brunn Two-Strings",
    "Lady Aedra of the Quill",
    "The Stranger Who Came At Dusk",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pick_bard() -> str:
    # Deterministic but varied — uses microsecond mod len(BARDS).
    return BARDS[datetime.now(timezone.utc).microsecond % len(BARDS)]


class BalladCommission(BaseModel):
    character_id: str
    title_hint: Optional[str] = Field(default="", max_length=120)
    event_summary: str = Field(min_length=10, max_length=1000)
    tone: Optional[str] = Field(default="heroic", description="heroic / tragic / mocking / sombre / haunting")
    nation: Optional[str] = ""


async def _generate_ballad(commission: BalladCommission, character_name: str) -> Dict:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Bardic services are unavailable.")

    bard = _pick_bard()
    system = (
        "You are a court bard of Delarom, a high-fantasy world. You compose short, "
        "evocative ballads about heroic, tragic, mocking, sombre, or haunting events. "
        "Your style is reminiscent of Tolkien, Le Guin, and traditional English "
        "folk-balladry. Output ONLY the ballad text — no preamble, no commentary."
    )
    prompt = (
        f"Compose a ballad titled appropriately for the event below. "
        f"You will be paid for ONE ballad of 3-6 short rhyming stanzas of 4 lines each. "
        f"Then on a NEW line below the ballad write 'TITLE: <your title>'.\n\n"
        f"Subject character: {character_name}\n"
        f"Nation: {commission.nation or 'unspecified'}\n"
        f"Tone: {commission.tone or 'heroic'}\n"
        f"Title hint (optional, ignore if unsuitable): {commission.title_hint or '(none)'}\n\n"
        f"EVENT TO BE SUNG OF:\n{commission.event_summary}\n\n"
        f"Remember: ONLY the ballad text, then a single 'TITLE: …' line. No quotes, no narration about yourself."
    )

    chat = LlmChat(
        api_key=api_key,
        session_id=f"ballad-{uuid.uuid4()}",
        system_message=system,
    ).with_model("openai", "gpt-4o")

    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bardic AI failed: {e}")

    # Split out title.
    lines = [ln.rstrip() for ln in raw.strip().splitlines()]
    title = commission.title_hint or "Untitled"
    body_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("TITLE:"):
            title = stripped.split(":", 1)[1].strip().strip('"').strip("'") or title
        else:
            body_lines.append(line)
    # Trim trailing blank lines
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    body = "\n".join(body_lines).strip() or raw.strip()

    return {"bard": bard, "title": title, "body": body}


def attach_ballad_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    require_admin,
    resolve_character_for_user,
):
    @api_router.get("/ballads")
    async def list_ballads(
        character_id: Optional[str] = None,
        nation: Optional[str] = None,
        limit: int = 50,
    ):
        """Public — anyone can browse the bardic record."""
        q: Dict = {}
        if character_id:
            q["subject_character_id"] = character_id
        if nation:
            q["nation"] = nation
        cursor = db.ballads.find(q, {"_id": 0}).sort("composed_at", -1)
        return await cursor.to_list(min(max(limit, 1), 200))

    @api_router.get("/ballads/{ballad_id}")
    async def get_ballad(ballad_id: str):
        ballad = await db.ballads.find_one({"id": ballad_id}, {"_id": 0})
        if not ballad:
            raise HTTPException(status_code=404, detail="Ballad not found")
        return ballad

    @api_router.post("/ballads/commission")
    async def commission_ballad(
        payload: BalladCommission,
        current_user: User = Depends(get_current_user),
    ):
        """Pay a bard to immortalise a moment from your character's history.

        Caller must own the subject character. The AI generates a short ballad
        in the requested tone and stores it permanently in the bardic record.
        """
        char = await resolve_character_for_user(payload.character_id, current_user)
        # Rough rate-limit: max 10 ballads per character per day. Cheap but effective.
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        recent = await db.ballads.count_documents({
            "subject_character_id": payload.character_id,
            "composed_at": {"$gte": since},
        })
        if recent >= 10:
            raise HTTPException(status_code=429, detail="Your character has commissioned too many ballads today. Try tomorrow.")

        generated = await _generate_ballad(payload, char.get("name", "an unknown soul"))

        doc = {
            "id": str(uuid.uuid4()),
            "title": generated["title"],
            "body": generated["body"],
            "bard": generated["bard"],
            "subject_character_id": char["id"],
            "subject_character_name": char.get("name", "Unknown"),
            "commissioned_by_user_id": current_user.id,
            "tone": payload.tone or "heroic",
            "nation": payload.nation or char.get("nation", ""),
            "composed_at": _now_iso(),
        }
        await db.ballads.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @api_router.delete("/admin/ballads/{ballad_id}")
    async def admin_delete_ballad(ballad_id: str, admin: User = Depends(require_admin)):
        result = await db.ballads.delete_one({"id": ballad_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Ballad not found")
        return {"ok": True}
