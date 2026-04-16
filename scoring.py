import tomllib
from pathlib import Path
from datetime import datetime, timedelta
from forex_python.converter import CurrencyRates

# ── Load config ───────────────────────────────────────────────────────────────
_cfg_path = Path(__file__).parent / "config.toml"
with open(_cfg_path, "rb") as _f:
    _cfg = tomllib.load(_f)

_sc  = _cfg["scoring"]
_bt  = _sc["budget_tiers"]
_ct  = _sc["competition_tiers"]
_ft  = _sc["freshness_tiers"]
_cq  = _sc["client_quality"]
_cx  = _sc["complexity"]
_ins = _sc["insights"]

THRESHOLD_BID      = _sc["threshold_bid"]
THRESHOLD_CONSIDER = _sc["threshold_consider"]

DEFAULT_WEIGHTS    = dict(_sc["weights"])
COMPLEXITY_KEYWORDS: list[str] = _cx["keywords"]

_fx_cache: dict = {}
_cache_ttl = timedelta(hours=1)


def _get_usd_rate(currency_code: str) -> float:
    if currency_code in ("USD", "NA", None):
        return 1.0
    key = f"{currency_code}_USD"
    entry = _fx_cache.get(key)
    if entry and datetime.now() - entry["ts"] < _cache_ttl:
        return entry["rate"]
    try:
        rate = float(CurrencyRates().get_rate(currency_code, "USD"))
        _fx_cache[key] = {"rate": rate, "ts": datetime.now()}
        return rate
    except Exception:
        fallback = {"EUR": 1.1, "GBP": 1.25, "CAD": 0.75, "AUD": 0.65, "INR": 0.012}
        return fallback.get(currency_code, 1.0)


# ── Component scorers (each returns 0–100) ────────────────────────────────────

def skill_score(row, keywords: list[str]) -> float:
    skills = row.get("skills_list", [])
    if not skills or not keywords:
        return 0.0
    matches = sum(1 for s in skills if s.lower() in keywords)
    return min(matches / max(len(keywords), 1), 1.0) * 100


def budget_score(row) -> float:
    avg_usd = row.get("avg_budget_usd", 0)
    if avg_usd <= 0:
        rate = _get_usd_rate(row.get("currency_code", "USD"))
        avg_usd = ((row.get("budget_min", 0) + row.get("budget_max", 0)) / 2) * rate
    if avg_usd >= _bt["excellent"]: return 100.0
    if avg_usd >= _bt["good"]:      return 75.0
    if avg_usd >= _bt["fair"]:      return 50.0
    if avg_usd >= _bt["low"]:       return 25.0
    return 10.0


def competition_score(row) -> float:
    bids = row.get("bid_count", 0)
    if bids <= _ct["excellent"]: return 100.0
    if bids <= _ct["good"]:      return 80.0
    if bids <= _ct["fair"]:      return 50.0
    if bids <= _ct["low"]:       return 25.0
    return 10.0


def client_quality_score(row) -> float:
    score = 0.0
    if row.get("client_verified"):
        score += _cq["verified_bonus"]
    rep = row.get("client_reputation", 0.0) or 0.0
    score += min(rep / 5.0, 1.0) * _cq["reputation_max"]
    age = row.get("client_account_age_days", 0) or 0
    if age > _cq["age_senior_days"]:
        score += _cq["age_senior_bonus"]
    elif age > _cq["age_junior_days"]:
        score += _cq["age_junior_bonus"]
    return min(score, 100.0)


def urgency_score(row) -> float:
    score = 0.0
    if row.get("flag_urgent"):   score += 60.0
    if row.get("flag_featured"): score += 25.0
    if row.get("flag_premium"):  score += 15.0
    return min(score, 100.0)


def freshness_score(row) -> float:
    hrs = row.get("time_since_posted_hrs", 999)
    if hrs <= _ft["excellent"]: return 100.0
    if hrs <= _ft["good"]:      return 80.0
    if hrs <= _ft["fair"]:      return 60.0
    if hrs <= _ft["low"]:       return 30.0
    return 10.0


def complexity_score(row) -> float:
    desc = (row.get("description") or "").lower()
    hits = sum(1 for kw in COMPLEXITY_KEYWORDS if kw in desc)
    length_bonus  = min(len(desc) / _cx["description_length_target"], 1.0) * 30
    keyword_bonus = min(hits / _cx["keyword_hits_target"], 1.0) * 70
    return min(keyword_bonus + length_bonus, 100.0)


# ── Master scorer ─────────────────────────────────────────────────────────────

def calculate_score(row, keywords: list[str], weights: dict | None = None, enabled: dict | None = None) -> float:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    e = enabled or {k: True for k in DEFAULT_WEIGHTS}

    components = {
        "skill":       skill_score(row, keywords),
        "budget":      budget_score(row),
        "competition": competition_score(row),
        "client":      client_quality_score(row),
        "urgency":     urgency_score(row),
        "freshness":   freshness_score(row),
        "complexity":  complexity_score(row),
    }

    active = {k: v for k, v in w.items() if e.get(k, True)}
    total_weight = sum(active.values())
    if total_weight == 0:
        return 0.0

    return round(sum((active[k] / total_weight) * components[k] for k in active), 1)


def get_component_scores(row, keywords: list[str]) -> dict:
    return {
        "skill":       round(skill_score(row, keywords), 1),
        "budget":      round(budget_score(row), 1),
        "competition": round(competition_score(row), 1),
        "client":      round(client_quality_score(row), 1),
        "urgency":     round(urgency_score(row), 1),
        "freshness":   round(freshness_score(row), 1),
        "complexity":  round(complexity_score(row), 1),
    }


def decision(score: float) -> str:
    if score >= THRESHOLD_BID:      return "BID"
    if score >= THRESHOLD_CONSIDER: return "CONSIDER"
    return "SKIP"


def generate_insights(row) -> tuple[list[str], list[str]]:
    good, risks = [], []

    if row.get("bid_count", 99) <= _ins["low_competition_bids"]:
        good.append("Low competition")
    if row.get("client_verified"):
        good.append("Payment verified client")
    if row.get("avg_budget_usd", 0) >= _ins["decent_budget_usd"]:
        good.append("Decent budget")
    if row.get("client_reputation", 0) >= _ins["high_rating_threshold"]:
        good.append(f"High client rating ({row['client_reputation']:.1f}/5)")
    if row.get("time_since_posted_hrs", 999) <= _ins["fresh_hours"]:
        good.append("Fresh project")
    if row.get("flag_urgent"):
        good.append("Marked urgent")
    if row.get("flag_featured"):
        good.append("Featured listing")
    if row.get("client_account_age_days", 0) >= 365:
        good.append("Established client account")

    if not row.get("client_verified"):
        risks.append("Payment not verified")
    if row.get("bid_count", 0) > _ins["high_competition_bids"]:
        risks.append(f"High competition ({row['bid_count']} bids)")
    if row.get("avg_budget_usd", 0) < _ins["very_low_budget_usd"]:
        risks.append("Very low budget")
    if row.get("client_account_age_days", 999) < _ins["new_account_days"]:
        risks.append("Brand new client account")
    if row.get("client_reputation", 1) == 0.0:
        risks.append("No client reviews")
    if row.get("flag_nda"):
        risks.append("NDA required")
    if row.get("bid_velocity", 0) > _ins["high_velocity"]:
        risks.append("Rapidly attracting bids")

    return good, risks
