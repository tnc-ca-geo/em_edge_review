import json
import os
from datetime import datetime

import pytz

from logger import get_logger
from onboard_system.automated_reporting import settings
from onboard_system.automated_reporting.risk_scores.utils.risk_score_model_underprediction_utils import (
    calculate_unprocessed_percentage,
    check_unprocessed_videos,
)

LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)

# Unprocessed videos % thresholds
UNPROCESSED_LOW = settings.MODEL_UNDERPREDICTION_THRESHOLD_LOW_PERCENT
UNPROCESSED_HIGH = settings.MODEL_UNDERPREDICTION_THRESHOLD_HIGH_PERCENT

# Underprediction ratio thresholds
UNDER_RATIO_HIGH = settings.MODEL_UNDERPREDICTION_UNDER_RATIO_HIGH_PERCENT / 100.0

logger = get_logger(__name__)


def calculate_risk_score_model_underprediction(  # noqa: PLR0912
    risk_score_elogs: dict,
    video_list: list,
    processed_video_list: list,
    risk_score_path: str,
) -> dict:
    """Calculate the aggregated risk score for the day based on model underprediction and unprocessed videos.

    For the elog component, as elogs report retained catch only, elog catches are compared against the retained catches predicted by the model.
    The rules are:
      - if underprediction_flag:
          under_ratio ≤ UNDER_RATIO_HIGH → risk 2
          under_ratio  > UNDER_RATIO_HIGH → risk 3
      - elif model predicted something (catches_retained_model > 0): risk 1
      - else: 0

    For the unprocessed videos component, a comparison between the day's video list and processed videos is made. Then, a risk score is assigned following these rules:
      - unprocessed% ≤ UNPROCESSED_LOW   → 1
      - UNPROCESSED_LOW < % ≤ UNPROCESSED_HIGH → 2
      - % > UNPROCESSED_HIGH → 3
      - if no video_list → 0

    The final risk score is the maximum of the two scores.

    Args:
        risk_score_elogs (dict): A dictionary containing the elogs risk score.
            - "date": The date of the record.
            - "risk_score": int, the risk score for the day.
            - "catches_elogs": int, the total number of catches logged in elogs."
            - "catches_retained_model": int, the total number of retained catches predicted by the model."
            - "catches_difference": int, the difference between elogs and model predictions."
            - "underprediction_flag": bool, True if the model predicts less than elogs.
        risk_score_path (str): The path to save the risk score file.
        video_list (list): A list of video file names for a certain date.
        processed_video_list (list): A list of processed video file names.

    Returns:
        dict: A dictionary containing:
            - "date": The date of the record.
            - "risk_score": int, the risk score for the day.
            - "risk_score_under": risk score associated with the model underprediction.,
            - "catches_elogs": int, the total number of catches logged in elogs."
            - "catches_retained_model": int, the total number of retained catches predicted by the model."
            - "catches_difference": int, the difference between elogs and model predictions."
            - "risk_score_unprocessed": risk score associated with the unprocessed videos.,
            - "unprocessed_percentage": float, the percentage of unprocessed videos.
            - "unprocessed_list": list, a list of unprocessed video file names.
    """
    # --- Underprediction component ---
    underprediction_flag = risk_score_elogs.get("underprediction_flag", False)
    catches_elogs = risk_score_elogs.get("catches_elogs", 0)
    catches_retained_model = risk_score_elogs.get("catches_retained_model", 0)

    if underprediction_flag:
        under_ratio = (catches_elogs - catches_retained_model) / catches_elogs
        risk_score_under = 2 if under_ratio <= UNDER_RATIO_HIGH else 3
    elif catches_retained_model > 0:
        risk_score_under = 1
    else:
        risk_score_under = 0

    catches_difference = abs(catches_retained_model - catches_elogs)
    catches_difference_percentage = (
        catches_difference / catches_elogs * 100 if catches_elogs > 0 else 0
    )

    # --- Unprocessed videos component ---
    if video_list:
        unprocessed_videos = check_unprocessed_videos(processed_video_list, video_list)
        unprocessed_percentage = calculate_unprocessed_percentage(unprocessed_videos, video_list)

        if unprocessed_percentage <= UNPROCESSED_LOW:
            risk_score_unprocessed = 1
        elif UNPROCESSED_LOW < unprocessed_percentage <= UNPROCESSED_HIGH:
            risk_score_unprocessed = 2
        else:
            risk_score_unprocessed = 3
    else:
        logger.info("No video data available.")
        risk_score_unprocessed = 0
        unprocessed_percentage = None
        unprocessed_videos = []

    today_date = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    risk_score = max(risk_score_under, risk_score_unprocessed)
    risk_score_under = None if risk_score_under == 0 else risk_score_under
    risk_score_unprocessed = None if risk_score_unprocessed == 0 else risk_score_unprocessed
    risk_score = None if risk_score == 0 else risk_score

    risk_score_dict = {
        "date": today_date,
        "risk_score": risk_score,
        "risk_score_under": risk_score_under,
        "catches_elogs": catches_elogs,
        "catches_retained_model": catches_retained_model,
        "catches_difference": catches_difference,
        "catches_difference_percentage": catches_difference_percentage,
        "risk_score_unprocessed": risk_score_unprocessed,
        "unprocessed_percentage": unprocessed_percentage,
        "unprocessed_list": unprocessed_videos,
    }
    logger.info(f"Risk score based on model underprediction: {risk_score_dict}")

    risk_score_model_underprediction_file = os.path.join(
        risk_score_path, "risk_score_model_underprediction.json"
    )

    with open(risk_score_model_underprediction_file, "w") as f:
        json.dump(risk_score_dict, f)
    logger.info(f"Risk score data saved to {risk_score_model_underprediction_file}")

    return risk_score_dict
