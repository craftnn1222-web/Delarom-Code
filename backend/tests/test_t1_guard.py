"""Tests for the T1 player-puppeteering guard."""
from t1_guard import detect_player_puppeteering, sanitize_player_puppeteering


# Real-world example from the user-reported regression. The AI played Ausar
# (the player's character) — every sentence below is a T1 violation and the
# guard must catch all of them.
USER_REGRESSION_TEXT = """
At the carriage, Ausar steps out, a familiar gentle smile creasing his features, his presence calm yet commanding in the soft glow of the torches.
Behind him, Orion follows, grinning broadly at Alee's eager reception.
As Ausar approaches, his voice contains a warm timbre. "Alee, it's always good to see your enthusiasm untempered."
He gaze shifts to Orion for a moment, an unspoken camaraderie passing between them.
"Perhaps there are treasures yet to be discovered in our tales from the journey."
The night air carries a cool touch, a gentle reminder of the time's advance.
The estate stands as an island of light and warmth amidst the darkened landscape.
""".strip()


# A clean response — only NPCs and environment, never names Ausar as subject.
CLEAN_RESPONSE = """
Orion lingers at the threshold, his grin slow to fade as Alee bounds toward the carriage.
Behind him, Arwen the apprentice mage emerges blinking into the torchlight, eyes wide at the estate's grandeur.
A distant seagull calls; the trees whisper.
Sophie's tail wiggles, eager for the night's tales.
What do you do?
""".strip()


def test_detects_action_subject_violation():
    """`Ausar steps out`, `As Ausar approaches`, etc. should be flagged."""
    flagged = detect_player_puppeteering(USER_REGRESSION_TEXT, "Ausar")
    assert len(flagged) >= 2, f"Expected ≥2 violations, got {len(flagged)}: {flagged}"
    joined = " | ".join(flagged).lower()
    assert "steps out" in joined
    assert "approaches" in joined


def test_detects_voice_possessive_violation():
    """`Ausar's voice`, `his gaze` (after Ausar reference) etc. should be flagged."""
    flagged = detect_player_puppeteering(USER_REGRESSION_TEXT, "Ausar")
    joined = " ".join(flagged).lower()
    assert "voice" in joined  # "As Ausar approaches, his voice contains a warm timbre"


def test_clean_response_no_false_positives():
    """A T1-clean response should produce zero flags."""
    flagged = detect_player_puppeteering(CLEAN_RESPONSE, "Ausar")
    assert flagged == [], f"False positives on clean text: {flagged}"


def test_sanitize_returns_sentinel_when_response_is_mostly_violation():
    """When >80% of the text is the AI playing the player, sanitizer should
    return sentinel `-1` so the caller knows to retry instead of returning a stub."""
    _, stripped = sanitize_player_puppeteering(USER_REGRESSION_TEXT, "Ausar")
    # The user's regression text is mostly Ausar-puppeteering. After stripping,
    # only the environment/Orion/Arwen lines remain — that may or may not be
    # long enough. The contract is: stripped > 0 OR -1; never 0 silently.
    assert stripped != 0, "Sanitize must flag violations on this text"


def test_sanitize_preserves_clean_text():
    cleaned, stripped = sanitize_player_puppeteering(CLEAN_RESPONSE, "Ausar")
    assert stripped == 0
    assert cleaned == CLEAN_RESPONSE


def test_no_character_name_means_no_detection():
    """Defensive: without a character name we can't detect violations."""
    flagged = detect_player_puppeteering(USER_REGRESSION_TEXT, "")
    assert flagged == []


def test_does_not_flag_npc_actions_addressing_player():
    """`Orion turns to Ausar` should NOT be flagged — Orion is the subject,
    not Ausar. Ausar appears only as an object."""
    text = "Orion turns to Ausar and offers him a cup. The fire crackles."
    flagged = detect_player_puppeteering(text, "Ausar")
    assert flagged == [], f"Should not flag NPC->player addressing: {flagged}"


def test_flags_dialogue_attributed_to_player():
    """`Ausar said` / `Ausar replied` are clear violations."""
    text = '"It is good to see you," Ausar said warmly.'
    flagged = detect_player_puppeteering(text, "Ausar")
    assert len(flagged) >= 1


def test_multi_player_protection():
    """When responding to Player B (Alee), the AI must not puppeteer
    Player A (Ausar). Pass BOTH names to the guard."""
    text = (
        '"It is wonderful to see you!" Alee called out. '
        "As Ausar approaches the carriage, his voice contains a warm timbre. "
        '"I have missed you, Alee," Ausar said. '
        "The night air carried a cool touch."
    )
    flagged = detect_player_puppeteering(text, ["Alee", "Ausar"])
    # Should catch BOTH the Alee-side and Ausar-side violations.
    joined = " ".join(flagged).lower()
    assert "ausar" in joined, f"Should flag Ausar puppeteering: {flagged}"
    # And `Alee called out` is dialogue attribution — also a violation
    assert any("called" in s.lower() or "alee" in s.lower() for s in flagged), \
        f"Should flag Alee dialogue attribution: {flagged}"


def test_first_name_only_violation():
    """Given the full name "Ausar Veltraus" the guard should also catch
    bare "Ausar steps…" — players usually go by first name mid-narrative."""
    text = "Ausar steps forward and draws his sword."
    flagged = detect_player_puppeteering(text, "Ausar Veltraus")
    assert len(flagged) >= 1, f"Should flag first-name-only ref: {flagged}"


def test_multi_player_clean_passes():
    """Two player names protected, response is clean — no false positives."""
    text = (
        "The steward bowed deeply, his smile measured. "
        "Behind him, candles guttered in the autumn breeze. "
        "The household fell quiet, awaiting word."
    )
    flagged = detect_player_puppeteering(text, ["Alee", "Ausar"])
    assert flagged == [], f"Clean multi-PC response flagged: {flagged}"
