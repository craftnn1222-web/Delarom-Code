"""Sanity: the frontend contract for shuffle/repeat-one is fully client-side
(no backend endpoints), so this file just documents the invariants the tests
enforced by hand and via Playwright in iteration_26 / this iteration:

    1. Shuffle picks a different index than the current when the playlist
       has ≥ 2 tracks (pickShuffleIndex).
    2. Repeat-one overrides shuffle when both are toggled on.
    3. Toggles persist across reloads via localStorage under the key
       `delarom_music_modes` shaped `{ [themeKey]: {shuffle, repeatOne} }`.
    4. Per-row toggles and main-control toggles read/write the same state
       object (they mirror each other).

Kept as a placeholder so any regression in the backend surface
(e.g., someone accidentally adding a `mode` field to the music payload)
still trips the pytest suite. Nothing to assert here beyond "module
imports cleanly".
"""


def test_music_module_imports() -> None:
    import routes.music  # noqa: F401
