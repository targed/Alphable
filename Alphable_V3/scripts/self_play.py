#!/usr/bin/env python3
import sys
import subprocess

def main():
    print("WARNING: This script is deprecated. Please use 'alphable selfplay generate' instead.")
    cmd = [sys.executable, "-m", "alphable.cli.main", "selfplay", "generate"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

if __name__ == '__main__':
    main()
