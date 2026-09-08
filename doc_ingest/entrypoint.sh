#!/bin/sh
set -e

# Clone the repo if not already present
if [ ! -d "$CLONE_DIR" ]; then
  echo "Cloning repository $REPO_URL into $CLONE_DIR"
  git clone "$REPO_URL" "$CLONE_DIR"
else
  echo "Repository already cloned at $CLONE_DIR"
fi

# Run the ingestion script
python main.py
