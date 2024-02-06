#!/bin/bash
# Run this from the project root directory
printf "==== Running flake8\n"
python -m flake8
printf "==== Running mypy\n"
mypy src examples
