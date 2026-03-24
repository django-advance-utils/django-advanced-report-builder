#!/usr/bin/env python
"""Run Playwright tests for django-advanced-report-builder.

Usage:
    uv run run_tests.py                              # run all tests
    uv run run_tests.py --f test_table_reports.py    # run a specific file
    uv run run_tests.py --headed                     # run with browser visible
    uv run run_tests.py --video                      # record mp4 videos
"""
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description='Run report builder Playwright tests')
    parser.add_argument('--f', '--file', dest='file', help='Test file to run')
    parser.add_argument('--headed', action='store_true', help='Run with browser visible')
    parser.add_argument('--video', action='store_true', help='Record mp4 videos to ./videos/')
    parser.add_argument('--slowmo', type=int, default=0, help='Slow down actions by ms')
    parser.add_argument('-v', action='store_true', help='Verbose output')
    parser.add_argument('-k', dest='keyword', help='Run tests matching keyword')
    args = parser.parse_args()

    cmd = ['pytest']

    if args.file:
        cmd.append(args.file)

    if args.headed:
        cmd.append('--headed')

    if args.video:
        cmd.extend(['--video', 'on', '--output', 'videos'])

    if args.slowmo:
        cmd.extend(['--slowmo', str(args.slowmo)])

    if args.v:
        cmd.append('-v')

    if args.keyword:
        cmd.extend(['-k', args.keyword])

    cmd.extend(['-s', '--tb=short'])

    print(f'Running: {" ".join(cmd)}')
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
