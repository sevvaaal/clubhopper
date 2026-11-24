"""Download team logos and player photos once, shrink them and keep our own copies.

Reads the image URLs from site/data/game.json (so run build.py first) and
writes small WebP files the site serves itself:

    site/img/teams/{team id}.webp     logos, fit into 64x64, transparent
    site/img/players/{player id}.webp photos, 96x96

Images already saved are skipped, so this picks up where it stopped. The
media host doesn't use the API key or the daily request quota, but we still go
gently. Players without a real photo get API-Football's generic silhouette;
those are detected (the same picture for many players) and left out so the
site shows an initials avatar instead.

    python images.py
    python build.py     # again, so game.json knows which images exist
"""

import hashlib
import json
import time
from collections import Counter
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "site" / "data" / "game.json"
IMG = ROOT / "site" / "img"
# Hashes of the original downloads, to spot the shared placeholder picture.
HASHES = ROOT / "data" / "raw" / "image-hashes.json"

LOGO_SIZE = 64
PHOTO_SIZE = 96
SECONDS_BETWEEN = 0.15
PLACEHOLDER_MIN_COPIES = 3  # a picture shared by this many players is a placeholder


def shrink_logo(raw: bytes) -> Image.Image:
    img = Image.open(BytesIO(raw)).convert("RGBA")
    img.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
    canvas = Image.new("RGBA", (LOGO_SIZE, LOGO_SIZE), (0, 0, 0, 0))
    canvas.paste(img, ((LOGO_SIZE - img.width) // 2, (LOGO_SIZE - img.height) // 2), img)
    return canvas


def shrink_photo(raw: bytes) -> Image.Image:
    img = Image.open(BytesIO(raw)).convert("RGBA")
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    return img.crop((left, top, left + side, top + side)).resize((PHOTO_SIZE, PHOTO_SIZE), Image.LANCZOS)


def main() -> None:
    game = json.loads(GAME.read_text(encoding="utf-8"))
    hashes: dict[str, str] = json.loads(HASHES.read_text()) if HASHES.exists() else {}
    jobs = [("teams", tid, t["logo"], shrink_logo) for tid, t in game["teams"].items() if t.get("logo")]
    jobs += [("players", pid, p["photo"], shrink_photo) for pid, p in game["players"].items() if p.get("photo")]

    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "image-cache"})
    fetched = failed = 0
    try:
        for kind, key, url, shrink in jobs:
            out = IMG / kind / f"{key}.webp"
            tag = f"{kind}/{key}"
            if out.exists() or tag in hashes:
                continue
            try:
                r = client.get(url)
                r.raise_for_status()
                hashes[tag] = hashlib.md5(r.content).hexdigest()
                out.parent.mkdir(parents=True, exist_ok=True)
                shrink(r.content).save(out, "WEBP", quality=82, method=6)
                fetched += 1
            except Exception as e:  # one bad image shouldn't stop the rest
                failed += 1
                print(f"  failed {tag}: {e}")
            if fetched % 100 == 0 and fetched:
                print(f"  {fetched} downloaded...")
                HASHES.write_text(json.dumps(hashes))
            time.sleep(SECONDS_BETWEEN)
    finally:
        HASHES.write_text(json.dumps(hashes))

    # Drop the generic silhouette: the same original picture for many players.
    counts = Counter(h for tag, h in hashes.items() if tag.startswith("players/"))
    placeholders = {h for h, n in counts.items() if n >= PLACEHOLDER_MIN_COPIES}
    removed = 0
    for tag, h in hashes.items():
        if h in placeholders:
            path = IMG / f"{tag}.webp"
            if path.exists():
                path.unlink()
                removed += 1

    logos = len(list((IMG / "teams").glob("*.webp")))
    photos = len(list((IMG / "players").glob("*.webp")))
    size = sum(f.stat().st_size for f in IMG.rglob("*.webp")) // 1024
    print(f"Downloaded {fetched}, failed {failed}, placeholders removed {removed}.")
    print(f"Now {logos} logos and {photos} player photos, {size} KB in {IMG.relative_to(ROOT)}")
    print("Run build.py again so game.json knows which images exist.")


if __name__ == "__main__":
    main()
