import pandas as pd


def load_data(file):
    import json

    data = json.load(file)

    # Handle different possible structures
    if isinstance(data, dict):
        # Case: {"result": {"projects": [...]}}
        if "result" in data and "projects" in data["result"]:
            data = data["result"]["projects"]
        # Case: {"projects": [...]}
        elif "projects" in data:
            data = data["projects"]
        else:
            # fallback: take values
            data = list(data.values())

    return pd.DataFrame(data)


def normalize_data(df):
    # Ensure columns exist safely
    def safe_get(d, key, default=0):
        if isinstance(d, dict):
            return d.get(key, default)
        return default

    # Budget
    if "budget" in df.columns:
        df["budget_min"] = df["budget"].apply(lambda x: safe_get(x, "minimum", 0))
        df["budget_max"] = df["budget"].apply(lambda x: safe_get(x, "maximum", 0))
    else:
        df["budget_min"] = 0
        df["budget_max"] = 0

    # Bids
    if "bid_stats" in df.columns:
        df["bid_count"] = df["bid_stats"].apply(lambda x: safe_get(x, "bid_count", 0))
    else:
        df["bid_count"] = 0

    # Client verification
    if "owner_info" in df.columns:
        df["client_verified"] = df["owner_info"].apply(
            lambda x: (
                safe_get(x.get("status", {}), "payment_verified", False)
                if isinstance(x, dict)
                else False
            )
        )
    else:
        df["client_verified"] = False

    # Skills
    if "jobs" in df.columns:
        df["skills_list"] = df["jobs"].apply(
            lambda jobs: (
                [j.get("name", "") for j in jobs] if isinstance(jobs, list) else []
            )
        )
    else:
        df["skills_list"] = [[] for _ in range(len(df))]

    # Title safety
    if "title" not in df.columns:
        df["title"] = "No Title"

    # Description safety
    if "description" not in df.columns:
        df["description"] = ""

    return df
