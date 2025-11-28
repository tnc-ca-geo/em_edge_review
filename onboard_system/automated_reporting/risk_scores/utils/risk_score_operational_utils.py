from datetime import datetime, timedelta
from typing import List, Optional

from logger import get_logger
from onboard_system.automated_reporting import settings

OPERATIONAL_GAP_THRESHOLD = settings.OPERATIONAL_GAP_THRESHOLD
EXPECTED_VIDEO_LENGTH = settings.EXPECTED_VIDEO_LENGTH
EXPECTED_RECORD_INTERVAL = settings.EXPECTED_RECORD_INTERVAL

logger = get_logger(__name__)


def get_todays_videos_from_server() -> List[str]:
    """Placeholder: implement in your environment-specific layer."""
    msg = "Provide get_todays_videos_from_server() in your project."
    raise NotImplementedError(msg)


def get_gps_records_from_server() -> List[str]:
    """Placeholder: implement in your environment-specific layer."""
    msg = "Provide get_gps_records_from_server() in your project."
    raise NotImplementedError(msg)


def extract_timestamp_from_video_filename(filename: str) -> Optional[datetime]:
    """Extract timestamp from a video filename.

    Expected format:
        {boatname}_{camera_id}_{YYYYMMDD}-{HHMMSS}_{resolution}.mp4
    """
    parts = filename.split("_")
    if len(parts) < 3:  # noqa: PLR2004
        return None

    try:
        return datetime.strptime(parts[2], "%Y%m%d-%H%M%S")
    except ValueError:
        logger.exception("Invalid video filename format: %s", filename)
        return None


def extract_timestamp_from_gps_filename(filename: str) -> Optional[datetime]:
    """Extract timestamp from a GPS filename.

    Expected format:
        {boatname}_{YYYYMMDD}_{HHMM}.csv
    """
    parts = filename.split("_")
    if len(parts) != 3:  # noqa: PLR2004
        return None

    try:
        date_part = parts[1]
        time_part = parts[2].split(".")[0] + "00"
        return datetime.strptime(f"{date_part}-{time_part}", "%Y%m%d-%H%M%S")
    except ValueError:
        logger.exception("Invalid GPS filename format: %s", filename)
        return None


def find_gaps_in_list(data_list: list, data_source: str = "video") -> list[timedelta]:
    """Identify significant time gaps between consecutive data items.

    Extracts timestamps from a list of items (e.g., video or GPS filenames),
    and finds gaps that exceed the configured threshold (`OPERATIONAL_GAP_THRESHOLD`).
    Each gap is reduced by a fixed adjustment, to estimate the actual unrecorded interval.

    Args:
        data_list (list): Filenames) containing timestamps.
        data_source (str, optional): Data source type ("video" or "gps").
            Defaults to "video".

    Returns:
        list[datetime.timedelta]: Durations of gaps that exceeded the threshold,
        adjusted for video length.
    """
    datetimes = []
    if data_source == "video":
        datetimes = [
            dt
            for dt in (extract_timestamp_from_video_filename(video) for video in data_list)
            if dt is not None
        ]
    elif data_source == "gps":
        datetimes = [
            dt
            for dt in (extract_timestamp_from_gps_filename(gps) for gps in data_list)
            if dt is not None
        ]

    time_gaps = []
    for i in range(1, len(datetimes)):
        time_gap = datetimes[i] - datetimes[i - 1]
        if time_gap > OPERATIONAL_GAP_THRESHOLD:
            adjust = EXPECTED_VIDEO_LENGTH if data_source == "video" else EXPECTED_RECORD_INTERVAL
            adjusted = time_gap - adjust
            time_gaps.append(adjusted)

    return time_gaps


def calculate_total_footage_time(video_list: List[str]) -> timedelta:
    """Estimate the total recorded footage duration from video filenames.

    Extracts timestamps from video filenames and sums time differences between
    consecutive recordings. If a gap between two videos exceeds the configured
    threshold (`OPERATIONAL_GAP_THRESHOLD`), only the nominal segment duration
    (`EXPECTED_VIDEO_LENGTH`) is added—preventing overestimation due to large gaps.
    If any footage exists, one additional `EXPECTED_VIDEO_LENGTH` is added to account
    for the final recorded segment.

    Args:
        video_list (List[str]): A list of video file names.

    Returns:
        datetime.timedelta: Total footage time.
    """
    video_datetimes = [
        dt
        for dt in (extract_timestamp_from_video_filename(video) for video in video_list)
        if dt is not None
    ]

    total_time = timedelta()
    for i in range(1, len(video_datetimes)):
        delta = video_datetimes[i] - video_datetimes[i - 1]
        total_time += delta if delta <= OPERATIONAL_GAP_THRESHOLD else EXPECTED_VIDEO_LENGTH

    # Add the last video time if total_time is not empty
    if total_time > timedelta():
        total_time += EXPECTED_VIDEO_LENGTH

    logger.debug(f"Total footage time: {total_time}")
    return total_time


def calculate_total_gps_records_time(gps_list: List[str]) -> timedelta:
    """Estimate the total duration covered by GPS records based on filenames.

    Extracts timestamps from GPS filenames and sums time differences between
    consecutive records. If a gap between two records exceeds the configured
    threshold (`OPERATIONAL_GAP_THRESHOLD`), only the nominal record interval
    (`EXPECTED_RECORD_INTERVAL`) is added—preventing overestimation caused by missing data.
    If any records exist, one additional `EXPECTED_RECORD_INTERVAL` is added to account
    for the final recorded point.

    Args:
        gps_list (List[str]): A list of GPS file names from which timestamps are extracted.

    Returns:
        datetime.timedelta: The total time covered by the GPS records.
    """
    gps_datetimes = [
        dt
        for dt in (extract_timestamp_from_gps_filename(gps) for gps in gps_list)
        if dt is not None
    ]

    total_time = timedelta()
    for i in range(1, len(gps_datetimes)):
        delta = gps_datetimes[i] - gps_datetimes[i - 1]
        total_time += delta if delta <= OPERATIONAL_GAP_THRESHOLD else EXPECTED_RECORD_INTERVAL

    # Add the last GPS record time if total_time is not empty
    if total_time > timedelta():
        total_time += EXPECTED_RECORD_INTERVAL

    logger.debug(f"Total GPS records time: {total_time}")

    return total_time
