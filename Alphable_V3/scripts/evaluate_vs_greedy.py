"""V2-native evaluator: Alphable vs Greedy baseline with replay logging."""

import os
import subprocess
import sys


def main():
    print("WARNING: This script is deprecated. Please use 'alphable eval baseline --opponent greedy' instead.")
    cmd = [
        sys.executable,
        '-m', 'alphable.cli.main', 'eval', 'baseline',
        '--opponent', 'greedy',
    ]
    cmd.extend(sys.argv[1:])
    raise SystemExit(subprocess.call(cmd))


if __name__ == '__main__':
    main()
