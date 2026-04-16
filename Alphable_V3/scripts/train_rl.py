#!/usr/bin/env python3
import sys
import subprocess

def main():
    print("WARNING: This script is deprecated. Please use 'alphable train rl' instead.")
    cmd = [sys.executable, "-m", "alphable.cli.main", "train", "rl"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

if __name__ == '__main__':
    main()
