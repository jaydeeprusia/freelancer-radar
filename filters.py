def apply_filters(df, keyword_filter, min_budget, max_bids, min_score):
    if keyword_filter:
        df = df[df['skills_list'].apply(
            lambda skills: any(keyword.lower() in [s.lower() for s in skills] for keyword in keyword_filter)
        )]

    df = df[df['budget_max'] >= min_budget]
    df = df[df['bid_count'] <= max_bids]
    df = df[df['score'] >= min_score]

    return df