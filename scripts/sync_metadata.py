#!/usr/bin/env python3
"""Sync latest GitHub release versions, download URLs, JSON-LD, llms.txt, and sitemap.xml.

Zero external dependencies (Python 3.9+ stdlib only).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWNER = "Viguru24"

TARGETS = [
    {
        "repo": "Video",
        "asset_regex": r"\.msixbundle$",
        "files": ["index.html", "cosmo-symphony/index.html", "llms.txt"],
    },
    {
        "repo": "YouTube",
        "asset_regex": r"\.apk$",
        "files": ["index.html", "vixz/index.html", "llms.txt"],
    },
    {
        "repo": "Kin-Tracker",
        "asset_regex": r"KinTracker-v.*\.apk$",
        "files": ["index.html", "kin-tracker/index.html", "llms.txt"],
    },
    {
        "repo": "CosmoWhisper-Downloads",
        "asset_regex": r"\.exe$",
        "files": ["index.html", "cosmowhisper/index.html", "llms.txt"],
    },
    {
        "repo": "CosmoWhisper-Native",
        "asset_regex": r"\.dmg$",
        "files": ["index.html", "cosmowhisper/index.html", "llms.txt"],
    },
    {
        "repo": "VixzDesktop",
        "asset_regex": r"\.msix$",
        "files": ["index.html", "vixz/index.html", "llms.txt"],
    },
]


def github_get_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "viguru24-metadata-sync/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_latest_release(repo: str, asset_regex: str) -> tuple[str, str] | None:
    url = f"https://api.github.com/repos/{OWNER}/{repo}/releases/latest"
    try:
        data = github_get_json(url)
    except urllib.error.HTTPError as exc:
        print(f"[WARN] Could not fetch {repo}: HTTP {exc.code}")
        return None
    tag = data.get("tag_name", "")
    pattern = re.compile(asset_regex)
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if pattern.search(name):
            return tag, asset["browser_download_url"]
    return None


def sync_file(path: Path, replacements: list[tuple[re.Pattern[str], str]], dry_run: bool) -> bool:
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    updated = original
    for regex, repl in replacements:
        updated = regex.sub(repl, updated)
    if updated == original:
        return False
    if dry_run:
        print(f"[DRY-RUN] Would update {path.relative_to(ROOT)}")
    else:
        path.write_text(updated, encoding="utf-8", newline="\n")
        print(f"[UPDATED] {path.relative_to(ROOT)}")
    return True


def ping_indexnow(host: str, urls: list[str], dry_run: bool) -> None:
    key = os.environ.get("INDEXNOW_KEY", "").strip()
    if not key:
        print("[INFO] INDEXNOW_KEY not set; skipping IndexNow ping.")
        return
    payload = json.dumps({
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": urls,
    }).encode("utf-8")
    if dry_run:
        print(f"[DRY-RUN] Would ping IndexNow for {len(urls)} URLs")
        return
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"[INDEXNOW] HTTP {resp.status}")


def build_scoped_patterns(repo: str, clean_ver: str) -> list[tuple[re.Pattern[str], str]]:
    ver_num = r"v[0-9]+\.[0-9]+\.[0-9]+"
    if repo == "Video":
        return [
            (re.compile(rf"(Cosmo Symphony</h3>[\s\S]{{0,200}}?Windows MSIX ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(🌌 Windows MSIX ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(Cosmo\.Symphony_[^\"]*\.msixbundle\"[^>]*>\s*📥 Download MSIX ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(r'("name":\s*"Cosmo Symphony"[\s\S]{0,400}?"softwareVersion":\s*")[^"]+(")'), rf"\g<1>{clean_ver}\g<2>"),
            (re.compile(rf"(Cosmo Symphony Windows MSIX \(){ver_num}(\))"), rf"\g<1>v{clean_ver}\g<2>"),
        ]
    if repo == "YouTube":
        return [
            (re.compile(rf"(Vixz YouTube Player</h3>[\s\S]{{0,200}}?Android APK • ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(🎬 Android APK ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(Vixz-YouTube-Player-[^\"]*\.apk\"[^>]*>\s*📥 (?:Download|Android) APK ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(r'("name":\s*"Vixz YouTube Player"[\s\S]{0,400}?"softwareVersion":\s*")[^"]+(")'), rf"\g<1>{clean_ver}\g<2>"),
            (re.compile(rf"(Vixz YouTube Player Android APK \(){ver_num}(\))"), rf"\g<1>v{clean_ver}\g<2>"),
        ]
    if repo == "Kin-Tracker":
        return [
            (re.compile(rf"(Kin-Tracker</h3>[\s\S]{{0,200}}?Android APK ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(🛰️ Android APK ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(KinTracker-[^\"]*\.apk\"[^>]*>\s*📥 Download APK ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(r'("name":\s*"Kin-Tracker"[\s\S]{0,400}?"softwareVersion":\s*")[^"]+(")'), rf"\g<1>{clean_ver}\g<2>"),
            (re.compile(rf"(Kin-Tracker Android APK \(){ver_num}(\))"), rf"\g<1>v{clean_ver}\g<2>"),
        ]
    if repo == "CosmoWhisper-Downloads":
        return [
            (re.compile(rf"(CosmoWhisper-Setup-[^\"]*\.exe\"[^>]*>\s*🪟 Windows Setup ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(🎙️ Windows Setup ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(r'("name":\s*"CosmoWhisper Native"[\s\S]{0,400}?"softwareVersion":\s*")[^"]+(")'), rf"\g<1>{clean_ver}\g<2>"),
            (re.compile(rf"(CosmoWhisper Windows Setup \(){ver_num}(\))"), rf"\g<1>v{clean_ver}\g<2>"),
        ]
    if repo == "CosmoWhisper-Native":
        return [
            (re.compile(rf"(CosmoWhisper_v[^\"]*\.dmg\"[^>]*>\s*🍎 macOS DMG ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(macOS DMG ){ver_num}( • Offline AI)"), rf"\g<1>v{clean_ver}\g<2>"),
            (re.compile(rf"(CosmoWhisper macOS DMG \(){ver_num}(?:-mac)?(\))"), rf"\g<1>v{clean_ver}-mac\g<2>"),
        ]
    if repo == "VixzDesktop":
        return [
            (re.compile(rf"(VixzDesktop-[^\"]*\.msix\"[^>]*>\s*📥 Download MSIX ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(VixzDesktop-[^\"]*\.msix\"[^>]*>\s*🖥️ Windows MSIX ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(rf"(Windows 11 Desktop ){ver_num}"), rf"\g<1>v{clean_ver}"),
            (re.compile(r'("name":\s*"Vixz Desktop"[\s\S]{0,400}?"softwareVersion":\s*")[^"]+(")'), rf"\g<1>{clean_ver}\g<2>"),
            (re.compile(rf"(Vixz Desktop Windows MSIX \(){ver_num}(\))"), rf"\g<1>v{clean_ver}\g<2>"),
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Viguru24 release metadata & sitemap.")
    parser.add_argument("--dry-run", action="store_true", help="Print detected versions and planned updates without writing files.")
    parser.add_argument("--ping-indexnow", action="store_true", help="Submit sitemap URLs to IndexNow when changes occur.")
    args = parser.parse_args()

    file_replacements: dict[str, list[tuple[re.Pattern[str], str]]] = {}

    for t in TARGETS:
        res = fetch_latest_release(t["repo"], t["asset_regex"])
        if not res:
            continue
        tag, dl_url = res
        clean_ver = tag.lstrip("v").removesuffix("-mac")
        print(f"[OK] {t['repo']:24} latest={tag:12} asset={dl_url.rsplit('/', 1)[-1]}")

        url_re = re.compile(
            rf'https://github\.com/{OWNER}/{re.escape(t["repo"])}/releases/download/[^/"\s)]+/[^"\s)]*{t["asset_regex"].replace("^", "")}'
        )
        scoped = build_scoped_patterns(t["repo"], clean_ver)
        for rel_file in t["files"]:
            file_replacements.setdefault(rel_file, []).append((url_re, dl_url))
            file_replacements[rel_file].extend(scoped)

    changed_any = False
    for rel_file, repls in file_replacements.items():
        if sync_file(ROOT / rel_file, repls, args.dry_run):
            changed_any = True

    if changed_any:
        today = dt.date.today().isoformat()
        sync_file(
            ROOT / "sitemap.xml",
            [(re.compile(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>"), f"<lastmod>{today}</lastmod>")],
            args.dry_run,
        )

    if args.ping_indexnow and (changed_any or args.dry_run):
        urls = [
            "https://viguru24.github.io/",
            "https://viguru24.github.io/cosmo-symphony/",
            "https://viguru24.github.io/vixz/",
            "https://viguru24.github.io/cosmowhisper/",
            "https://viguru24.github.io/kin-tracker/",
            "https://viguru24.github.io/cosmo-compendium/",
        ]
        ping_indexnow("viguru24.github.io", urls, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
