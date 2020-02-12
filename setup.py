#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

setup(
    name='picterra',
    version='0',
    description='Picterra API client',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    zip_safe=False,
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
