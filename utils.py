from typing import Any
import json
import pandas as pd
from datetime import datetime, timezone
from forex_python.converter import CurrencyRates

_fx = CurrencyRates()
_fx_cache: dict = {}


def _to_usd(amount: float, currency_code: str, exchange_rate: float = 0.0) -> float:
    amt = float(amount)
    if not amt or currency_code in ("USD", "NA", None):
        return amt
    if exchange_rate and exchange_rate > 0:
        return amt * float(exchange_rate)
    cache_key = f"{currency_code}_USD"
    if cache_key in _fx_cache:
        return amt * float(_fx_cache[cache_key])
    try:
        rate = float(_fx.get_rate(currency_code, "USD"))
        _fx_cache[cache_key] = rate
        return amt * rate
    except Exception:
        return amt


def convert_to_currency(amount_usd: float, target_currency: str) -> float:
    if target_currency in ("USD", "NA", None):
        return amount_usd
    try:
        return float(_fx.convert("USD", target_currency, amount_usd))
    except Exception:
        return amount_usd


def load_data(file) -> pd.DataFrame:
    data = json.load(file)
    if isinstance(data, dict):
        if "result" in data and "projects" in data["result"]:
            data = data["result"]["projects"]
        elif "projects" in data:
            data = data["projects"]
        else:
            data = list(data.values())
    return pd.DataFrame(data)


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    def sg(d, key, default: Any = 0):
        return d.get(key, default) if isinstance(d, dict) else default

    now_ts = datetime.now(timezone.utc).timestamp()

    # ── Budget ──────────────────────────────────────────────────────────────
    if "budget" in df.columns:
        df["budget_min"] = df["budget"].apply(lambda x: sg(x, "minimum", 0))
        df["budget_max"] = df["budget"].apply(lambda x: sg(x, "maximum", 0))
    else:
        df["budget_min"] = df["budget_max"] = 0

    # ── Currency ─────────────────────────────────────────────────────────────
    if "currency" in df.columns:
        df["currency_code"] = df["currency"].apply(
            lambda x: sg(x, "code", "NA") if isinstance(x, dict) else "NA"
        )
        df["exchange_rate"] = df["currency"].apply(
            lambda x: sg(x, "exchange_rate", 0.0) if isinstance(x, dict) else 0.0
        )
    else:
        df["currency_code"] = "NA"
        df["exchange_rate"] = 0.0

    # ── USD-normalised budget ────────────────────────────────────────────────
    df["budget_min_usd"] = df.apply(
        lambda r: _to_usd(r["budget_min"], r["currency_code"], r["exchange_rate"]), axis=1
    )
    df["budget_max_usd"] = df.apply(
        lambda r: _to_usd(r["budget_max"], r["currency_code"], r["exchange_rate"]), axis=1
    )
    df["avg_budget_usd"] = (df["budget_min_usd"] + df["budget_max_usd"]) / 2

    # ── Bid stats ────────────────────────────────────────────────────────────
    if "bid_stats" in df.columns:
        df["bid_count"] = df["bid_stats"].apply(lambda x: sg(x, "bid_count", 0))
        df["bid_avg"]   = df["bid_stats"].apply(lambda x: sg(x, "bid_avg", 0.0))
    else:
        df["bid_count"] = df["bid_avg"] = 0

    # ── Owner / client info ──────────────────────────────────────────────────
    if "owner_info" in df.columns:
        df["client_verified"] = df["owner_info"].apply(
            lambda x: sg(sg(x, "status", {}), "payment_verified", False)
            if isinstance(x, dict) else False
        )
        df["client_country_code"] = df["owner_info"].apply(
            lambda x: sg(sg(x, "country", {}), "code", "NA")
            if isinstance(x, dict) else "NA"
        )
        df["client_reputation"] = df["owner_info"].apply(
            lambda x: sg(sg(sg(x, "reputation", {}), "entire_history", {}), "overall", 0.0)
            if isinstance(x, dict) else 0.0
        )
        df["client_account_age_days"] = df["owner_info"].apply(
            lambda x: max(0, (now_ts - sg(x, "registration_date", now_ts)) / 86400)
            if isinstance(x, dict) else 0
        )
    else:
        df["client_verified"]        = False
        df["client_country_code"]    = "NA"
        df["client_reputation"]      = 0.0
        df["client_account_age_days"] = 0

    # ── Upgrades / flags ─────────────────────────────────────────────────────
    if "upgrades" in df.columns:
        df["flag_featured"]  = df["upgrades"].apply(lambda x: bool(sg(x, "featured", False)))
        df["flag_urgent"]    = df["upgrades"].apply(lambda x: bool(sg(x, "urgent", False)))
        df["flag_nda"]       = df["upgrades"].apply(lambda x: bool(sg(x, "NDA", False)))
        df["flag_premium"]   = df["upgrades"].apply(lambda x: bool(sg(x, "premium", False)))
        df["flag_recruiter"] = df["upgrades"].apply(lambda x: sg(x, "recruiter", None) is not None)
    else:
        for col in ("flag_featured", "flag_urgent", "flag_nda", "flag_premium", "flag_recruiter"):
            df[col] = False

    # ── Skills ───────────────────────────────────────────────────────────────
    if "jobs" in df.columns:
        df["skills_list"] = df["jobs"].apply(
            lambda j: [x.get("name", "") for x in j] if isinstance(j, list) else []
        )
    else:
        df["skills_list"] = [[] for _ in range(len(df))]
    df["skill_count"] = df["skills_list"].apply(len)

    # ── Time fields ──────────────────────────────────────────────────────────
    submit_col = "time_submitted" if "time_submitted" in df.columns else "submitdate"
    if submit_col in df.columns:
        df["submit_ts"] = pd.to_numeric(df[submit_col], errors="coerce").fillna(now_ts)
    else:
        df["submit_ts"] = now_ts

    df["time_since_posted_hrs"] = ((now_ts - df["submit_ts"]) / 3600).clip(lower=0)
    df["submitdate"] = pd.to_datetime(df["submit_ts"], unit="s").dt.strftime("%Y-%m-%d %H:%M")

    # ── Bid velocity (bids per hour since posted) ────────────────────────────
    df["bid_velocity"] = df.apply(
        lambda r: r["bid_count"] / r["time_since_posted_hrs"]
        if r["time_since_posted_hrs"] > 0 else 0.0,
        axis=1,
    )

    # ── Location (from owner_info.country.code) ──────────────────────────────
    df["location_code"] = df["client_country_code"]

    # ── Language ─────────────────────────────────────────────────────────────
    if "language" not in df.columns:
        df["language"] = "NA"

    # ── Text fields ──────────────────────────────────────────────────────────
    if "title" not in df.columns:
        df["title"] = "No Title"
    if "description" not in df.columns:
        df["description"] = ""

    return df
