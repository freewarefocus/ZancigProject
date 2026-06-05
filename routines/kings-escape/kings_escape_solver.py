#!/usr/bin/env python3
"""
King's Escape — Knight's Tour Path Solver
==========================================

Utility to find all viable knight's tour paths on a 6x6 board for the
"King's Escape" mentalism routine. For each starting square, discovers
which ending squares (edge = "escape" or center = "castle") are reachable
via a complete knight's tour, and saves example paths.

The output feeds into a Zancig ZRI routine: once the performer knows the
starting square, they look up the pre-chosen ending square and announce
where the king will "escape" (edge) or "return to castle" (center).

Board Notation
--------------
Chess-style: columns a-f (left to right), rows 1-6 (bottom to top).
So a1 = bottom-left = internal (5,0), f6 = top-right = internal (0,5).

Usage
-----
    python kings_escape_solver.py                # survey: one path per viable ending
    python kings_escape_solver.py --mode count   # count mode: enumerate endings
    python kings_escape_solver.py --starts a1 c3 # specific starting squares only
    python kings_escape_solver.py --max-tours 500 # limit tours per start (count mode)
    python kings_escape_solver.py --output results.json  # save JSON results
"""

import argparse
import json
import sys
import time
from collections import defaultdict

N = 6

KNIGHT_MOVES = [
    (1, 2), (2, 1), (-1, 2), (-2, 1),
    (1, -2), (2, -1), (-1, -2), (-2, -1),
]

CENTER = {(2, 2), (2, 3), (3, 2), (3, 3)}
EDGE = {
    (r, c)
    for r in range(N)
    for c in range(N)
    if r == 0 or r == N - 1 or c == 0 or c == N - 1
}
VALID_ENDS = CENTER | EDGE


# --- Coordinate conversion ---

def rc_to_label(r, c):
    """Internal (row, col) to chess-style label. Row 0 = top = rank 6."""
    return f"{chr(ord('a') + c)}{N - r}"


def label_to_rc(label):
    """Chess-style label to internal (row, col)."""
    col = ord(label[0].lower()) - ord('a')
    row = N - int(label[1])
    if not (0 <= row < N and 0 <= col < N):
        raise ValueError(f"Invalid square: {label}")
    return (row, col)


def end_type(square):
    """Return 'CENTER' or 'EDGE' for a valid ending square."""
    if square in CENTER:
        return "CASTLE"
    if square in EDGE:
        return "ESCAPE"
    return "INTERIOR"


# --- Precomputed neighbor table ---

def knight_neighbors(r, c):
    result = []
    for dr, dc in KNIGHT_MOVES:
        nr, nc = r + dr, c + dc
        if 0 <= nr < N and 0 <= nc < N:
            result.append((nr, nc))
    return result


NEIGHBORS = {
    (r, c): knight_neighbors(r, c)
    for r in range(N)
    for c in range(N)
}


# --- Tour finders ---

def find_one_tour(start, target_end=None):
    """Find a single knight's tour from start.

    If target_end is given, only accept tours ending on that specific square.
    If target_end is None, accept any tour ending on a VALID_ENDS square.
    Uses Warnsdorff's heuristic for speed.
    """
    path = [start]
    visited = 1 << (start[0] * N + start[1])  # bitmask for speed

    def search(pos):
        if len(path) == N * N:
            if target_end is not None:
                return pos == target_end
            return pos in VALID_ENDS

        candidates = []
        for sq in NEIGHBORS[pos]:
            bit = 1 << (sq[0] * N + sq[1])
            if not (visited & bit):
                candidates.append(sq)

        # Warnsdorff: try most constrained first
        candidates.sort(key=lambda sq: sum(
            1 for nxt in NEIGHBORS[sq]
            if not (visited & (1 << (nxt[0] * N + nxt[1])))
        ))

        for sq in candidates:
            bit = 1 << (sq[0] * N + sq[1])
            path.append(sq)
            # Use nonlocal-free approach: modify visited via list trick
            # Actually, use iterative bitmask approach
            old_visited = visited
            yield_visited = old_visited | bit

            # We need to pass visited down — use a mutable container
            result = _search_inner(sq, path, yield_visited)
            if result is not None:
                return result

            path.pop()

        return None

    def _search_inner(pos, path, vis):
        if len(path) == N * N:
            if target_end is not None:
                return list(path) if pos == target_end else None
            return list(path) if pos in VALID_ENDS else None

        candidates = []
        for sq in NEIGHBORS[pos]:
            bit = 1 << (sq[0] * N + sq[1])
            if not (vis & bit):
                candidates.append(sq)

        candidates.sort(key=lambda sq: sum(
            1 for nxt in NEIGHBORS[sq]
            if not (vis & (1 << (nxt[0] * N + nxt[1])))
        ))

        for sq in candidates:
            bit = 1 << (sq[0] * N + sq[1])
            path.append(sq)
            result = _search_inner(sq, path, vis | bit)
            if result is not None:
                return result
            path.pop()

        return None

    return _search_inner(start, path, visited)


def find_tours_count(start, max_tours=5000, progress_cb=None):
    """Find up to max_tours knight's tours from start, counting endings.

    Returns dict: {ending_square: [list_of_paths]} where each path is a
    list of (r,c) tuples. Only stores up to 3 example paths per ending
    to save memory, but counts all found.
    """
    endings = defaultdict(lambda: {"count": 0, "examples": []})
    total_found = [0]
    path = [start]
    visited = 1 << (start[0] * N + start[1])

    def search(pos, vis):
        if total_found[0] >= max_tours:
            return

        if len(path) == N * N:
            if pos in VALID_ENDS:
                total_found[0] += 1
                entry = endings[pos]
                entry["count"] += 1
                if len(entry["examples"]) < 3:
                    entry["examples"].append(list(path))
                if progress_cb and total_found[0] % 500 == 0:
                    progress_cb(total_found[0])
            return

        candidates = []
        for sq in NEIGHBORS[pos]:
            bit = 1 << (sq[0] * N + sq[1])
            if not (vis & bit):
                candidates.append(sq)

        # Warnsdorff heuristic
        candidates.sort(key=lambda sq: sum(
            1 for nxt in NEIGHBORS[sq]
            if not (vis & (1 << (nxt[0] * N + nxt[1])))
        ))

        for sq in candidates:
            bit = 1 << (sq[0] * N + sq[1])
            path.append(sq)
            search(sq, vis | bit)
            path.pop()

            if total_found[0] >= max_tours:
                return

    search(start, visited)
    return dict(endings), total_found[0]


def survey_start(start):
    """Survey mode: find one example path per viable ending square.

    Tries each valid ending square and reports which ones are reachable.
    """
    results = {}
    for end_sq in sorted(VALID_ENDS):
        path = find_one_tour(start, target_end=end_sq)
        if path is not None:
            results[end_sq] = path
    return results


# --- Display helpers ---

def print_board(path):
    """Print the board with move numbers."""
    board = [[0] * N for _ in range(N)]
    for step, (r, c) in enumerate(path, 1):
        board[r][c] = step

    # Column headers
    print("    " + "  ".join(chr(ord('a') + c) for c in range(N)))
    print("   +" + "---" * N + "+")

    for r in range(N):
        rank = N - r
        cells = " ".join(f"{board[r][c]:2d}" for c in range(N))
        print(f" {rank} | {cells} |")

    print("   +" + "---" * N + "+")


def format_path_compact(path):
    """Format a path as a compact string of square labels."""
    return " -> ".join(rc_to_label(r, c) for r, c in path)


def format_path_moves(path):
    """Format a path as numbered moves."""
    lines = []
    for i, (r, c) in enumerate(path, 1):
        lines.append(f"{i:2d}. {rc_to_label(r, c)}")
    return "\n".join(lines)


def print_summary_table(all_results, mode):
    """Print a summary table of all starts and their viable endings."""
    print("\n" + "=" * 70)
    print("KING'S ESCAPE — SUMMARY")
    print("=" * 70)

    if mode == "survey":
        print(f"\n{'START':<8} {'ESCAPE (edge)':<40} {'CASTLE (center)'}")
        print("-" * 70)

        for start in sorted(all_results.keys()):
            label = rc_to_label(*start)
            data = all_results[start]
            escapes = sorted([rc_to_label(*sq) for sq in data if sq in EDGE])
            castles = sorted([rc_to_label(*sq) for sq in data if sq in CENTER])
            print(f"  {label:<6} {', '.join(escapes) if escapes else '(none)':<40} "
                  f"{', '.join(castles) if castles else '(none)'}")

    elif mode == "count":
        print(f"\n{'START':<7} {'TOTAL':<8} {'ENDINGS (square: count)'}")
        print("-" * 70)

        for start in sorted(all_results.keys()):
            label = rc_to_label(*start)
            endings, total = all_results[start]

            parts = []
            for sq in sorted(endings.keys()):
                sq_label = rc_to_label(*sq)
                count = endings[sq]["count"]
                etype = "C" if sq in CENTER else "E"
                parts.append(f"{sq_label}({etype}):{count}")

            print(f"  {label:<5} {total:<8} {', '.join(parts)}")

    print()


def print_detail(start, data, mode):
    """Print detailed results for one starting square."""
    label = rc_to_label(*start)
    print(f"\n--- Start: {label} ---")

    if mode == "survey":
        if not data:
            print("  No valid tours found.")
            return

        for end_sq in sorted(data.keys()):
            path = data[end_sq]
            end_label = rc_to_label(*end_sq)
            etype = end_type(end_sq)
            print(f"\n  End: {end_label} ({etype})")
            print_board(path)

    elif mode == "count":
        endings, total = data
        if total == 0:
            print("  No valid tours found.")
            return

        print(f"  Total tours found: {total}")
        for sq in sorted(endings.keys()):
            entry = endings[sq]
            sq_label = rc_to_label(*sq)
            etype = end_type(sq)
            print(f"\n  End: {sq_label} ({etype}) — {entry['count']} tours")
            if entry["examples"]:
                print("  Example path:")
                print_board(entry["examples"][0])


def save_results_json(all_results, mode, filepath):
    """Save results to JSON file."""
    output = {
        "board_size": N,
        "mode": mode,
        "center_squares": [rc_to_label(*sq) for sq in sorted(CENTER)],
        "starts": {}
    }

    for start in sorted(all_results.keys()):
        start_label = rc_to_label(*start)

        if mode == "survey":
            data = all_results[start]
            endings = {}
            for end_sq, path in data.items():
                end_label = rc_to_label(*end_sq)
                endings[end_label] = {
                    "type": end_type(end_sq),
                    "path": [rc_to_label(*sq) for sq in path],
                }
            output["starts"][start_label] = {
                "escape_count": sum(1 for sq in data if sq in EDGE),
                "castle_count": sum(1 for sq in data if sq in CENTER),
                "endings": endings,
            }

        elif mode == "count":
            endings_data, total = all_results[start]
            endings = {}
            for end_sq, entry in endings_data.items():
                end_label = rc_to_label(*end_sq)
                endings[end_label] = {
                    "type": end_type(end_sq),
                    "count": entry["count"],
                    "example_paths": [
                        [rc_to_label(*sq) for sq in path]
                        for path in entry["examples"]
                    ],
                }
            output["starts"][start_label] = {
                "total_tours": total,
                "endings": endings,
            }

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {filepath}")


# --- Main ---

def parse_args():
    parser = argparse.ArgumentParser(
        description="King's Escape — Knight's Tour path solver for 6x6 board"
    )
    parser.add_argument(
        "--mode", choices=["survey", "count"], default="survey",
        help="survey: one path per viable ending (fast). "
             "count: enumerate up to --max-tours, count endings (thorough). "
             "Default: survey"
    )
    parser.add_argument(
        "--starts", nargs="+", metavar="SQ",
        help="Specific starting squares (e.g. a1 c3 f6). Default: all 36"
    )
    parser.add_argument(
        "--max-tours", type=int, default=5000,
        help="Max tours to enumerate per start in count mode (default: 5000)"
    )
    parser.add_argument(
        "--output", "-o", metavar="FILE",
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--detail", action="store_true",
        help="Print detailed paths/boards (verbose)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress output"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Determine starting squares
    if args.starts:
        starts = []
        for s in args.starts:
            try:
                starts.append(label_to_rc(s))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        starts = [(r, c) for r in range(N) for c in range(N)]

    total_starts = len(starts)
    all_results = {}

    print(f"King's Escape Solver — {N}x{N} board, mode: {args.mode}")
    print(f"Starting squares: {total_starts}")
    if args.mode == "count":
        print(f"Max tours per start: {args.max_tours}")
    print()

    overall_start = time.time()

    for i, start in enumerate(starts):
        label = rc_to_label(*start)

        if args.mode == "survey":
            if not args.quiet:
                print(f"[{i+1}/{total_starts}] Surveying {label}...", end="", flush=True)

            t0 = time.time()
            results = survey_start(start)
            elapsed = time.time() - t0

            all_results[start] = results
            n_escape = sum(1 for sq in results if sq in EDGE)
            n_castle = sum(1 for sq in results if sq in CENTER)

            if not args.quiet:
                print(f" {len(results)} endings ({n_escape} escape, {n_castle} castle) "
                      f"[{elapsed:.1f}s]")

        elif args.mode == "count":
            if not args.quiet:
                print(f"[{i+1}/{total_starts}] Counting {label}...", end="", flush=True)

            def progress(n):
                if not args.quiet:
                    print(f" {n}...", end="", flush=True)

            t0 = time.time()
            endings, total = find_tours_count(start, args.max_tours, progress)
            elapsed = time.time() - t0

            all_results[start] = (endings, total)

            if not args.quiet:
                print(f" {total} tours, {len(endings)} distinct endings [{elapsed:.1f}s]")

    overall_elapsed = time.time() - overall_start

    # Print summary
    print_summary_table(all_results, args.mode)

    # Print detail if requested
    if args.detail:
        for start in sorted(all_results.keys()):
            print_detail(start, all_results[start], args.mode)

    print(f"Total time: {overall_elapsed:.1f}s")

    # Save JSON if requested
    if args.output:
        save_results_json(all_results, args.mode, args.output)


if __name__ == "__main__":
    main()
