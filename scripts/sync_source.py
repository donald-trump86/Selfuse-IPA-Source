import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("source_sync")

CONFIG_PATH = "config/apps.json"
OUTPUT_SOURCE_PATH = "source.json"

SOURCE_METADATA = {
    "$schema": "https://github.com/SideStore/sidestore-source-types/raw/main/schema.json",
    "name": "Selfuse IPA Source",
    "identifier": "com.donald-trump86.sidestore-source",
    "subtitle": "Personal Auto-updated App Repository",
    "description": "Auto-updated SideStore source maintained by donald-trump86.",
    "iconURL": "https://raw.githubusercontent.com/SideStore/SideStore/main/SideStore/Assets.xcassets/AppIcon.appiconset/Icon-60%403x.png",
    "website": "https://github.com/donald-trump86/Selfuse-IPA-Source"
}

def get_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SideStore-Sync-Bot"
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def extract_app_version(tag_name: str, asset_name: str, custom_pattern: Optional[str] = None) -> str:
    if custom_pattern:
        match = re.search(custom_pattern, tag_name) or re.search(custom_pattern, asset_name)
        if match:
            return match.group(1) if match.groups() else match.group(0)

    # SideStore matches version against CFBundleShortVersionString in the IPA Info.plist.
    # Match standard major.minor or major.minor.patch version from asset filename or tag
    match_asset = re.search(r"(\d+\.\d+(?:\.\d+)?)", asset_name)
    if match_asset:
        return match_asset.group(1)

    match_tag = re.search(r"(\d+\.\d+(?:\.\d+)?)", tag_name)
    if match_tag:
        return match_tag.group(1)

    cleaned = tag_name.strip()
    cleaned = re.sub(r"^[vV]", "", cleaned)
    cleaned = re.sub(r"[\(\)]", "", cleaned)
    return cleaned

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    emoji_pattern = re.compile(r"[\U00010000-\U0010FFFF\u2600-\u26FF\u2700-\u27BF]", flags=re.UNICODE)
    cleaned = emoji_pattern.sub("", text)
    cleaned = cleaned.strip()
    if len(cleaned) > 800:
        cleaned = cleaned[:800] + "..."
    return cleaned

def fetch_releases(repo: str) -> List[Dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if resp.status_code == 200:
        return resp.json()

    url_latest = f"https://api.github.com/repos/{repo}/releases/latest"
    resp_latest = requests.get(url_latest, headers=get_headers(), timeout=30)
    if resp_latest.status_code == 200:
        return [resp_latest.json()]

    resp.raise_for_status()
    return []

def find_matching_asset(release: Dict[str, Any], pattern_str: str) -> Optional[Dict[str, Any]]:
    pattern = re.compile(pattern_str, re.IGNORECASE)
    for asset in release.get("assets", []):
        if pattern.search(asset.get("name", "")):
            return asset
    return None

def process_app(app_conf: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = app_conf["name"]
    repo = app_conf["repo"]
    pattern_str = app_conf.get("assetPattern", r".*\.ipa$")
    custom_ver_pattern = app_conf.get("versionPattern")
    logger.info("Synchronizing app: %s (Repo: %s)", name, repo)

    try:
        releases = fetch_releases(repo)
        if not releases:
            logger.warning("No releases found for %s (%s).", name, repo)
            return None

        target_release = None
        target_asset = None
        valid_versions = []

        for rel in releases:
            if rel.get("draft"):
                continue
            asset = find_matching_asset(rel, pattern_str)
            if asset:
                if not target_release:
                    target_release = rel
                    target_asset = asset

                ver_str = extract_app_version(rel.get("tag_name", "1.0.0"), asset.get("name", ""), custom_ver_pattern)
                ver_date = rel.get("published_at") or rel.get("created_at") or ""
                ver_desc = sanitize_text(rel.get("body") or "")

                valid_versions.append({
                    "version": ver_str,
                    "date": ver_date,
                    "downloadURL": asset["browser_download_url"],
                    "size": asset.get("size", 0),
                    "localizedDescription": ver_desc
                })

        if not target_release or not target_asset:
            logger.warning("No matching .ipa asset found for %s (%s).", name, repo)
            return None

        latest_version = extract_app_version(
            target_release.get("tag_name", "1.0.0"),
            target_asset.get("name", ""),
            custom_ver_pattern
        )
        latest_date = target_release.get("published_at") or target_release.get("created_at") or ""
        latest_desc = sanitize_text(target_release.get("body") or "")

        app_data: Dict[str, Any] = {
            "name": name,
            "bundleIdentifier": app_conf["bundleIdentifier"],
            "developerName": app_conf.get("developerName", repo.split("/")[0]),
            "subtitle": app_conf.get("subtitle", ""),
            "version": latest_version,
            "versionDate": latest_date,
            "versionDescription": latest_desc,
            "downloadURL": target_asset["browser_download_url"],
            "localizedDescription": app_conf.get("localizedDescription", ""),
            "iconURL": app_conf.get("iconURL", ""),
            "tintColor": app_conf.get("tintColor", "007AFF"),
            "size": target_asset.get("size", 0),
            "versions": valid_versions[:5]
        }

        logger.info("Successfully fetched %s version %s (%s)", name, latest_version, target_asset["name"])
        return app_data

    except Exception as e:
        logger.error("Failed to parse %s (%s): %s", name, repo, e)
        return None

def main():
    if not os.path.exists(CONFIG_PATH):
        logger.error("Config file not found: %s", CONFIG_PATH)
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        app_configs = json.load(f)

    apps_data = []
    for conf in app_configs:
        app_result = process_app(conf)
        if app_result:
            apps_data.append(app_result)

    final_source = {
        **SOURCE_METADATA,
        "apps": apps_data,
        "news": []
    }

    with open(OUTPUT_SOURCE_PATH, "w", encoding="utf-8") as f:
        json.dump(final_source, f, ensure_ascii=False, indent=2)

    logger.info("Successfully generated %s containing %d apps.", OUTPUT_SOURCE_PATH, len(apps_data))

if __name__ == "__main__":
    main()
