# scorer.py
"""
Scoring utilities for ranking hotels/destinations/travel options.
"""

def tag_match_score(item_tags, user_tags):
    if not item_tags or not user_tags:
        return 0.0
    matches = sum(1 for t in item_tags if t in user_tags)
    return matches / max(1, len(user_tags))

def budget_score(price, budget):
    if not budget:
        return 0.5
    mn = budget.get("min", 0)
    mx = budget.get("max", price or 1)
    if mn <= price <= mx:
        return 1.0
    diff = min(abs(price - mx), abs(price - mn))
    denom = mx if mx else price or 1
    return max(0.0, 1 - (diff / denom))

def past_similarity_score(item_tags, past_trips):
    if not past_trips or not item_tags:
        return 0.0
    past_tags = []
    for t in past_trips:
        past_tags.extend(t.get("tags", []))
    if not past_tags:
        return 0.0
    matches = sum(1 for tag in item_tags if tag in past_tags)
    return matches / max(1, len(set(past_tags)))

def score_item(item, user_profile, signals=None, user_past_trips=None):
    """
    item: hotel or destination dict (with 'tags', 'price' or 'avg_price')
    user_profile: {interests:[], budget:{min,max}}
    signals: optional dict from search parsing, e.g. {'recentBehaviorMatch':True, 'search_budget_max':12000, 'tags':[...]}
    user_past_trips: list of past_trips
    """
    # weights (tunable)
    w_tag = 1.3
    w_budget = 1.0
    w_pop = 0.5
    w_recency = 0.7
    w_past = 0.9

    tag_score = tag_match_score(item.get("tags", []), user_profile.get("interests", []))
    b_score = budget_score(item.get("price", item.get("avg_price", 0)), user_profile.get("budget", {}))
    popularity = item.get("popularity", 0.5)
    recency = 1.0 if signals and signals.get("recentBehaviorMatch") else 0.0
    past_score = past_similarity_score(item.get("tags", []), user_past_trips or [])

    # apply search budget constraint if present
    if signals and signals.get("search_budget_max") and item.get("price"):
        if item["price"] > signals["search_budget_max"]:
            b_score *= 0.6

    score = (w_tag * tag_score) + (w_budget * b_score) + (w_pop * popularity) + (w_recency * recency) + (w_past * past_score)
    return score
