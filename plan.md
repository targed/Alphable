The "Big" Fix: Cythonize the Move Generator
Your structure.py is pure Python. It involves heavy recursion and list manipulation. Python is very slow at this. We can compile your move generator into C code using Cython, which usually yields a 10x-50x speedup for this specific type of algorithm.
Here is how to do it (Works on Windows/WSL and Linux):
Step A: Rename and Prepare
Rename structure.py to structure.pyx.
(Optional but recommended) You can add static types (like cdef int r), but even just compiling it "as is" gives a speed boost.
Step B: Create setup.py
Create a file named setup.py in the same folder:
code
Python
from setuptools import setup
from Cython.Build import cythonize

setup(
ext_modules = cythonize("structure.pyx", compiler_directives={'language_level' : "3"})
)
Step C: Compile
Run this command in your terminal:
code
Bash
python3 setup.py build_ext --inplace
This will create a file like structure.cpython-310-x86_64-linux-gnu.so (Linux) or .pyd (Windows).
Step D: Update Imports
Python prefers .so or .pyd files over .py files.
Ensure the original structure.py is renamed to structure_backup.py.
Run train.py.
Python will now import the compiled C version of your GADDAG.
