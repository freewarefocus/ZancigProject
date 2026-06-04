# Nim

Optimal strategy coach for the game of Nim. Computes the mathematically perfect move (XOR-fold / Sprague-Grundy) and signals it via haptic so the performer always wins.

## Requirements

None. Pure haptic I/O — runs on any Zancig device.

## Setup phase (screen visible)

1. **Input digit (2–9):** Number of piles.
2. **Input digit (1–9):** Size of each pile, repeated for each pile entered in step 1.
3. **Haptic signal:** Ready (two longs) = you have the winning position, go first. Nack (three fast buzzes) = opponent has the advantage.
4. **Confirm (yes/no):** Are you going first? Then the device goes dark.

## Performance loop (stealth)

Each round alternates between the performer's turn and the opponent's turn.

### Performer's turn

1. **Haptic output — two digits separated by a gap:**
   - First digit: pile number (1-based).
   - Second digit: how many to take from that pile.
2. **Wait for press:** Performer acknowledges and makes the move on the table.
3. If no winning move exists (losing position), a nack buzzes first — then the device suggests taking 1 from the largest pile (damage control).
4. If the game is over after the performer's move: ready signal, wait for press, round ends.

### Opponent's turn

1. **Input digit (1–N):** Which pile the opponent took from.
   - If the selected pile is empty, nack buzzes and input repeats.
2. **Input digit (1–pile size):** How many the opponent took.
3. If the game is over after the opponent's move: end signal (three longs), wait for press, round ends.

## End of round

1. **Confirm (yes/no):** Play again? Yes restarts from setup. No exits the routine.
