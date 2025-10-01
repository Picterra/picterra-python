#!/bin/bash

# This script checks that all the titles of the commits between the current branch and master
# follow the "([[a-zA-Z_]+\])+ .+$" regex.

# Regex to match the commit title format
COMMIT_TITLE_REGEX="^(\[[a-zA-Z_]+\])+ .+$"

master=$1
head=$2


# Get the list of commit titles between the current branch and master:
# using master..HEAD would not work so we pass it from GH event vars
COMMIT_TITLES=$(git log $master..$head --pretty=format:%s)

# Array to store offending commit titles
OFFENDING_COMMIT_TITLES=()

# Check each commit title against the regex
while IFS= read -r title; do
  if ! [[ "$title" =~ $COMMIT_TITLE_REGEX ]]; then
    OFFENDING_COMMIT_TITLES+=("$title")
  fi
done <<< "$COMMIT_TITLES"

# Check if there are any offending commit titles
if [ ${#OFFENDING_COMMIT_TITLES[@]} -ne 0 ]; then
  echo "Error: The following commit titles do not follow the format '([<scope>])+ <description>':"
  for title in "${OFFENDING_COMMIT_TITLES[@]}"; do
    echo "- $title"
  done
  exit 1
else
  echo "Success: All commit titles are formatted correctly."
fi
