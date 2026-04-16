import pytest
from scoring import (
    skill_score, budget_score, competition_score,
    client_quality_score, urgency_score, freshness_score,
    complexity_score, calculate_score, decision,
)


def row(**kwargs):
    defaults = {
        "skills_list": [], "avg_budget_usd": 0, "budget_min": 0, "budget_max": 0,
        "currency_code": "USD", "bid_count": 0, "client_verified": False,
        "client_reputation": 0.0, "client_account_age_days": 0,
        "flag_urgent": False, "flag_featured": False, "flag_premium": False,
        "time_since_posted_hrs": 999, "description": "", "bid_velocity": 0,
    }
    return {**defaults, **kwargs}


# ── skill_score ───────────────────────────────────────────────────────────────

def test_skill_score_empty_skills():
    assert skill_score(row(), ["python"]) == 0.0

def test_skill_score_empty_keywords():
    assert skill_score(row(skills_list=["Python"]), []) == 0.0

def test_skill_score_exact_match():
    assert skill_score(row(skills_list=["Python", "API"]), ["python"]) > 0

def test_skill_score_fuzzy_match():
    # "automation" should fuzzy-match "automate"
    assert skill_score(row(skills_list=["Automate"]), ["automation"]) > 0

def test_skill_score_partial_match():
    # "web-automation" contains "automation"
    assert skill_score(row(skills_list=["web-automation"]), ["automation"]) > 0

def test_skill_score_no_match():
    assert skill_score(row(skills_list=["Photoshop"]), ["python", "api"]) == 0.0


# ── budget_score ──────────────────────────────────────────────────────────────

def test_budget_score_zero():
    assert budget_score(row(avg_budget_usd=0)) == 10.0

def test_budget_score_excellent():
    assert budget_score(row(avg_budget_usd=1000)) == 100.0

def test_budget_score_good():
    assert budget_score(row(avg_budget_usd=300)) == 75.0

def test_budget_score_fair():
    assert budget_score(row(avg_budget_usd=80)) == 50.0

def test_budget_score_low():
    assert budget_score(row(avg_budget_usd=20)) == 25.0


# ── competition_score ─────────────────────────────────────────────────────────

def test_competition_score_zero_bids():
    assert competition_score(row(bid_count=0)) == 100.0

def test_competition_score_many_bids():
    assert competition_score(row(bid_count=100)) == 10.0


# ── client_quality_score ──────────────────────────────────────────────────────

def test_client_quality_unverified_new():
    assert client_quality_score(row()) < 20.0

def test_client_quality_verified_senior():
    score = client_quality_score(row(client_verified=True, client_reputation=5.0, client_account_age_days=400))
    assert score == 100.0

def test_client_quality_verified_no_rep():
    score = client_quality_score(row(client_verified=True))
    assert score > 0


# ── urgency_score ─────────────────────────────────────────────────────────────

def test_urgency_score_none():
    assert urgency_score(row()) == 0.0

def test_urgency_score_urgent():
    assert urgency_score(row(flag_urgent=True)) == 60.0

def test_urgency_score_all_flags():
    assert urgency_score(row(flag_urgent=True, flag_featured=True, flag_premium=True)) == 100.0


# ── freshness_score ───────────────────────────────────────────────────────────

def test_freshness_score_very_fresh():
    assert freshness_score(row(time_since_posted_hrs=0.5)) == 100.0

def test_freshness_score_old():
    assert freshness_score(row(time_since_posted_hrs=500)) == 10.0


# ── complexity_score ──────────────────────────────────────────────────────────

def test_complexity_score_empty_desc():
    assert complexity_score(row(description="")) == 0.0

def test_complexity_score_with_keywords():
    assert complexity_score(row(description="build an api with automation and machine learning pipeline")) > 0


# ── calculate_score & decision ────────────────────────────────────────────────

def test_calculate_score_returns_float():
    r = row(skills_list=["Python"], avg_budget_usd=500, bid_count=3,
            client_verified=True, time_since_posted_hrs=2)
    score = calculate_score(r, ["python"])
    assert isinstance(score, float)
    assert 0 <= score <= 100

def test_calculate_score_all_disabled():
    r = row()
    enabled = {k: False for k in ["skill", "budget", "competition", "client", "urgency", "freshness", "complexity"]}
    assert calculate_score(r, ["python"], enabled=enabled) == 0.0

def test_decision_bid():
    assert decision(70) == "BID"

def test_decision_consider():
    assert decision(35) == "CONSIDER"

def test_decision_skip():
    assert decision(10) == "SKIP"
