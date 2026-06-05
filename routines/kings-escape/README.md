# King's Escape — Knight's Tour Path Generator

Data generation utility for the **King's Escape** mentalism routine.

## The Effect

A spectator freely chooses any square on a 6x6 grid. The performer
immediately reveals where the king will end up — either **escaping off
the edge** of the board or **returning to his castle** (one of the 4
center squares) — then directs a complete 36-move knight's tour to get
there.

## How It Works

This utility finds all viable knight's tour paths on a 6x6 board and
reports which ending squares (edge or center) are reachable from each
starting position. The output feeds into a Zancig ZRI routine that uses
a pre-built lookup table: start square → chosen ending + full path.

### Board Layout

```
     c1   c2  c3  c4  c5  c6
    +-------------------------+
 r1 |  .   .   .   .   .   .  |   . = edge square (20 total)
 r2 |  .                   .  |
 r3 |  .       C   C       .  |   C = castle square (4 center)
 r4 |  .       C   C       .  |
 r5 |  .                   .  |
 r6 |  .   .   .   .   .   .  |
    +-------------------------+
```

Squares use **row,col** notation (1-indexed): `1,1` = top-left, `6,6` =
bottom-right. This maps directly to two `get_digit(1, 6)` calls in ZRI.

### Target Endings

- **Edge (escape):** Any of the 20 border squares — the king escapes
  off the map
- **Castle:** One of the 4 center squares (3,3 / 3,4 / 4,3 / 4,4) —
  the king returns to his castle

### Algorithm

Backtracking DFS with **Warnsdorff's heuristic** (visit squares with
the fewest onward moves first). Pre-computed neighbor tables and flat
indexing keep the hot path fast in pure Python.

## Usage

```
python generate_tours.py                          # survey all 36 starts
python generate_tours.py --start 1,1              # single starting square
python generate_tours.py --count 5000             # count mode (see below)
python generate_tours.py --start 2,4 --count 10000
python generate_tours.py --verify                 # validate saved paths
python generate_tours.py --show-path 1,1 3,4      # display a specific tour
python generate_tours.py -o my_results.json       # custom output file
```

### Modes

**Survey** (default): For each starting square, finds one example path
per viable target ending. Answers "which endings are reachable?" with
proof paths. Stops after 5,000 consecutive tours with no new ending
found. Runtime: ~10-30 minutes for all 36 starts.

**Count** (`--count N`): Enumerates up to N complete tours per start and
tallies how many end on each square. Useful for seeing how common each
ending is. Runtime varies with N.

### Inspecting Results

After running, the program writes `tours_data.json` (or the file
specified with `-o`).

Verify all saved paths are valid knight's tours:

```
python generate_tours.py --verify
```

Display a specific tour as a numbered grid:

```
python generate_tours.py --show-path 1,1 3,4
```

```
Knight's tour: 1,1 -> 3,4

     c1  c2  c3  c4  c5  c6
    +-------------------+
 r1 |  1  24   9  22   3  26  |
 r2 | 10  35   2  25  16  21  |
 r3 | 31   8  23  36  27   4  |
 r4 | 34  11  32  15  20  17  |
 r5 |  7  30  13  18   5  28  |
 r6 | 12  33   6  29  14  19  |
    +-------------------+
```

## Output Format (JSON)

```json
{
  "mode": "survey",
  "board_size": 6,
  "starts": {
    "1,1": {
      "type": "corner",
      "tours_searched": 12801,
      "edge_endings": {
        "1,2": ["1,1", "2,3", "1,5", ...],
        "6,1": ["1,1", "3,2", ...]
      },
      "castle_endings": {
        "3,4": ["1,1", "2,3", "1,5", ...]
      }
    }
  }
}
```

Each ending maps to its full 36-step path as a list of `"row,col"`
strings.

## Workflow

1. **Generate** — Run the survey to discover viable endings for every start
2. **Choose** — Pick one ending per start (edge or castle) for the lookup table
3. **Build routine** — Embed the chosen paths into a ZRI routine
4. **Perform** — Spectator picks a square, device reveals the ending and
   feeds the path via haptic

## Requirements

Python 3.7+. No external dependencies.
