from forex_python.converter import CurrencyRates
from datetime import datetime, timedelta

_currency_cache = {}
_cache_duration = timedelta(hours=1)
BEST_PRICE = 500  # USD
GOOD_PRICE = 250  # USD
FAIR_PRICE = 100  # USD


def skill_match_score(skills, keywords):
    if not skills:
        return 0
    matches = sum(1 for s in skills if s.lower() in keywords)
    return min(matches * 10, 40)


def budget_score(min_budget, max_budget, currency_code="USD"):
    c = CurrencyRates()
    conversion_factor = 1.0
    if currency_code != "USD":
        cache_key = f"{currency_code}_to_USD"
        current_time = datetime.now()

        if (
            cache_key in _currency_cache
            and current_time - _currency_cache[cache_key]["timestamp"] < _cache_duration
        ):
            conversion_factor = _currency_cache[cache_key]["rate"]
        else:
            try:
                conversion_factor = c.get_rate(currency_code, "USD")
                # Cache the rate with current timestamp
                _currency_cache[cache_key] = {
                    "rate": conversion_factor,
                    "timestamp": current_time,
                }
            except:
                # Fallback to hardcoded rates if forex_python fails
                if currency_code == "EUR":
                    conversion_factor = 1.1
                elif currency_code == "GBP":
                    conversion_factor = 1.25
                elif currency_code == "CAD":
                    conversion_factor = 0.75
                elif currency_code == "AUD":
                    conversion_factor = 0.65

    # Convert budget to USD equivalent for consistent scoring
    converted_min = min_budget * conversion_factor
    converted_max = max_budget * conversion_factor
    avg = (converted_min + converted_max) / 2

    if avg > BEST_PRICE:
        return 20
    elif avg > GOOD_PRICE:
        return 12
    elif avg > FAIR_PRICE:
        return 6
    return 2


def competition_score(bids):
    if bids < 5:
        return 20
    elif bids < 15:
        return 10
    return 3


def client_score(verified):
    return 20 if verified else 5


def calculate_score(row, keywords):
    score = 0
    score += skill_match_score(row["skills_list"], keywords)
    score += budget_score(row["budget_min"], row["budget_max"], row["currency_code"])
    score += competition_score(row["bid_count"])
    score += client_score(row["client_verified"])
    return score


def decision(score):
    if score >= 70:
        return "BID"
    elif score >= 50:
        return "CONSIDER"
    return "SKIP"
