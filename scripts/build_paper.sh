#!/usr/bin/env bash
# scripts/build_paper.sh - Compiles the Alphable V4 research paper to PDF
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PAPER_DIR="${REPO_ROOT}/paper"
OUTPUT_PDF="${PAPER_DIR}/alphable_v4.pdf"

echo "=== Building Alphable V4 Research Paper ==="
cd "${PAPER_DIR}"

# Step 1: Initial pdflatex pass
echo "--> Pass 1: pdflatex (generating aux files)"
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null || {
    echo "ERROR: First pdflatex pass failed. Printing log excerpt:"
    tail -n 35 main.log
    exit 1
}

# Step 2: Run bibtex
echo "--> Pass 2: bibtex (compiling citations)"
bibtex main > /dev/null || {
    echo "ERROR: bibtex compilation failed. Printing log excerpt:"
    cat main.blg || true
    exit 1
}

# Step 3: Second pdflatex pass (resolving references)
echo "--> Pass 3: pdflatex (resolving bibliography cross-references)"
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null || {
    echo "ERROR: Second pdflatex pass failed. Printing log excerpt:"
    tail -n 35 main.log
    exit 1
}

# Step 4: Final pdflatex pass (locking hyperref links and table floats)
echo "--> Pass 4: pdflatex (final layout generation)"
pdflatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null || {
    echo "ERROR: Final pdflatex pass failed. Printing log excerpt:"
    tail -n 35 main.log
    exit 1
}

# Copy / link final output
cp main.pdf "${OUTPUT_PDF}"
echo "=== Success: Paper built at ${OUTPUT_PDF} ($(du -h "${OUTPUT_PDF}" | cut -f1)) ==="
