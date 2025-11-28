import json
import os
from datetime import datetime

import pytz

from logger import get_logger
from onboard_system.automated_reporting.settings import LOCAL_TZ_NAME

LOCAL_TZ = pytz.timezone(LOCAL_TZ_NAME)

logger = get_logger(__name__)


def calculate_risk_score_illegal_species(
    counts_by_species_with_risk_features: list,
    risk_score_path: str,
) -> dict:
    """Calculate the aggregated risk score for the day based on illegal species risk features.

    Rules:
      - For an illegal species:
          * If any catch was retained → risk 3.
          * If all catches were discarded → risk 2.
      - If no illegal species were caught → risk 1.
    Aggregated risk is the maximum across species.

    Args:
        counts_by_species_with_risk_features (list): A list of dictionaries, each containing:
            - "fao_code": The FAO code of the species.
            - "RETAINED": Count of retained catches.
            - "VESSEL_DISCARD": Count of discarded catches.
            - "is_illegal": Boolean indicating if the species is in the illegal species list.
        risk_score_path (str): The path to save the risk score file.

    Returns:
        dict: A dictionary containing:
            - "risk_score": int, the highest risk score across species.
            - "illegal_retained_catches": int, the sum of retained catches from illegal species.
            - "illegal_discarded_catches": int, the sum of discarded catches from illegal species.
            - "illegal_species_retained": list of FAO codes for illegal species with retained catches.
    """
    aggregated_score = None

    illegal_retained_catches = 0
    illegal_discarded_catches = 0
    illegal_species_retained = []

    for species in counts_by_species_with_risk_features:
        risk = 1
        fao_code = species.get("fao_code")
        retained = species.get("RETAINED", 0)
        discarded = species.get("VESSEL_DISCARD", 0) + species.get("WATER_DISCARD", 0)
        is_illegal = species.get("is_illegal", False)

        # For illegal species:
        if is_illegal:
            illegal_retained_catches += retained
            illegal_discarded_catches += discarded
            if retained > 0:
                risk = 3
                illegal_species_retained.append(fao_code)
            else:  # retained == 0 (all discarded)
                risk = 2

        if aggregated_score is None:
            aggregated_score = 1
        else:
            aggregated_score = max(aggregated_score, risk)

    today_date = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    risk_dict = {
        "date": today_date,
        "risk_score": aggregated_score,
        "illegal_retained_catches": illegal_retained_catches,
        "illegal_discarded_catches": illegal_discarded_catches,
        "illegal_species_retained": illegal_species_retained,
    }
    logger.info(f"Risk score based on illegal species: {risk_dict}")

    risk_score_illegal_species_file = os.path.join(
        risk_score_path, "risk_score_illegal_species.json"
    )

    with open(risk_score_illegal_species_file, "w") as f:
        json.dump(risk_dict, f, indent=4)

    logger.info(f"Risk score data saved to {risk_score_illegal_species_file}")
    return risk_dict
