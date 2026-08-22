"""
Wanted Posters (Phase 5, 2026-05-30).

For each open bounty on the Bounty Board, players may commission an
AI-generated WANTED poster. The image is generated once via Gemini /
OpenAI gpt-image-1, stored on disk via ImageService, and cached on the
bounty document. Subsequent requests serve the cached image.
"""
import os
import uuid
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException


def _build_poster_prompt(
    *,
    subject_name: str,
    subject_kind: str,  # "npc" or "character"
    crime_label: str,
    nation: str,
    appearance: str = "",
    race: str = "",
) -> str:
    """Construct the image-gen prompt for a WANTED poster."""
    parts = [
        "A weathered medieval fantasy WANTED poster, parchment background with torn edges,",
        "prominent block-letter heading 'WANTED' at the top in faux-medieval script,",
        f"a central detailed ink-and-wash portrait sketch of {subject_name},",
    ]
    if race:
        parts.append(f"a {race},")
    if appearance:
        parts.append(f"appearance: {appearance[:200]},")
    parts.extend([
        f"subject's name beneath the portrait reading '{subject_name}',",
        f"a short charge line below reading 'For {crime_label[:80]}',",
        f"the bottom shows a faux royal sigil and the nation name '{nation}',",
        "muted aged-paper colour palette, candlelight ambiance,",
        "high-fantasy realism, brush-and-quill illustration style,",
        "no modern fonts, no QR codes, no out-of-period elements.",
    ])
    return " ".join(parts)


async def _generate_poster_image(prompt: str) -> bytes:
    """Call the configured image gen service and return raw image bytes."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="The herald's printers are silent.")
    images = None
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
        gen = OpenAIImageGeneration(api_key=api_key)
        images = await gen.generate_images(
            prompt=prompt,
            model="gpt-image-1",
            number_of_images=1,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image service error: {e}") from e
    if not images:
        raise HTTPException(status_code=502, detail="No poster image returned")
    return images[0]


def attach_wanted_poster_routes(
    api_router: APIRouter,
    *,
    db,
    User,
    get_current_user,
    logger,
):
    @api_router.post("/bounties/{bounty_id}/poster")
    async def commission_poster(
        bounty_id: str,
        current_user: User = Depends(get_current_user),
    ):
        """Generate (or return cached) WANTED poster image for a bounty.

        Public bounty board → any logged-in user may commission. Costs one
        image generation per unique bounty (cached on the bounty doc).
        """
        bounty = await db.bounties.find_one({"id": bounty_id}, {"_id": 0})
        if not bounty:
            raise HTTPException(status_code=404, detail="Bounty not found")
        if bounty.get("poster_image_id"):
            return {
                "ok": True,
                "image_id": bounty["poster_image_id"],
                "image_url": f"/api/image/{bounty['poster_image_id']}",
                "cached": True,
            }

        # Pull subject details
        subject_kind = bounty.get("perpetrator_type", "character")
        subject_id = bounty.get("perpetrator_id")
        subject_name = bounty.get("perpetrator_name", "Unknown Soul")
        race = ""
        appearance = ""
        if subject_kind == "npc" and subject_id:
            subject = await db.npcs.find_one({"id": subject_id}, {"_id": 0})
        else:
            subject = await db.characters.find_one({"id": subject_id}, {"_id": 0})
        if subject:
            race = subject.get("race", "") or ""
            appearance = subject.get("appearance", "") or ""
            subject_name = subject.get("name", subject_name) or subject_name

        crime_label = bounty.get("worst_severity") or "crimes against the realm"
        prompt = _build_poster_prompt(
            subject_name=subject_name,
            subject_kind=subject_kind,
            crime_label=crime_label,
            nation=bounty.get("nation", ""),
            race=race,
            appearance=appearance,
        )

        try:
            raw = await _generate_poster_image(prompt)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Wanted poster gen failed: {e}")
            raise HTTPException(status_code=502, detail=f"Poster generation failed: {e}")

        from image_service import ImageService
        img_service = ImageService(db)
        image_id = await img_service.store_bytes(raw, mime_type="image/png")
        await db.bounties.update_one(
            {"id": bounty_id},
            {"$set": {"poster_image_id": image_id}},
        )
        return {
            "ok": True,
            "image_id": image_id,
            "image_url": f"/api/image/{image_id}",
            "cached": False,
        }

    @api_router.get("/bounties/{bounty_id}/poster")
    async def get_poster(bounty_id: str):
        """Public — fetch the existing poster (no generation). Returns 404 if none yet."""
        bounty = await db.bounties.find_one({"id": bounty_id}, {"_id": 0, "poster_image_id": 1})
        if not bounty or not bounty.get("poster_image_id"):
            raise HTTPException(status_code=404, detail="No poster yet for this bounty")
        return {
            "image_id": bounty["poster_image_id"],
            "image_url": f"/api/image/{bounty['poster_image_id']}",
        }
