"""Download a few Unsplash photos to bundle as offline fallbacks for the extension.

Developer tool, run once (not needed to use the extension). Standard library only.

    python tools/fetch_fallback_photos.py            # from the momentum-dash folder
    python tools/fetch_fallback_photos.py --count 5

The Access Key is read from the UNSPLASH_ACCESS_KEY environment variable, or from
config.js if that is not set. Writes assets/fallback/fallback-N.jpg + credits.json.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_DIR / "assets" / "fallback"
QUERY = "dark forest mountains mist"  # same mood as the live background
WIDTH = 1920  # big enough for most screens, small enough for the repo


def read_access_key() -> str:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        config = PROJECT_DIR / "config.js"
        if config.exists():
            match = re.search(r'UNSPLASH_ACCESS_KEY\s*=\s*"([^"]+)"', config.read_text())
            key = match.group(1) if match else None
    if not key or key.startswith("YOUR_"):
        sys.exit("No Unsplash key: set UNSPLASH_ACCESS_KEY or create config.js from config.example.js.")
    return key


def api_get(url: str, key: str):
    request = urllib.request.Request(url, headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=5, help="number of photos (max 30)")
    args = parser.parse_args()

    key = read_access_key()
    params = urllib.parse.urlencode(
        {"query": QUERY, "orientation": "landscape", "content_filter": "high", "count": args.count}
    )
    photos = api_get(f"https://api.unsplash.com/photos/random?{params}", key)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    credits = []
    for i, photo in enumerate(photos, start=1):
        filename = f"fallback-{i}.jpg"
        image_url = f"{photo['urls']['raw']}&w={WIDTH}&q=75&fm=jpg&fit=max"
        urllib.request.urlretrieve(image_url, OUT_DIR / filename)
        api_get(photo["links"]["download_location"], key)  # Unsplash guideline: count the download
        credits.append(
            {
                "file": filename,
                "photographer": photo["user"]["name"],
                "profileUrl": photo["user"]["links"]["html"],
                "photoUrl": photo["links"]["html"],
            }
        )
        size_kb = (OUT_DIR / filename).stat().st_size // 1024
        print(f"{filename}: {photo['user']['name']} ({size_kb} KB)")

    (OUT_DIR / "credits.json").write_text(json.dumps(credits, indent=2) + "\n")
    print(f"Wrote {len(credits)} photos + credits.json to {OUT_DIR.relative_to(PROJECT_DIR)}")


if __name__ == "__main__":
    main()
