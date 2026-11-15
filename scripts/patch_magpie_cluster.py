#!/usr/bin/env python3
"""
Automated compatibility patcher for native C MAGPIE engine on HPC clusters.

Applies:
1. Cluster memory bounding & thread pinning patch (compat_memory_info.h -> memory_info.h).
2. __has_builtin macro shim for legacy compilers (e.g. GCC 8 on RHEL/CentOS nodes)
   where #if defined(__has_builtin) && __has_builtin(...) causes syntax errors.
3. Pre-endgame (PEG) worker stack size definitions ensuring collision-free enum
   declarations across GCC 8 through GCC 13+ and different MAGPIE checkouts.
"""

import os
import shutil
import sys
import re

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
                try:
                    os.remove(LIBMAGPIE)
                except OSError:
                    pass

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

def patch_peg_defs():
    """
    Ensure PEG_POOL_WORKER_STACK_BYTES is defined without causing enum syntax collisions.
    1. Strip any legacy macro or enum shims from peg_pool.h and peg_pool.c.
    2. In src/def/peg_defs.h: ensure PEG_POOL_WORKER_STACK_BYTES is defined.
    3. In src/impl/peg_pool.c: ensure #include "../def/peg_defs.h" is present.
    """
    peg_defs_path = os.path.join(REPO_ROOT, "vendor", "magpie", "src", "def", "peg_defs.h")
    peg_pool_c_path = os.path.join(REPO_ROOT, "vendor", "magpie", "src", "impl", "peg_pool.c")
    peg_pool_h_path = os.path.join(REPO_ROOT, "vendor", "magpie", "src", "impl", "peg_pool.h")

    # Step A: Clean up any macro injections from peg_defs.h, peg_pool.h, peg_pool.c
    macro_patterns = [
        re.compile(r'#ifndef PEG_POOL_WORKER_STACK_BYTES\s*\n\s*#define PEG_POOL_WORKER_STACK_BYTES\s+[^\n]+\s*\n\s*#endif\s*\n?', re.MULTILINE),
        re.compile(r'#ifndef PEG_POOL_WORKER_STACK_BYTES\s*\nenum\s*\{[^}]*PEG_POOL_WORKER_STACK_BYTES[^}]*\};\s*\n(#define PEG_POOL_WORKER_STACK_BYTES[^\n]*\n)?#endif\s*\n?', re.MULTILINE),
    ]
    for p in [peg_pool_h_path, peg_pool_c_path]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                cleaned = content
                for pat in macro_patterns:
                    cleaned = pat.sub("", cleaned)
                if cleaned != content:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(cleaned)
                    print(f"[Patcher] Cleaned legacy PEG shims from {os.path.relpath(p, REPO_ROOT)}")
                    if os.path.exists(LIBMAGPIE):
                        try:
                            os.remove(LIBMAGPIE)
                        except OSError:
                            pass
            except Exception as e:
                print(f"[Patcher] Warning cleaning {p}: {e}")

    # Step B: Ensure src/def/peg_defs.h has PEG_POOL_WORKER_STACK_BYTES
    if os.path.exists(peg_defs_path):
        try:
            with open(peg_defs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Clean any internal #define inside enum
            content = re.sub(r'\n#define PEG_POOL_WORKER_STACK_BYTES PEG_POOL_WORKER_STACK_BYTES\s*\n', '\n', content)
            if "PEG_POOL_WORKER_STACK_BYTES" not in content:
                enum_block = (
                    "\n// PEG work-stealing pool capacities (peg_pool.c).\n"
                    "enum {\n"
                    "  PEG_POOL_QUEUE_INIT_CAP = 1024,\n"
                    "  PEG_POOL_WORKER_STACK_BYTES = 64 * 1024 * 1024,\n"
                    "};\n\n"
                )
                if "#endif" in content:
                    idx = content.rfind("#endif")
                    content = content[:idx] + enum_block + content[idx:]
                else:
                    content += enum_block
                with open(peg_defs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[Patcher] Added PEG_POOL_WORKER_STACK_BYTES to {os.path.relpath(peg_defs_path, REPO_ROOT)}")
                if os.path.exists(LIBMAGPIE):
                    try:
                        os.remove(LIBMAGPIE)
                    except OSError:
                        pass
        except Exception as e:
            print(f"[Patcher] Warning patching {peg_defs_path}: {e}")

    # Step C: Ensure src/impl/peg_pool.c includes ../def/peg_defs.h
    if os.path.exists(peg_pool_c_path):
        try:
            with open(peg_pool_c_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "peg_defs.h" not in content:
                if '#include "peg_pool.h"' in content:
                    content = content.replace(
                        '#include "peg_pool.h"',
                        '#include "peg_pool.h"\n#include "../def/peg_defs.h"'
                    )
                else:
                    content = '#include "../def/peg_defs.h"\n' + content
                with open(peg_pool_c_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[Patcher] Injected #include \"../def/peg_defs.h\" into {os.path.relpath(peg_pool_c_path, REPO_ROOT)}")
                if os.path.exists(LIBMAGPIE):
                    try:
                        os.remove(LIBMAGPIE)
                    except OSError:
                        pass
        except Exception as e:
            print(f"[Patcher] Warning patching {peg_pool_c_path}: {e}")

if __name__ == "__main__":
    patch_memory_info()
    patch_builtin_shims()
    patch_peg_defs()
    print("[Patcher] MAGPIE compatibility check complete.")
