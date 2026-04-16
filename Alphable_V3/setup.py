from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        "alphable.core.structure",
        ["src/alphable/core/structure.pyx"],
        include_dirs=[np.get_include()],
        language="c++",
    )
]

setup(
    name="alphable",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=cythonize(extensions, language_level=3) if extensions else [],
    zip_safe=False,
)
