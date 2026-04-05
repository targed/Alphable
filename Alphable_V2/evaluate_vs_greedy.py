"""V2-native evaluator: Alphable vs Greedy baseline with replay logging."""

import os
import subprocess
import sys


def main():
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), 'evaluate_vs_baseline.py'),
        '--opponent', 'greedy',
    ]
    cmd.extend(sys.argv[1:])
    raise SystemExit(subprocess.call(cmd))


if __name__ == '__main__':
    main()
