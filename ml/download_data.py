"""Download the WELFake fake-news dataset from Hugging Face into ml/data/."""
import shutil
import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT = DATA_DIR / "WELFake.parquet"

URL = (
    "https://huggingface.co/datasets/davanstrien/WELFake/resolve/main/"
    "data/train-00000-of-00001-290868f0a36350c5.parquet"
)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        print(f"Dataset already present: {OUTPUT}")
        return

    print(f"Downloading WELFake dataset from Hugging Face...")
    try:
        with urllib.request.urlopen(URL) as response, open(OUTPUT, "wb") as out:
            shutil.copyfileobj(response, out)
    except Exception as exc:
        OUTPUT.unlink(missing_ok=True)
        print(f"Download failed: {exc}", file=sys.stderr)
        sys.exit(1)

    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"Downloaded {OUTPUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
