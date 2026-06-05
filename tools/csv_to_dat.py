#!/usr/bin/env python3
"""Convert a CSV file to device-ready pipe-delimited .dat.

Usage:
    python csv_to_dat.py input.csv [output.dat] [--key COL] [--value COL] [--title TITLE]

Expects a CSV with at least two columns. By default uses column 0 as key
and column 1 as value. Use --key and --value to specify column indices.

If output path is omitted, writes to ../data/{input_stem}.dat.
"""

import csv
import sys
import os
import argparse


def convert(input_path, output_path=None, key_col=0, value_col=1, title=None):
    rows = []
    with open(input_path, encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > max(key_col, value_col):
                rows.append((row[key_col].strip(), row[value_col].strip()))

    if output_path is None:
        stem = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'{stem}.dat')

    if title is None:
        title = os.path.splitext(os.path.basename(input_path))[0]

    with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'# {title}\n')
        f.write(f'#\n')
        for key, value in rows:
            if key:
                f.write(f'{key}|{value}\n')

    print(f'Wrote {len(rows)} entries to {output_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', help='Input CSV file')
    parser.add_argument('output', nargs='?', default=None, help='Output .dat file')
    parser.add_argument('--key', type=int, default=0, help='Key column index (default: 0)')
    parser.add_argument('--value', type=int, default=1, help='Value column index (default: 1)')
    parser.add_argument('--title', default=None, help='Title for comment header')
    args = parser.parse_args()
    convert(args.input, args.output, args.key, args.value, args.title)
