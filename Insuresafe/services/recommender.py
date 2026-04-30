"""
    Fetch policies from MongoDB and recommend based on age, income, and affordability.
    Scoring:
      - Closeness to policy's ideal age and income midpoint.
      - Penalize if existing premium or policy count is high.
    Returns top 5 recommended policies with their names and scores.
    """
def calculate_risk_level(annual_income, existing_premiums):
    """
    Calculate risk level based on premium burden
    """

    if annual_income <= 0:
        return "High", 1

    ratio = existing_premiums / annual_income

    if ratio < 0.20:
        return "Low", 5

    elif ratio < 0.40:
        return "Medium", 3

    else:
        return "High", 1


def recommend_policies(
    age,
    annual_income,
    existing_premiums=0,
    existing_policy_count=0,
    max_total_premium=100000
):
    from db import policies_col

    # --------------------------------
    # Risk Calculation
    # --------------------------------
    risk_level, max_allowed_policies = calculate_risk_level(
        annual_income,
        existing_premiums
    )

    # HARD BLOCK
    if existing_policy_count >= max_allowed_policies:
        return []

    try:
        policies = list(policies_col.find())
    except Exception:
        return []

    category_best = {}

    for p in policies:
        min_age = p.get("min_age", 0)
        max_age = p.get("max_age", 100)
        min_inc = p.get("min_income", 0)
        max_inc = p.get("max_income", 10**12)
        premium = p.get("premium_amount", 0)
        category = p.get("category", "General")

        # Eligibility Check
        if not (
            min_age <= age <= max_age and
            min_inc <= annual_income <= max_inc
        ):
            continue

        # Expensive policy block
        if existing_premiums + premium > max_total_premium:
            continue

        # Score Calculation
        count_penalty = max(
            0.7,
            1.0 - 0.05 * existing_policy_count
        )

        age_mid = (min_age + max_age) / 2
        inc_mid = (min_inc + max_inc) / 2

        age_range = (max_age - min_age) or 1
        inc_range = (max_inc - min_inc) or 1

        age_score = 1 - abs(age - age_mid) / age_range
        inc_score = 1 - abs(annual_income - inc_mid) / inc_range

        total_score = max(
            0,
            (age_score + inc_score) * count_penalty
        )

        policy_data = {
            "name": p.get("name", "Unnamed Policy"),
            "score": round(total_score, 3),
            "category": category,
            "risk_level": risk_level
        }

        # Keep only best policy per category
        if (
            category not in category_best or
            total_score > category_best[category]["score"]
        ):
            category_best[category] = policy_data

    # Final output = Top 1 per category
    recommendations = list(category_best.values())

    recommendations.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return recommendations[:5]