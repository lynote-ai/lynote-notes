#!/usr/bin/env bash
# End-to-end CLI walkthrough for Lynote Notes.
# Run from the repository root after `pip install -e .`.
set -euo pipefail

WORKSPACE="$(mktemp -d)/lynote-demo"

echo "== add a source =="
lynote-notes --workspace "$WORKSPACE" add examples/sample-lecture.md

echo
echo "== list sources =="
lynote-notes --workspace "$WORKSPACE" list

echo
echo "== generate a cited note =="
lynote-notes --workspace "$WORKSPACE" note --title "Week 3 notes"

echo
echo "== ask a question =="
lynote-notes --workspace "$WORKSPACE" ask "Why is retrieval important?"

echo
echo "== export (Anki) =="
lynote-notes --workspace "$WORKSPACE" list --notes
