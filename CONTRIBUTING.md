# Contributing to Alphable

Thank you for your interest in contributing to Alphable! This guide explains our development workflow, testing standards, and pull request process.

---

## 1. Code of Conduct & Open Science Principles

Alphable is an open-source research and competitive AI project for imperfect-information Scrabble. We adhere to scientific rigor, verifiable benchmarks, and open-science reproducibility:
- Every performance claim must be accompanied by reproducible tournament telemetry and statistical tests (e.g., paired $t$-tests and Wilson score confidence intervals).
- We maintain transparency regarding engine baselines and configuration limits.

---

## 2. Environment Setup

### Prerequisites
- Linux (x86_64) or macOS
- Python 3.10 or higher
- GCC / Clang and standard build essentials (for native C MAGPIE library compilation)
- TeX Live (pdflatex, bibtex) if compiling research papers

### Installation
Clone the repository and run the setup script:

```bash
git clone https://github.com/Alphable/Alphable.git
cd Alphable

# One-command environment setup
./install.sh
```

Or configure manually in a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e ".[dev]"

# Compile native MAGPIE C-library
cd vendor/magpie
make all
cd ../..
```

---

## 3. Running Tests

We enforce high test coverage across all engine bindings, search algorithms, models, and platform tools.

```bash
# Run all core engine, search, and platform unit tests
pytest tests/ -v

# Run visualizer integration tests
pytest visualizer/tests/ -v

# Run full combined test suite
pytest tests/ visualizer/tests/ -q
```

Before opening a pull request, verify that all **185 tests** pass without errors.

---

## 4. Coding Standards

- **Python Style**: Follow PEP 8 conventions. Use clear, self-explanatory variable and function names.
- **Type Annotations**: Add type hints to public methods and dataclasses.
- **Memory Safety**: Any ctypes bindings with native C libraries (`alphable_v4/engine/magpie_bindings.py`) must cleanly manage allocated strings and memory buffers (`magpie_free_string`).
- **Deterministic Evaluation**: Use Common Random Numbers (CRN) and paired duplicate seeds when benchmarking to prevent tile distribution variance from distorting algorithmic evaluations.

---

## 5. Submitting Changes

1. Fork the repository and create a feature branch (`git checkout -b feature/my-improvement`).
2. Implement your changes with accompanying unit tests in `tests/`.
3. Run the test suite: `pytest tests/ visualizer/tests/ -q`.
4. If modifying search or evaluation behavior, run a benchmark validation:
   ```bash
   ./scripts/reproduce_benchmarks.sh --quick
   ```
5. Commit your changes with clear, semantic commit messages (`feat: ...`, `fix: ...`, `docs: ...`).
6. Push your branch to GitHub and open a Pull Request.

---

## 6. License

Alphable is licensed under the **GNU General Public License v3.0 (GPLv3)**. By contributing, you agree that your contributions will be licensed under the same terms.
