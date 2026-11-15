#!/usr/bin/env python3
"""
Automated compatibility patcher for native C MAGPIE engine on HPC clusters.

Applies:
1. Cluster memory bounding & thread pinning patch (compat_memory_info.h -> memory_info.h).
2. __has_builtin macro shim for legacy compilers (e.g. GCC 8 on RHEL/CentOS nodes)
   where #if defined(__has_builtin) && __has_builtin(...) causes syntax errors.
"""

import os
import shutil
import sys

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SRC_HEADER = os.path.join(REPO_ROOT, "alphable_v4", "engine", "compat_memory_info.h")
TARGET_COMPAT = os.path.join(REPO_ROOT, "vendor", "magpie", "src", "compat", "memory_info.h")
LIBMAGPIE = os.path.join(REPO_ROOT, "vendor", "magpie", "bin", "libmagpie.so")

def patch_memory_info():
    if os.path.exists(SRC_HEADER) and os.path.isdir(os.path.dirname(TARGET_COMPAT)):
        need_copy = True
        if os.path.exists(TARGET_COMPAT):
            with open(SRC_HEADER, "rb") as f1, open(TARGET_COMPAT, "rb") as f2:
                if f1.read() == f2.read():
                    need_copy = False
        if need_copy:
            print(f"[Patcher] Applying cluster memory bounding patch to {TARGET_COMPAT}...")
            shutil.copyfile(SRC_HEADER, TARGET_COMPAT)
            if os.path.exists(LIBMAGPIE):
                os.remove(LIBMAGPIE)

def patch_builtin_shims():
    targets = [
        os.path.join(REPO_ROOT, "vendor", "magpie", "src", "ent", "wmp.h"),
        os.path.join(REPO_ROOT, "vendor", "magpie", "src", "def", "bit_defs.h"),
        os.path.join(REPO_ROOT, "vendor", "magpie", "src", "ent", "kwg.h"),
        os.path.join(REPO_ROOT, "vendor", "magpie", "src", "ent", "pat_features.h"),
        os.path.join(REPO_ROOT, "vendor", "magpie", "src", "impl", "move_gen.c"),
    ]
    shim = "\n#ifndef __has_builtin\n#define __has_builtin(x) 0\n#endif\n"

    for path in targets:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "__has_builtin(x)" not in content:
                lines = content.splitlines(True)
                for i, line in enumerate(lines[:15]):
                    if line.startswith("#define ") and "_H" in line:
                        lines.insert(i + 1, shim)
                        break
                else:
                    lines.insert(0, shim)
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                print(f"[Patcher] Injected __has_builtin compatibility shim into {os.path.relpath(path, REPO_ROOT)}")
                if os.path.exists(LIBMAGPIE):
                    try:
                        os.remove(LIBMAGPIE)
                    except OSError:
                        pass
        except Exception as e:
            print(f"[Patcher] Warning while checking {path}: {e}")

if __name__ == "__main__":
    patch_memory_info()
    patch_builtin_shims()
    print("[Patcher] MAGPIE compatibility check complete.")
