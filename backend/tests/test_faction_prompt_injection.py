"""Verifies the FACTION ALLEGIANCE + RIVALRY prompt block is injected into
the AI scene state correctly — and that NPCs are TOLD TO PROBE rather than
auto-know affiliation. This is the realism rule the user explicitly asked for.
"""
import sys
sys.path.insert(0, "/app/backend")

from quest_master_ai import QuestMasterAI  # noqa: E402


def _ai():
    return QuestMasterAI()


def test_no_faction_block_when_player_has_no_faction():
    out = _ai()._format_scene_state({"npcs": [], "events": [], "player_faction": None})
    assert "PLAYER FACTION ALLEGIANCE" not in out
    assert "RULES OF PROBING" not in out


def test_faction_block_renders_with_membership():
    state = {
        "npcs": [], "events": [],
        "player_faction": {
            "name": "The Forgemaster's Guild",
            "rank": "officer",
            "motto": "Steel Is Patience Made Sharp",
            "nation_home": "dhor-kuldor",
            "icon": "hammer",
        },
        "faction_rivalries": [],
    }
    out = _ai()._format_scene_state(state)
    assert "PLAYER FACTION ALLEGIANCE" in out
    assert "Forgemaster" in out
    assert "officer" in out
    assert "Steel Is Patience Made Sharp" in out
    # Critical realism rules MUST be in the prompt
    assert "DO NOT magically know" in out
    assert "PROBE" in out or "probe" in out
    assert "where you from" in out.lower() or "what banner" in out.lower()


def test_active_rivalry_renders_and_keeps_probing_first():
    state = {
        "npcs": [], "events": [], "nation": "aigraels",
        "player_faction": {
            "name": "The Forgemaster's Guild",
            "rank": "leader",
            "motto": "Steel Is Patience",
            "nation_home": "dhor-kuldor",
        },
        "faction_rivalries": [
            {
                "name": "The Ardent Legion",
                "nation_home": "aigraels",
                "intensity": 55,
                "status": "escalated",
                "in_their_territory": True,
            },
        ],
    }
    out = _ai()._format_scene_state(state)
    assert "ACTIVE FACTION RIVALRIES" in out
    assert "Ardent Legion" in out
    assert "escalated" in out
    assert "55/100" in out
    assert "HOME TERRITORY" in out
    # Even with escalated rivalry, the AI must STILL be told NPCs do not auto-know
    assert "DO NOT magically know" in out
    # And told that locals here are MORE LIKELY to probe (not auto-attack)
    assert "probe" in out.lower()


def test_dormant_rivalry_is_not_surfaced():
    """Below the declared threshold (25), a rivalry is too cool to make NPCs probe."""
    state = {
        "npcs": [], "events": [],
        "player_faction": {
            "name": "X Guild", "rank": "member", "motto": "", "nation_home": "dhor-kuldor",
        },
        "faction_rivalries": [
            {"name": "Quiet Rival", "nation_home": "aigraels", "intensity": 10, "status": "tense", "in_their_territory": False},
        ],
    }
    out = _ai()._format_scene_state(state)
    assert "Quiet Rival" not in out, "rivalries below intensity 25 should not appear in the prompt"
    # Faction block itself still renders.
    assert "PLAYER FACTION ALLEGIANCE" in out


def test_sworn_enemies_tier_adds_harder_scrutiny_rule():
    state = {
        "npcs": [], "events": [],
        "player_faction": {"name": "A", "rank": "leader", "motto": "", "nation_home": "x"},
        "faction_rivalries": [
            {"name": "B", "nation_home": "y", "intensity": 90, "status": "sworn-enemies", "in_their_territory": False},
        ],
    }
    out = _ai()._format_scene_state(state)
    assert "SWORN-ENEMY" in out
    assert "scrutinise strangers HARDER" in out
    # The HARDER scrutiny clause must STILL say they probe first (no auto-attack)
    sworn_idx = out.find("SWORN-ENEMY")
    tail = out[sworn_idx:sworn_idx + 600]
    assert "probe" in tail.lower() or "do not auto-know" in tail.lower()
