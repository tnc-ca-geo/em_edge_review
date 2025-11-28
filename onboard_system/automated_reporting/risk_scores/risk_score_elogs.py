import json
import os
from datetime import datetime

import pandas as pd
import pytz

from logger import get_logger
from onboard_system.automated_reporting import settings

logger = get_logger(__name__)
LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)

_OVER_LOW = settings.ELOGS_OVERPREDICTION_LOW_PERCENT / 100.0
_OVER_MED = settings.ELOGS_OVERPREDICTION_MED_PERCENT / 100.0
_UNDER_FLAG = settings.ELOGS_UNDERPREDICTION_FLAG_PERCENT / 100.0


def calculate_risk_score_elogs(  # noqa: PLR0912
    counts_by_species: list,
    elog_catch_df: pd.DataFrame,
    risk_score_path: str,
) -> dict:
    """Calculate the aggregated risk score for the day based on elog comparisson.

    As elogs report retained catch only, elog catches are compared against the retained catches predicted by the model.

    The rules are:
      - If the model's retained catch prediction is within ±_OVER_LOW of the elog value, then assign a risk score of 1 (Low)
      - If the model predicts _OVER_LOW%–_OVER_MED% more than what was logged in the elogs, then assign a risk score of 2 (Medium)
      - If the model predicts >_OVER_MED% more than what was logged, OR if there is no elog for that day, then assign a risk score of 3 (High).

    Args:
        counts_by_species (list): A list of dictionaries, each containing:
            - "fao_code": The FAO code of the species.
            - "RETAINED": Count of retained catches predicted by the model.
        elog_catch_df (pd.DataFrame): DataFrame containing the elog data with columns:
            - date: The date of the record.
            - utc_time: The time of the record in UTC.
            - species: The scientific name of the catch.
            - amount: The count of the catch.
            - fao_code: The FAO code of the catch.
        risk_score_path (str): The path to save the risk score file.

    Returns:
        dict: A dictionary containing:
            - "date": The date of the record.
            - "risk_score": int, the risk score for the day.
            - "catches_elogs": int, the total number of catches logged in elogs."
            - "catches_retained_model": int, the total number of retained catches predicted by the model."
            - "catches_difference": int, the difference between elogs and model predictions."
            - "underprediction_flag": bool, True if the model predicts less than elogs.
    """
    underprediction_flag = False

    catches_retained_model = int(sum(species.get("RETAINED", 0) for species in counts_by_species))

    if not elog_catch_df.empty:
        catches_elogs = int(elog_catch_df["amount"].sum())
    else:
        catches_elogs = 0

    if catches_elogs == 0:  # No elogs for the day
        if catches_retained_model == 0:
            risk_score = None
        else:  # Model predicts catches but no elogs
            risk_score = 3
    elif catches_retained_model >= catches_elogs:  # Model predicts more than elogs
        over_ratio = (catches_retained_model - catches_elogs) / catches_elogs
        if over_ratio <= _OVER_LOW:  # noqa: PLR2004
            risk_score = 1
        elif over_ratio <= _OVER_MED:  # noqa: PLR2004
            risk_score = 2
        else:
            risk_score = 3
    else:  # Model predicts less than elogs
        risk_score = 1  # we assume the elogs are correct, as there is no motivation for the captains to overreport
        under_ratio = (catches_elogs - catches_retained_model) / catches_elogs
        if under_ratio > _UNDER_FLAG:  # noqa: PLR2004
            underprediction_flag = True

    catches_difference = abs(catches_retained_model - catches_elogs)
    catches_difference_percentage = (
        0
        if catches_elogs == 0 and catches_difference == 0
        else 100
        if catches_elogs == 0
        else catches_difference / catches_elogs * 100
    )

    today_date = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    risk_score_dict = {
        "date": today_date,
        "risk_score": risk_score,
        "catches_elogs": catches_elogs,
        "catches_retained_model": catches_retained_model,
        "catches_difference": catches_difference,
        "catches_difference_percentage": catches_difference_percentage,
        "underprediction_flag": bool(underprediction_flag),
    }
    logger.info(f"Risk score based on elog comparisson: {risk_score_dict}")

    risk_score_elogs_file = os.path.join(risk_score_path, "risk_score_elogs.json")

    with open(risk_score_elogs_file, "w") as f:
        json.dump(risk_score_dict, f)

    logger.info(f"Risk score data saved to {risk_score_elogs_file}")

    return risk_score_dict
