# TODO: Typing Duel 3D Improvements

## Visuals & Polish
- [ ] **Assets:** Replace generated Canvas sprites with a proper sci-fi font (e.g., using `THREE.FontLoader`).
- [ ] **Background:** Add a starfield or "cyberpunk grid" animation to the background instead of a static color.
- [ ] **Particles:** Add particle explosions when a word is cleared.
- [ ] **Feedback:** Add floating score text (+10) at the position of cleared words.

## Gameplay
- [ ] **Difficulty:** Implement word difficulty scaling (longer words as game progresses).
- [ ] **Combo System:** Add score multipliers for streaks of words without errors.
- [ ] **Typing Feedback:** Highlight letters in the target word as they are typed (currently only full word match is shown).

## Architecture
- [ ] **Persistence:** Save game results to a database (FastSQL) for leaderboards.
- [ ] **Reconnect:** Improve `initGame` to handle state recovery if a user refreshes mid-game (currently they rejoin but might miss active word context).
- [ ] **Validation:** Enforce server-side cooldowns on word submissions to prevent script cheating.
