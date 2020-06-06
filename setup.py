#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

setup(
    name='picterra',
    version='1.0.0',
    description='Picterra API client',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    setup_requires=[
        'pytest-runner',
        'flake8',
    ],
    install_requires=[
        'requests',
    ],
    tests_require=[
        'pytest',
        'flake8',
        'responses',
    ],
)
