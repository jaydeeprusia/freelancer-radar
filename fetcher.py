import tomllib
import requests
import pandas as pd
import os
import json
from pathlib import Path
from datetime import datetime

_cfg_path = Path(__file__).parent / "config.toml"
with open(_cfg_path, "rb") as _f:
    _cfg = tomllib.load(_f)

BASE_URL  = _cfg["api"]["base_url"]
SORT_FIELD   = _cfg["api"]["sort_field"]
REVERSE_SORT = str(_cfg["api"]["reverse_sort"]).lower()
CACHE_DIR    = _cfg["cache"]["directory"]

os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_filename(query):
    today = datetime.now().strftime("%Y-%m-%d")
    safe_query = query.replace(" ", "_").lower()
    return os.path.join(CACHE_DIR, f"{safe_query}_{today}.json")


def load_from_cache(query):
    filepath = get_cache_filename(query)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return pd.DataFrame(data)
    return None


def save_to_cache(query, projects):
    filepath = get_cache_filename(query)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


def fetch_projects(
    auth_token, query="", limit=20, max_price=100, pages=3, refresh_cache=False,
    countries=None, languages=None
):

    # 🔁 Try cache first
    if not refresh_cache:
        cached_df = load_from_cache(query)
        if cached_df is not None:
            print("Loaded from cache")
            return cached_df

    all_projects = []

    headers = {
        "freelancer-auth-v2": auth_token,
        "freelancer-app-name": "main",
        "freelancer-app-platform": "web",
        "Accept": "application/json",
    }

    for page in range(pages):
        params = {
            "query": query,
            "limit": limit,
            "offset": page * limit,
            "full_description": "true",
            "job_details": "true",
            "owner_info": "true",
            "sort_field": SORT_FIELD,
            "reverse_sort": REVERSE_SORT,
            "max_price": max_price,
        }

        if countries:
            params["countries[]"] = countries
        if languages:
            params["languages[]"] = languages
        
        params["project_types[]"] = "fixed"  # Only fixed-price projects for now

        response = requests.get(BASE_URL, headers=headers, params=params)

        if response.status_code != 200:
            print("Error:", response.text)
            break

        data = response.json()
        projects = data.get("result", {}).get("projects", [])

        if not projects:
            break

        all_projects.extend(projects)

    # 💾 Save cache
    if all_projects:
        save_to_cache(query, all_projects)

    return pd.DataFrame(all_projects)
