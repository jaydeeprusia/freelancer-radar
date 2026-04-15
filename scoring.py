def skill_match_score(skills, keywords):
    if not skills:
        return 0
    matches = sum(1 for s in skills if s.lower() in keywords)
    return min(matches * 10, 40)


def budget_score(min_budget, max_budget):
    avg = (min_budget + max_budget) / 2
    if avg > 1500:
        return 20
    elif avg > 500:
        return 12
    elif avg > 100:
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
    score += budget_score(row["budget_min"], row["budget_max"])
    score += competition_score(row["bid_count"])
    score += client_score(row["client_verified"])
    return score


def decision(score):
    if score >= 70:
        return "BID"
    elif score >= 50:
        return "CONSIDER"
    return "SKIP"
