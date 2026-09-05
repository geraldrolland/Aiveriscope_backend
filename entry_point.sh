#!/bin/sh
set -e

echo "[entry] Checking Chromium..."
if ! command -v chromium >/dev/null 2>&1; then
    echo "[entry] Installing Chromium (first start only)..."
    apt-get update
    apt-get install -y --no-install-recommends chromium fonts-liberation
    rm -rf /var/lib/apt/lists/*
else
    echo "[entry] Chromium already installed."
fi 

echo "[entry] Installing Python dependencies..."
pip install -r /app/requirements.txt

echo "[entry] Downloading NLTK data..."
python -c "
import nltk, os, zipfile
root = nltk.data.path[0]
for r in ('punkt', 'punkt_tab', 'stopwords', 'wordnet'):
    sub = 'tokenizers' if r.startswith('punkt') else 'corpora'
    target = os.path.join(root, sub, r)
    if os.path.isdir(target):
        continue
    if not nltk.download(r, quiet=True, force=True):
        raise SystemExit('NLTK download failed: ' + r)
    zpath = target + '.zip'
    if os.path.isfile(zpath) and not os.path.isdir(target):
        with zipfile.ZipFile(zpath) as z:
            z.extractall(os.path.join(root, sub))
"

echo "[entry] Starting: $*"
exec "$@"
