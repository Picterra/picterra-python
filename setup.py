#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="picterra",
    version="1.2.2",
    description="Picterra API client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages("src"),
    setup_requires=[
        "pytest-runner",
        "flake8",
    ],
    install_requires=[
        "requests",
        # We use the new `allowed_methods` option
        "urllib3>=1.26.0",
    ],
    tests_require=["pytest==7.1", "flake8", "responses==0.22", "httpretty"],
)
