#!/usr/bin/env python
# -*- coding: utf-8 -*-
# read the contents of your README file
import sys
from pathlib import Path

from setuptools import find_packages, setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

if sys.version_info >= (3, 8):
    lint_deps = ["flake8", "mypy==1.8.0", "types-requests"]
else:
    lint_deps = ["flake8", "mypy==1.4.1", "types-requests"]
test_deps = ["pytest==7.1", "responses==0.22", "httpretty"]

setup(
    name="picterra",
    version="2.0.5",
    description="Picterra API client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=[
        "requests",
        # We use the new `allowed_methods` option
        "urllib3>=1.26.0",
    ],
    extras_require={
        "test": test_deps,
        "lint": lint_deps,
    },
)
