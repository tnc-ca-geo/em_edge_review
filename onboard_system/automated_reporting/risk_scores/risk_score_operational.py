import json
import os
from datetime import datetime, timedelta
from typing import Dict, Union

import pytz

from logger import get_logger
from onboard_system.automated_reporting import settings
from onboard_system.automated_reporting.risk_scores.utils.risk_score_operational_utils import (
    calculate_total_footage_time,
    calculate_total_gps_records_time,
    find_gaps_in_list,
)

logger = get_logger(__name__)

LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)
OPERATIONAL_COVERAGE_MIN_DURATION = settings.OPERATIONAL_COVERAGE_MIN_DURATION
OPERATIONAL_GAPS_PERCENT_LOW = settings.OPERATIONAL_GAPS_PERCENT_LOW
OPERATIONAL_GAPS_PERCENT_HIGH = settings.OPERATIONAL_GAPS_PERCENT_HIGH


def _percent(numerator: timedelta, denominator: timedelta) -> float:
    """Return (numerator/denominator)*100, safe for zero denominators."""
    if denominator <= timedelta(0):
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def calculate_operational_risk_score(  # noqa: PLR0912, PLR0915
    video_list: list, gps_list: list, risk_score_path: str
) -> Dict[str, Union[str, int, None]]:
    """Calculates the operational risk score based on video and GPS coverage/gaps.

    Two risk scores are calculated: one for video and one for GPS. The video footage risk score is determined based on the total time of video footage and the proportion of time gaps in the video footage.
    The GPS risk score is determined based on the total time of GPS records and the proportion of time gaps in the GPS records.

    The score value for each one is determined following these rules:
    - If the total time of video footage/gps records is less than OPERATIONAL_COVERAGE_MIN_DURATION (median hauling time), the risk score is 3.
    - If the total time of video footage/gps records is greater than OPERATIONAL_COVERAGE_MIN_DURATION, the risk score is determined by the proportion of time gaps:
        - If the proportion of time gaps is greater than OPERATIONAL_GAPS_PERCENT_HIGH, the risk score is 3.
        - If the proportion of time gaps is between OPERATIONAL_GAPS_PERCENT_LOW and OPERATIONAL_GAPS_PERCENT_HIGH, the risk score is 2.
        - If the proportion of time gaps is less than OPERATIONAL_GAPS_PERCENT_LOW, the risk score is 1.
    If there is no video data, the risk score for video is set to 0. If there is no GPS data, the risk score for GPS is set to 0.
    The final risk score is the maximum of the two scores. If both scores are 0, the risk score is set to None.

    Args:
        video_list (list): A list of video file names.
        gps_list (list): A list of GPS records.
        risk_score_path (str): The path to save the risk score file.

    Returns:
        dict: A dictionary containing:
            - date: The date of the risk score calculation.
            - risk_score: The risk score for the day, maximum risk score between video and GPS.
            - risk_video: The risk score for video.
            - total_time: The total time of video footage.
            - total_time_gaps: The total time gaps in video footage
            - gaps_percentage_over_total: The percentage of time gaps in video footage
            - risk_gps: The risk score for GPS.
            - gps_total_time: The total time of GPS records.
            - gps_total_time_gaps: The total time gaps in GPS records.
            - gps_gaps_percentage_over_total: The percentage of time gaps in GPS records.
    """
    # --- Video ---
    if video_list:
        video_time_gaps = find_gaps_in_list(data_list=video_list, data_source="video")
        video_total_time = calculate_total_footage_time(video_list)
        video_total_time_gaps = sum(video_time_gaps, timedelta())
        video_gaps_percentage_over_total = _percent(video_total_time_gaps, video_total_time)

        if video_total_time < OPERATIONAL_COVERAGE_MIN_DURATION:
            risk_video = 3
        else:  # noqa: PLR5501
            if video_gaps_percentage_over_total > OPERATIONAL_GAPS_PERCENT_HIGH:
                risk_video = 3
            elif video_gaps_percentage_over_total > OPERATIONAL_GAPS_PERCENT_LOW:
                risk_video = 2
            else:
                risk_video = 1
    else:
        logger.info("No video data available.")
        risk_video = 0
        video_time_gaps = []
        video_total_time = timedelta()
        video_total_time_gaps = timedelta()
        video_gaps_percentage_over_total = 0.0

    # --- GPS ---
    if gps_list:
        gps_records_time_gaps = find_gaps_in_list(data_list=gps_list, data_source="gps")
        gps_records_total_time = calculate_total_gps_records_time(gps_list)
        gps_records_total_time_gaps = sum(gps_records_time_gaps, timedelta())
        gps_gaps_percentage_over_total = _percent(
            gps_records_total_time_gaps, gps_records_total_time
        )

        if gps_records_total_time < OPERATIONAL_COVERAGE_MIN_DURATION:
            risk_gps = 3
        else:  # noqa: PLR5501
            if gps_gaps_percentage_over_total > OPERATIONAL_GAPS_PERCENT_HIGH:
                risk_gps = 3
            elif gps_gaps_percentage_over_total > OPERATIONAL_GAPS_PERCENT_LOW:
                risk_gps = 2
            else:
                risk_gps = 1
    else:
        logger.info("No GPS data available.")
        risk_gps = 0
        gps_records_time_gaps = []
        gps_records_total_time = timedelta()
        gps_records_total_time_gaps = timedelta()
        gps_gaps_percentage_over_total = 0.0

    today_date = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    risk = max(risk_video, risk_gps)
    if risk == 0:
        risk = None
        risk_video = None
        risk_gps = None
    elif risk_video == 0:
        risk_video = None
    elif risk_gps == 0:
        risk_gps = None
    risk_dict = {
        "date": today_date,
        "risk_score": risk,
        "risk_video": risk_video,
        "total_time": str(video_total_time),
        "total_time_gaps": str(video_total_time_gaps),
        "gaps_percentage_over_total": str(video_gaps_percentage_over_total),
        "risk_gps": risk_gps,
        "gps_total_time": str(gps_records_total_time),
        "gps_total_time_gaps": str(gps_records_total_time_gaps),
        "gps_gaps_percentage_over_total": str(gps_gaps_percentage_over_total),
    }

    risk_score_operational_file = os.path.join(risk_score_path, "risk_score_operational.json")

    with open(risk_score_operational_file, "w") as f:
        json.dump(risk_dict, f, indent=4)

    logger.info(f"Risk score data saved to {risk_score_operational_file}")

    return risk_dict
