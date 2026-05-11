#!/bin/bash

set -e


cd "$(dirname "$0")/python_survey" || exit 1


if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt 2>/dev/null || {
    pip install -r requirements.txt
}

python main.py

deactivate
