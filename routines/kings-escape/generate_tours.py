"""
King's Escape — 6x6 Knight's Tour Path Generator

Finds knight's tours on a 6x6 board and reports which ones end on
"target" squares: edge squares (king escapes off the map) or the
4 center squares (king returns to castle).

Usage:
    python generate_tours.py                       # survey all 36 starts
    python generate_tours.py --count 5000          # count mode, 5000 tours/start
    python generate_tours.py --start 1,1           # single starting square
    python generate_tours.py --start 2,4 --count 10000
    python generate_tours.py --verify              # validate saved paths
"""

import argparse
import json
import sys
import time

SIZE = 6
TOTAL = SIZE * SIZE  # 36

KNIGHT_MOVES = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2), (1, 2), (2, -1), (2, 1)]

# 0-indexed center squares (display as 3,3  3,4  4,3  4,4)
CASTLE = {(2, 2), (2, 3), (3, 2), (3, 3)}

# Pre-computed neighbor lists using flat indices (0-35) for speed.
# ADJ[i] = tuple of flat neighbor indices for square i.
# ADJ_OF_ADJ[i][j] = tuple of flat neighbors of ADJ[i][j], used for Warnsdorff.
ADJ = []
for _r in range(SIZE):
    for _c in range(SIZE):
        _nbrs = []
        for _dr, _dc in KNIGHT_MOVES:
            _nr, _nc = _r + _dr, _c + _dc
            if 0 <= _nr < SIZE and 0 <= _nc < SIZE:
                _nbrs.append(_nr * SIZE + _nc)
        ADJ.append(tuple(_nbrs))

# Target squares (edge or castle) as a set of flat indices for fast lookup
TARGET_SET = set()
EDGE_SET = set()
CASTLE_SET = set()
for _r in range(SIZE):
    for _c in range(SIZE):
        _fi = _r * SIZE + _c
        if _r == 0 or _r == SIZE - 1 or _c == 0 or _c == SIZE - 1:
            EDGE_SET.add(_fi)
            TARGET_SET.add(_fi)
        if (_r, _c) in CASTLE:
            CASTLE_SET.add(_fi)
            TARGET_SET.add(_fi)


def is_edge(r, c):
    return r == 0 or r == SIZE - 1 or c == 0 or c == SIZE - 1


def is_castle(r, c):
    return (r, c) in CASTLE


def is_target(r, c):
    return is_edge(r, c) or is_castle(r, c)


def to_flat(r, c):
    return r * SIZE + c


def from_flat(fi):
    return fi // SIZE, fi % SIZE


def fmt(r, c):
    """Format 0-indexed position as 1-indexed 'row,col' string."""
    return f"{r + 1},{c + 1}"


def fmt_flat(fi):
    return fmt(fi // SIZE, fi % SIZE)


def parse_pos(s):
    """Parse '3,4' into 0-indexed (2, 3). Raises ValueError on bad input."""
    parts = s.split(",")
    if len(parts) != 2:
        raise ValueError(f"Bad position '{s}' — use row,col (e.g. 1,1)")
    r, c = int(parts[0]) - 1, int(parts[1]) - 1
    if not (0 <= r < SIZE and 0 <= c < SIZE):
        raise ValueError(f"Position '{s}' out of range (1-6)")
    return r, c


def square_type(r, c):
    if r == 0 or r == SIZE - 1:
        if c == 0 or c == SIZE - 1:
            return "corner"
        return "edge"
    if c == 0 or c == SIZE - 1:
        return "edge"
    if (r, c) in CASTLE:
        return "castle"
    return "inner"


# ---------------------------------------------------------------------------
# Core search — flat-index backtracking with inline Warnsdorff
# ---------------------------------------------------------------------------

def _warnsdorff_sorted(pos, visited):
    """Return unvisited neighbors of `pos` sorted by onward degree (ascending)."""
    adj = ADJ[pos]
    nbrs = []
    for n in adj:
        if not visited[n]:
            deg = 0
            for nn in ADJ[n]:
                if not visited[nn]:
                    deg += 1
            nbrs.append((deg, n))
    nbrs.sort()
    return nbrs


# ---------------------------------------------------------------------------
# Survey mode: find one path per distinct target ending
# ---------------------------------------------------------------------------

def survey(start_r, start_c, progress_cb=None):
    """Find one example path for each reachable target ending square.

    Uses backtracking DFS with Warnsdorff ordering. Stops after finding
    no new target endings for `patience` consecutive complete tours.

    Returns dict: {(end_r, end_c): [(r,c), ...path...], ...}
    Only includes edge/castle endings.
    """
    start = to_flat(start_r, start_c)
    visited = [False] * TOTAL
    path = [start]
    visited[start] = True

    results = {}       # flat end -> flat path
    tours_found = 0
    dry_streak = 0
    patience = 5000

    def backtrack(pos, depth):
        nonlocal tours_found, dry_streak

        if depth == TOTAL:
            tours_found += 1
            if pos in TARGET_SET and pos not in results:
                results[pos] = list(path)
                dry_streak = 0
            else:
                dry_streak += 1
            if progress_cb and tours_found % 1000 == 0:
                progress_cb(tours_found, len(results))
            return

        for _deg, nxt in _warnsdorff_sorted(pos, visited):
            if dry_streak >= patience:
                return
            visited[nxt] = True
            path.append(nxt)
            backtrack(nxt, depth + 1)
            path.pop()
            visited[nxt] = False

    backtrack(start, 1)

    # Convert flat indices back to (r,c) tuples
    rc_results = {}
    for end_fi, flat_path in results.items():
        rc_results[from_flat(end_fi)] = [from_flat(fi) for fi in flat_path]
    return rc_results, tours_found


# ---------------------------------------------------------------------------
# Count mode: enumerate up to N tours, tally endings
# ---------------------------------------------------------------------------

def count_tours(start_r, start_c, limit, progress_cb=None):
    """Enumerate up to `limit` complete tours. Tally ending squares.

    Returns (counts, examples, total):
        counts:   {(r,c): int}  — how many tours ended on each square
        examples: {(r,c): path} — one example path per ending (targets only)
        total:    int            — tours found
    """
    start = to_flat(start_r, start_c)
    visited = [False] * TOTAL
    path = [start]
    visited[start] = True

    counts = {}     # flat index -> count
    examples = {}   # flat index -> flat path
    total = [0]

    def backtrack(pos, depth):
        if total[0] >= limit:
            return

        if depth == TOTAL:
            total[0] += 1
            counts[pos] = counts.get(pos, 0) + 1
            if pos in TARGET_SET and pos not in examples:
                examples[pos] = list(path)
            if progress_cb and total[0] % 1000 == 0:
                progress_cb(total[0], limit)
            return

        for _deg, nxt in _warnsdorff_sorted(pos, visited):
            if total[0] >= limit:
                return
            visited[nxt] = True
            path.append(nxt)
            backtrack(nxt, depth + 1)
            path.pop()
            visited[nxt] = False

    backtrack(start, 1)

    # Convert flat indices back to (r,c) tuples
    rc_counts = {from_flat(k): v for k, v in counts.items()}
    rc_examples = {from_flat(k): [from_flat(fi) for fi in p] for k, p in examples.items()}
    return rc_counts, rc_examples, total[0]


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_path(path):
    """Check that a path is a valid knight's tour."""
    if len(path) != TOTAL:
        return False, f"Wrong length: {len(path)} (expected {TOTAL})"
    seen = set()
    for i, (r, c) in enumerate(path):
        if not (0 <= r < SIZE and 0 <= c < SIZE):
            return False, f"Step {i}: ({r},{c}) out of bounds"
        if (r, c) in seen:
            return False, f"Step {i}: ({r},{c}) visited twice"
        seen.add((r, c))
        if i > 0:
            pr, pc = path[i - 1]
            dr, dc = abs(r - pr), abs(c - pc)
            if sorted([dr, dc]) != [1, 2]:
                return False, f"Step {i}: ({pr},{pc})->({r},{c}) not a knight move"
    return True, "OK"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_path_grid(path):
    """Print a 6x6 grid showing move order."""
    grid = [[0] * SIZE for _ in range(SIZE)]
    for i, (r, c) in enumerate(path):
        grid[r][c] = i + 1
    print("     " + "  ".join(f"c{c + 1}" for c in range(SIZE)))
    print("    +" + "---" * SIZE + "-+")
    for r in range(SIZE):
        row_str = " ".join(f"{grid[r][c]:3d}" for c in range(SIZE))
        print(f" r{r + 1} |{row_str}  |")
    print("    +" + "---" * SIZE + "-+")


def results_to_json(all_results, mode):
    """Convert results to JSON-serializable structure."""
    data = {"mode": mode, "board_size": SIZE, "starts": {}}
    for start_pos, info in sorted(all_results.items()):
        start_key = fmt(*start_pos)
        entry = {
            "type": square_type(*start_pos),
            "tours_searched": info["tours_searched"],
            "edge_endings": {},
            "castle_endings": {},
        }
        if "counts" in info:
            entry["all_counts"] = {fmt(*k): v for k, v in sorted(info["counts"].items())}
        for end_pos, path in sorted(info["paths"].items()):
            end_key = fmt(*end_pos)
            path_strs = [fmt(*p) for p in path]
            if is_edge(*end_pos):
                entry["edge_endings"][end_key] = path_strs
            elif is_castle(*end_pos):
                entry["castle_endings"][end_key] = path_strs
        data["starts"][start_key] = entry
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="King's Escape — 6x6 Knight's Tour Path Generator")
    parser.add_argument("--start", type=str, default=None,
                        help="Single starting square (e.g. 1,1). Default: all 36.")
    parser.add_argument("--count", type=int, default=None,
                        help="Count mode: enumerate up to N tours per start.")
    parser.add_argument("--verify", action="store_true",
                        help="Verify paths in existing tours_data.json.")
    parser.add_argument("--show-path", type=str, default=None, nargs=2,
                        metavar=("START", "END"),
                        help="Show grid for a specific start->end path from JSON.")
    parser.add_argument("-o", "--output", type=str, default="tours_data.json",
                        help="Output JSON file (default: tours_data.json)")
    args = parser.parse_args()

    if args.verify:
        return do_verify(args.output)

    if args.show_path:
        return do_show_path(args.output, args.show_path[0], args.show_path[1])

    # Determine which starting squares to process
    if args.start:
        starts = [parse_pos(args.start)]
    else:
        starts = [(r, c) for r in range(SIZE) for c in range(SIZE)]

    mode = "count" if args.count else "survey"
    all_results = {}

    print(f"King's Escape - 6x6 Knight's Tour Path Generator")
    print(f"=" * 50)
    print(f"Mode: {mode}" + (f" (limit {args.count})" if args.count else ""))
    print(f"Starts: {len(starts)}")
    print()

    t0 = time.time()

    for idx, (sr, sc) in enumerate(starts):
        label = fmt(sr, sc)
        stype = square_type(sr, sc)
        sys.stdout.write(f"[{idx + 1}/{len(starts)}] Start {label} ({stype})...")
        sys.stdout.flush()

        ts = time.time()

        def progress(found, extra):
            sys.stdout.write(f"\r[{idx + 1}/{len(starts)}] Start {label} ({stype})... "
                             f"{found} tours, {extra} " +
                             ("endings" if mode == "survey" else f"/ {args.count}"))
            sys.stdout.flush()

        if args.count:
            counts, examples, total = count_tours(sr, sc, args.count, progress)
            info = {"tours_searched": total, "paths": examples, "counts": counts}
        else:
            paths, total = survey(sr, sc, progress)
            info = {"tours_searched": total, "paths": paths}

        elapsed = time.time() - ts
        all_results[(sr, sc)] = info

        # Print summary for this start
        edge_ends = [e for e in info["paths"] if is_edge(*e)]
        castle_ends = [e for e in info["paths"] if is_castle(*e)]

        sys.stdout.write(f"\r[{idx + 1}/{len(starts)}] Start {label} ({stype}) — "
                         f"{total} tours in {elapsed:.1f}s\n")
        if edge_ends:
            print(f"  Edge endings ({len(edge_ends)}):   "
                  + "  ".join(fmt(*e) for e in sorted(edge_ends)))
        else:
            print(f"  Edge endings: none found")
        if castle_ends:
            print(f"  Castle endings ({len(castle_ends)}): "
                  + "  ".join(fmt(*e) for e in sorted(castle_ends)))
        else:
            print(f"  Castle endings: none found")

        if args.count and info["counts"]:
            target_counts = {k: v for k, v in info["counts"].items() if is_target(*k)}
            other_count = sum(v for k, v in info["counts"].items() if not is_target(*k))
            if target_counts:
                print(f"  Target counts: " +
                      "  ".join(f"{fmt(*k)}={v}" for k, v in sorted(target_counts.items())))
            if other_count:
                print(f"  Other endings: {other_count}")
        print()

    total_time = time.time() - t0

    # Summary
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)

    edge_coverage = sum(1 for info in all_results.values()
                        if any(is_edge(*e) for e in info["paths"]))
    castle_coverage = sum(1 for info in all_results.values()
                          if any(is_castle(*e) for e in info["paths"]))
    print(f"  {edge_coverage}/{len(starts)} starts have at least one edge ending")
    print(f"  {castle_coverage}/{len(starts)} starts have at least one castle ending")
    both = sum(1 for info in all_results.values()
               if any(is_edge(*e) for e in info["paths"])
               and any(is_castle(*e) for e in info["paths"]))
    print(f"  {both}/{len(starts)} starts have both edge and castle options")
    print(f"  Total time: {total_time:.1f}s")
    print()

    # Write JSON
    data = results_to_json(all_results, mode)
    outpath = args.output
    with open(outpath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {outpath}")


def do_verify(json_path):
    """Load JSON and verify all saved paths."""
    try:
        with open(json_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {json_path}")
        return 1

    errors = 0
    checked = 0
    for start_key, entry in data["starts"].items():
        for end_type in ("edge_endings", "castle_endings"):
            for end_key, path_strs in entry[end_type].items():
                path = [parse_pos(s) for s in path_strs]
                ok, msg = verify_path(path)
                checked += 1
                if not ok:
                    print(f"  FAIL {start_key} -> {end_key}: {msg}")
                    errors += 1
                else:
                    # Verify start and end match
                    if fmt(*path[0]) != start_key:
                        print(f"  FAIL {start_key} -> {end_key}: path starts at {fmt(*path[0])}")
                        errors += 1
                    elif fmt(*path[-1]) != end_key:
                        print(f"  FAIL {start_key} -> {end_key}: path ends at {fmt(*path[-1])}")
                        errors += 1

    if errors:
        print(f"\n{errors} errors in {checked} paths")
        return 1
    else:
        print(f"All {checked} paths verified OK")
        return 0


def do_show_path(json_path, start_str, end_str):
    """Display the grid for a specific start->end path."""
    try:
        with open(json_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {json_path}")
        return 1

    entry = data["starts"].get(start_str)
    if not entry:
        print(f"No data for start {start_str}")
        return 1

    path_strs = None
    for end_type in ("edge_endings", "castle_endings"):
        if end_str in entry[end_type]:
            path_strs = entry[end_type][end_str]
            break
    if not path_strs:
        print(f"No path from {start_str} to {end_str}")
        return 1

    path = [parse_pos(s) for s in path_strs]
    print(f"\nKnight's tour: {start_str} -> {end_str}")
    print(f"Start type: {entry['type']}")
    er, ec = parse_pos(end_str)
    print(f"End type: {'edge' if is_edge(er, ec) else 'castle'}")
    print()
    print_path_grid(path)
    print()
    print("Path: " + " -> ".join(path_strs))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
