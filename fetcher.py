import tomllib
import requests
import pandas as pd
import os
import json
from pathlib import Path
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

_cfg_path = Path(__file__).parent / "config.toml"
with open(_cfg_path, "rb") as _f:
    _cfg = tomllib.load(_f)

BASE_URL = _cfg["api"]["base_url"]
SORT_FIELD = _cfg["api"]["sort_field"]
REVERSE_SORT = str(_cfg["api"]["reverse_sort"]).lower()
CACHE_DIR = _cfg["cache"]["directory"]

os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_filename(query: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    safe_query = query.replace(" ", "_").lower()
    return os.path.join(CACHE_DIR, f"{safe_query}_{today}.json")


def load_from_cache(query: str) -> pd.DataFrame | None:
    filepath = get_cache_filename(query)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))
    return None


def save_to_cache(query: str, projects: list) -> None:
    filepath = get_cache_filename(query)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


@retry(
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _fetch_page(headers: dict, params: dict) -> list:
    response = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
    if response.status_code == 429:
        raise requests.exceptions.RequestException("Rate limited (429)")
    if response.status_code != 200:
        raise requests.exceptions.RequestException(
            f"HTTP {response.status_code}: {response.text[:200]}"
        )
    return response.json().get("result", {}).get("projects", [])


def fetch_projects(
    auth_token: str,
    query: str = "",
    limit: int = 20,
    max_price: int = 100,
    pages: int = 3,
    refresh_cache: bool = False,
    countries: list | None = None,
    languages: list | None = None,
) -> pd.DataFrame:

    if not refresh_cache:
        cached = load_from_cache(query)
        if cached is not None:
            return cached

    all_projects: list = []

    headers = {
        "freelancer-auth-v2": auth_token,
        "freelancer-app-name": "main",
        "freelancer-app-platform": "web",
        "Accept": "application/json",
    }

    for page in range(pages):
        params: dict = {
            "query": query,
            "limit": limit,
            "offset": page * limit,
            "full_description": "true",
            "job_details": "true",
            "owner_info": "true",
            "sort_field": SORT_FIELD,
            "reverse_sort": REVERSE_SORT,
            "max_price": max_price,
            "project_types[]": "fixed",
        }
        if countries:
            params["countries[]"] = countries
        if languages:
            params["languages[]"] = languages

        try:
            projects = _fetch_page(headers, params)
        except requests.exceptions.RequestException as e:
            print(f"Page {page} failed after retries: {e}")
            break

        if not projects:
            break
        all_projects.extend(projects)

    if all_projects:
        save_to_cache(query, all_projects)

    return pd.DataFrame(all_projects)
