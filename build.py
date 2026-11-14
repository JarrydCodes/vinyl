#!/usr/bin/env python3
"""Build a static site from your Discogs collection.

  export DISCOGS_TOKEN=your_token      (discogs.com/settings/developers -> Generate token)
  python3 build.py Jarrydvinyl

Output goes to ./site  (index.html, record.html, collection.js, covers/, nfc-links.csv)
Re-run any time; cached data and covers are reused, so only new records hit the API.
Optional: edit extras.json to add your own fields per release (see README in that file's example).
"""
import csv, json, os, re, shutil, sys, time, urllib.request

API = "https://api.discogs.com"
UA = "MyVinylSite/1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
CACHE = os.path.join(HERE, "cache")

def get(url, token, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Authorization": f"Discogs token={token}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                # stay under the 60 requests/minute limit
                time.sleep(1.1)
                return data if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30); continue
            raise
    raise RuntimeError("Rate limited too many times: " + url)

def clean(name):
    return re.sub(r"\s\(\d+\)$", "", name or "")

def fetch_collection(user, token):
    out, page = [], 1
    while True:
        d = get(f"{API}/users/{user}/collection/folders/0/releases?per_page=100&page={page}", token)
        out += d["releases"]
        if page >= d["pagination"]["pages"]: break
        page += 1
    return out

def detail(rid, token):
    path = os.path.join(CACHE, f"{rid}.json")
    if os.path.exists(path):
        return json.load(open(path))
    d = get(f"{API}/releases/{rid}", token)
    keep = {
        "tracklist": [{"pos": t.get("position", ""), "title": t.get("title", ""), "dur": t.get("duration", "")}
                      for t in d.get("tracklist", []) if t.get("type_", "track") == "track"],
        "country": d.get("country", ""),
        "released": d.get("released_formatted", d.get("year", "")),
        "url": d.get("uri", f"https://www.discogs.com/release/{rid}"),
    }
    json.dump(keep, open(path, "w"))
    return keep

def cover(rid, url, token):
    dest = os.path.join(SITE, "covers", f"{rid}.jpg")
    if os.path.exists(dest) or not url: return f"covers/{rid}.jpg" if os.path.exists(dest) else ""
    try:
        open(dest, "wb").write(get(url, token, raw=True))
        return f"covers/{rid}.jpg"
    except Exception as e:
        print("  cover failed", rid, e); return ""

def main():
    if len(sys.argv) < 2 or not os.environ.get("DISCOGS_TOKEN"):
        sys.exit(__doc__)
    user, token = sys.argv[1], os.environ["DISCOGS_TOKEN"]
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.join(SITE, "covers"), exist_ok=True)
    for f in ("index.html", "record.html", "tags.html", "style.css"):
        shutil.copy(os.path.join(HERE, "templates", f), os.path.join(SITE, f))

    extras_path = os.path.join(HERE, "extras.json")
    extras = json.load(open(extras_path)) if os.path.exists(extras_path) else {}

    print("Fetching your Discogs field names...")
    fields = {f["id"]: f["name"] for f in get(f"{API}/users/{user}/collection/fields", token).get("fields", [])}
    print("Fetching collection...")
    raw = fetch_collection(user, token)
    print(f"{len(raw)} records")
    records, seen = [], set()
    for i, r in enumerate(raw, 1):
        b = r["basic_information"]; rid = b["id"]
        if rid in seen: continue          # duplicate copies share one page
        seen.add(rid)
        print(f"[{i}/{len(raw)}] {b['title']}")
        d = detail(rid, token)
        fmt = b["formats"][0] if b.get("formats") else {}
        rec = {
            "id": rid,
            "title": b["title"],
            "artist": ", ".join(clean(a["name"]) for a in b["artists"]),
            "year": b.get("year") or None,
            "label": ", ".join(l["name"] for l in b.get("labels", [])[:2]),
            "catno": (b.get("labels") or [{}])[0].get("catno", ""),
            "format": ", ".join([fmt.get("name", "")] + fmt.get("descriptions", [])).strip(", "),
            "genres": b.get("genres", []),
            "styles": b.get("styles", []),
            "added": r.get("date_added", "")[:10],
            "rating": r.get("rating", 0),
            "cover": cover(rid, b.get("cover_image"), token),
            "notes": [{"label": fields.get(n["field_id"], "Note"), "value": n["value"]}
                      for n in r.get("notes", []) if n.get("value")],
            **d,
        }
        rec.update(extras.get(str(rid), {}))   # your own fields win
        records.append(rec)

    records.sort(key=lambda x: (x["artist"].lower(), x["year"] or 0))
    with open(os.path.join(SITE, "collection.js"), "w") as f:
        f.write("window.COLLECTION = " + json.dumps(records, ensure_ascii=False) + ";")
    with open(os.path.join(HERE, "nfc-links.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["release_id", "artist", "title", "path_to_write_to_tag"])
        for r in records:
            w.writerow([r["id"], r["artist"], r["title"], f"record.html?id={r['id']}"])
    print("Done. Open site/index.html or upload the site folder. Tag paths are in nfc-links.csv")

if __name__ == "__main__":
    main()
