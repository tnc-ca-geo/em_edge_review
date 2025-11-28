import json
import os
from datetime import datetime

import pandas as pd
import pytz

from logger import get_logger
from onboard_system.automated_reporting import settings

logger = get_logger(__name__)
LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)
DISTANCE_TO_BOUNDARY_KM_THRESHOLD = settings.GPS_DISTANCE_TO_BOUNDARY_KM_THRESHOLD


def calculate_risk_score_gps(
    catches_with_gps: list,
    risk_score_path: str,
) -> dict:
    """Calculate the risk score based on the GPS risk features of the catches.

    Criteria:
    - If any catch is inside the MPA or inside the coastline buffer, risk is 3.
    - Otherwise, if any catch is within the threshold distance to the boundary of the MPA or coastline buffer, risk is 2.
    - Otherwise, risk is 1.

    Args:
    catches_with_gps (list): List of dictionaries containing GPS data for each catch event.
    risk_score_path (str): Path to the folder where the risk score file will be saved.

    Returns:
    risk_score (dict): Dictionary containing the aggregated gps risk score for the day.
    """
    logger.info("Calculating risk score based on GPS data.")
    catches_with_gps_df = pd.DataFrame(catches_with_gps)

    if catches_with_gps_df.empty:
        # No catches available; assign empty values.
        risk = None
        any_in_mpa = None
        any_in_coast_buffer = None
        max_dist_to_eez_km = None
        min_dist_to_mpa_km = None
        min_dist_to_coast_buffer_km = None
    else:
        # Check if any catch is inside the MPA or outside the EEZ:
        any_in_mpa = bool((~catches_with_gps_df["outside_mpa"]).any())
        any_in_coast_buffer = bool((~catches_with_gps_df["outside_coast_buffer"]).any())

        if any_in_mpa or any_in_coast_buffer:
            risk = 3
        else:
            # All catches are outside the MPA and inside the EEZ, so we evaluate the distances.
            near_mpa = (
                catches_with_gps_df["dist_to_mpa_km"] < DISTANCE_TO_BOUNDARY_KM_THRESHOLD
            ).any()
            near_coast_buffer = (
                catches_with_gps_df["dist_to_coast_buffer_km"] < DISTANCE_TO_BOUNDARY_KM_THRESHOLD
            ).any()
            if near_mpa or near_coast_buffer:
                risk = 2
            else:
                # All catches are far from the MPA and EEZ boundaries.
                risk = 1

        max_dist_to_eez_km = (
            float(catches_with_gps_df["dist_to_eez_km"].max())
            if not catches_with_gps_df.empty
            else None
        )
        min_dist_to_mpa_km = (
            float(catches_with_gps_df["dist_to_mpa_km"].min())
            if not catches_with_gps_df.empty
            else None
        )
        min_dist_to_coast_buffer_km = (
            float(catches_with_gps_df["dist_to_coast_buffer_km"].min())
            if not catches_with_gps_df.empty
            else None
        )

    today_date = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    risk_dict = {
        "date": today_date,
        "risk_score": risk,
        "any_in_mpa": any_in_mpa,
        "any_in_coast_buffer": any_in_coast_buffer,
        "max_dist_to_eez_km": max_dist_to_eez_km,
        "min_dist_to_mpa_km": min_dist_to_mpa_km,
        "min_dist_to_coast_buffer_km": min_dist_to_coast_buffer_km,
    }
    logger.info(f"Risk score based on GPS data: {risk_dict}")

    risk_score_gps_file = os.path.join(risk_score_path, "risk_score_gps.json")

    with open(risk_score_gps_file, "w") as f:
        json.dump(risk_dict, f, indent=4)

    logger.info(f"Risk score data saved to {risk_score_gps_file}")

    return risk_dict
