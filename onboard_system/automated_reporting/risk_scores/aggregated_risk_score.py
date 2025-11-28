from typing import Optional

from onboard_system.automated_reporting import settings

AGGREGATED_SCORE_MIN = settings.AGGREGATED_SCORE_MIN
AGGREGATED_SCORE_MAX = settings.AGGREGATED_SCORE_MAX
AGGREGATED_SCORE_ROUND_DECIMALS = settings.AGGREGATED_SCORE_ROUND_DECIMALS
AGGREGATED_RISK_WEIGHTS = settings.AGGREGATED_RISK_WEIGHTS


def calculate_aggregated_risk_score(
    risk_score_gps: dict,
    risk_score_illegal_species: dict,
    risk_score_elogs: dict,
    risk_score_model_underprediction: dict,
    risk_score_operational: dict,
) -> Optional[float]:
    """Compute an aggregated risk score normalized to [SCORE_MIN, SCORE_MAX].

    Each input dict must contain a numeric `"risk_score"`.
    A weighted sum of the component scores is computed using `AGGREGATED_RISK_WEIGHTS`, then
    linearly normalized back to the same scale and rounded to `AGGREGATED_SCORE_ROUND_DECIMALS`.

    Returns:
        float | None: The aggregated score, or None if any component is missing.
    """
    scores = {
        "gps": risk_score_gps.get("risk_score"),
        "illegal_species": risk_score_illegal_species.get("risk_score"),
        "elogs": risk_score_elogs.get("risk_score"),
        "model_underprediction": risk_score_model_underprediction.get("risk_score"),
        "operational": risk_score_operational.get("risk_score"),
    }

    if any(v is None for v in scores.values()):
        return None

    weights = AGGREGATED_RISK_WEIGHTS
    min_weighted = sum(AGGREGATED_SCORE_MIN * weights[k] for k in scores)
    max_weighted = sum(AGGREGATED_SCORE_MAX * weights[k] for k in scores)

    raw_weighted = sum(float(scores[k]) * weights[k] for k in scores)

    denom = max_weighted - min_weighted
    if denom == 0:
        return float(AGGREGATED_SCORE_MIN)

    normalized = AGGREGATED_SCORE_MIN + (
        (AGGREGATED_SCORE_MAX - AGGREGATED_SCORE_MIN) * (raw_weighted - min_weighted) / denom
    )

    return round(normalized, AGGREGATED_SCORE_ROUND_DECIMALS)
