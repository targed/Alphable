#ifndef COMPAT_MEMORY_INFO_H
#define COMPAT_MEMORY_INFO_H

#ifndef __has_builtin
#define __has_builtin(x) 0
#endif

#include <errno.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../util/io_util.h"

// Platform-specific includes
#if defined(__EMSCRIPTEN__)
#include <emscripten.h>
#elif defined(_WIN32) || defined(_WIN64)
#include <windows.h>
#elif defined(__APPLE__) || defined(__MACH__)
#include <sys/param.h>
#include <sys/sysctl.h>
#include <sys/types.h>
#elif defined(__linux__) || defined(__unix__) || defined(__posix__)
#include <unistd.h>
#endif

// Search budgets use a fixed base on browsers; linear-memory growth must not
// increase subsequent search allocations. Native budgets use physical RAM or cgroup bounds.
#ifdef __EMSCRIPTEN__
#define DEFAULT_TT_FRACTION 0.125
#define TT_MIN_SIZE_POWER 20
#define PEG_TT_MIN_SIZE_POWER 12
#else
#define DEFAULT_TT_FRACTION 0.05
#define TT_MIN_SIZE_POWER 18
#define PEG_TT_MIN_SIZE_POWER 12
#endif

static inline bool search_memory_is_bounded(void) {
#ifdef __EMSCRIPTEN__
  return true;
#else
  return false;
#endif
}

static inline uint64_t get_search_memory_budget_base(void) {
  uint64_t total_memory = 0;

  // 1. Explicit user/HPC override via environment variable
  const char *env_mb = getenv("MAGPIE_MAX_MEMORY_MB");
  if (env_mb != NULL && *env_mb != '\0') {
    char *endptr = NULL;
    unsigned long long mb = strtoull(env_mb, &endptr, 10);
    if (endptr != env_mb && mb > 0) {
      return (uint64_t)mb * 1024ULL * 1024ULL;
    }
  }

#if defined(__EMSCRIPTEN__)
  // Fixed browser budgeting base: growing the heap for data must not also
  // grow search tables on the next solve. 0.125 reserves a stable 32 MiB TT.
  total_memory = 256ULL * 1024 * 1024;

#elif defined(_WIN32) || defined(_WIN64)
  // Windows implementation
  MEMORYSTATUSEX statex;
  statex.dwLength = sizeof(statex);
  if (GlobalMemoryStatusEx(&statex)) {
    total_memory = statex.ullTotalPhys;
  } else {
    log_fatal("error retrieving memory info on Windows");
  }

#elif defined(__APPLE__) || defined(__MACH__)
  // macOS implementation
  int64_t memsize;
  size_t len = sizeof(memsize);
  if (sysctlbyname("hw.memsize", &memsize, &len, NULL, 0) == 0) {
    total_memory = memsize;
  } else {
    perror("sysctlbyname failed");
  }

#elif defined(__linux__)
  // 2. Linux cgroup v2 memory limit check (/sys/fs/cgroup/memory.max)
  FILE *cgroup_v2 = fopen("/sys/fs/cgroup/memory.max", "r");
  if (cgroup_v2 != NULL) {
    char cg_buf[64];
    if (fgets(cg_buf, sizeof(cg_buf), cgroup_v2) != NULL) {
      if (strncmp(cg_buf, "max", 3) != 0) {
        char *endptr = NULL;
        unsigned long long cg_lim = strtoull(cg_buf, &endptr, 10);
        if (endptr != cg_buf && cg_lim > 0 && cg_lim < (1ULL << 60)) {
          total_memory = (uint64_t)cg_lim;
        }
      }
    }
    fclose(cgroup_v2);
  }

  // 3. Linux cgroup v1 memory limit check (/sys/fs/cgroup/memory/memory.limit_in_bytes)
  if (total_memory == 0) {
    FILE *cgroup_v1 = fopen("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r");
    if (cgroup_v1 != NULL) {
      char cg_buf[64];
      if (fgets(cg_buf, sizeof(cg_buf), cgroup_v1) != NULL) {
        char *endptr = NULL;
        unsigned long long cg_lim = strtoull(cg_buf, &endptr, 10);
        // cgroup v1 sets huge 64-bit int (~9e18) when unlimited
        if (endptr != cg_buf && cg_lim > 0 && cg_lim < (1ULL << 50)) {
          total_memory = (uint64_t)cg_lim;
        }
      }
      fclose(cgroup_v1);
    }
  }

  // 4. Fallback to /proc/meminfo MemTotal
  if (total_memory == 0) {
    FILE *file = fopen_or_die("/proc/meminfo", "r");
    if (!file) {
      perror("Unable to open /proc/meminfo");
      return 0;
    }

    char line[256];
    while (fgets(line, sizeof(line), file)) {
      if (strncmp(line, "MemTotal:", 9) == 0) {
        char *endptr;
        errno = 0;
        unsigned long memtotal_kb = strtoul(line + 9, &endptr, 10);

        if (errno != 0 || endptr == line + 9) {
          log_fatal("error parsing memtotal");
        }

        while (*endptr == ' ' || *endptr == '\t') {
          endptr++;
        }

        if (strncasecmp(endptr, "kB", 2) != 0) {
          log_fatal("expected 'kB' unit in meminfo");
        }

        total_memory = (uint64_t)memtotal_kb * 1024ULL;
        break;
      }
    }
    fclose_or_die(file);
  }
#else
  log_fatal("unsupported platform");
#endif

  // 5. Global Safety Cap: Scrabble search (transposition table) never needs more
  // than 1-2 GB total budget base. Capping avoids OOM crashes on multi-core HPC nodes
  // that have 512 GB - 1 TB host RAM.
  if (total_memory > 2ULL * 1024ULL * 1024ULL * 1024ULL) {
    total_memory = 2ULL * 1024ULL * 1024ULL * 1024ULL; // Cap at 2 GiB
  }

  return total_memory;
}

static inline int get_num_cores(void) {
  int core_count = 1; // Default fallback value

  // 1. Explicit environment override MAGPIE_THREADS
  const char *env_threads = getenv("MAGPIE_THREADS");
  if (env_threads != NULL && *env_threads != '\0') {
    char *endptr = NULL;
    long t = strtol(env_threads, &endptr, 10);
    if (endptr != env_threads && t > 0) {
      return (int)t;
    }
  }

  // 2. Fallback to OpenMP thread limit if set
  const char *omp_threads = getenv("OMP_NUM_THREADS");
  if (omp_threads != NULL && *omp_threads != '\0') {
    char *endptr = NULL;
    long t = strtol(omp_threads, &endptr, 10);
    if (endptr != omp_threads && t > 0) {
      return (int)t;
    }
  }

#if defined(__EMSCRIPTEN__)
  core_count = EM_ASM_INT({
    return (typeof navigator !== 'undefined' && navigator.hardwareConcurrency)
           ? navigator.hardwareConcurrency
           : 4;
  });

#elif defined(_WIN32) || defined(_WIN64)
  SYSTEM_INFO sys_info;
  GetSystemInfo(&sys_info);
  core_count = (int)sys_info.dwNumberOfProcessors;

#elif defined(__APPLE__) || defined(__MACH__)
  int name[] = {CTL_HW, HW_NCPU};
  size_t size = sizeof(core_count);
  if (sysctl(name, 2, &core_count, &size, NULL, 0) == -1) {
    core_count = 1;
  }

#elif defined(__linux__) || defined(__unix__) || defined(__posix__)
  long num_cores = sysconf(_SC_NPROCESSORS_ONLN);
  if (num_cores > 0) {
    core_count = (int)num_cores;
  }

#else
  fprintf(stderr, "Warning: Unknown operating system. Returning 1 core.\n");
  core_count = 1;
#endif

  return core_count;
}

static inline bool get_available_memory_bytes(uint64_t *out) {
  if (!out) {
    return false;
  }
  *out = get_search_memory_budget_base();
  return true;
}

#endif