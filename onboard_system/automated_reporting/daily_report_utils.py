import base64
import os
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import pytz
from jinja2 import Template
from onboard_system.automated_reporting.risk_scores.aggregated_risk_score import (
    calculate_aggregated_risk_score,
)
from onboard_system.automated_reporting.risk_scores.risk_score_elogs import (
    calculate_risk_score_elogs,
)
from onboard_system.automated_reporting.risk_scores.risk_score_gps import (
    calculate_risk_score_gps,
)
from onboard_system.automated_reporting.risk_scores.risk_score_illegal_species import (
    calculate_risk_score_illegal_species,
)
from onboard_system.automated_reporting.risk_scores.risk_score_model_underprediction import (
    calculate_risk_score_model_underprediction,
)
from onboard_system.automated_reporting.risk_scores.risk_score_operational import (
    calculate_operational_risk_score,
)
from onboard_system.automated_reporting.risk_scores.utils.risk_score_elogs_utils import (
    load_elog_data_from_db,
)
from onboard_system.automated_reporting.risk_scores.utils.risk_score_gps_utils import (
    generate_map,
    get_gps_data,
)
from onboard_system.automated_reporting.risk_scores.utils.risk_score_illegal_species_utils import (
    get_illegal_species_risk_features,
)
from onboard_system.automated_reporting.risk_scores.utils.risk_score_model_underprediction_utils import (
    get_processed_videos,
)
from onboard_system.automated_reporting.risk_scores.utils.risk_score_operational_utils import (
    extract_timestamp_from_video_filename,
    get_gps_records_from_server,
    get_todays_videos_from_server,
)

from logger import get_logger
from onboard_system.automated_reporting import settings
from onboard_system.species_registry import ICON_MAPPING

EXPECTED_FPS = settings.EXPECTED_FPS
LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)
DUMMY_DATA_BASE_PATH = settings.DUMMY_DATA_BASE_PATH
DISCARDED_MATCHING_THRESH = settings.DISCARDED_MATCHING_THRESH

logger = get_logger(__name__)

EVENT_TYPE_DISPLAY = {
    "RETAINED": "Retained",
    "VESSEL_DISCARD": "Vessel Discard",
    "WATER_DISCARD": "Water Discard",
}


def display_event_type(evt: str) -> str:
    return EVENT_TYPE_DISPLAY.get(evt, evt)


def extract_evidence_frames(catch_sequence: List[Dict], output_dir: str) -> None:
    """Placeholder: implement in your environment-specific layer.

    This function should extract evidence frames for the given catch sequence and save them to the output directory.
    """
    msg = "Provide extract_evidence_frames() in your project."
    raise NotImplementedError(msg)


def encode_to_base64(file_path: str) -> str:
    """Encode a file to a base64 string.

    Args:
        file_path (str): The path to the file to encode.

    Returns:
        str: The base64-encoded file string.
    """
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def load_icons_as_base64() -> dict:
    """Load all icon images as base64 strings."""
    icons_base64 = {}
    icons_dir = "onboard_system/automated_reporting/icons"

    for level, icons in ICON_MAPPING.items():
        icons_base64[level] = {}
        for key, icon_file in icons.items():
            icon_path = os.path.join(icons_dir, icon_file)
            if os.path.exists(icon_path):
                icons_base64[level][key] = encode_to_base64(icon_path)
            else:
                logger.warning(f"Icon file not found: {icon_path}")
                icons_base64[level][key] = ""

    return icons_base64


def load_logos_as_base64() -> dict:
    """Load logo images as base64 strings from the static directory."""
    logos_base64 = {}
    logos_dir = "onboard_system/automated_reporting/daily_report_template/static/images"

    # Define logo filenames
    logo_files = {
        "tnc_logo": "tnc-logo.svg",
        "partner_logo": "tryolabs-logo.svg",
        "calendar_icon": "calendar.svg",
    }

    for key, filename in logo_files.items():
        logo_path = os.path.join(logos_dir, filename)
        if os.path.exists(logo_path):
            logos_base64[key] = encode_to_base64(logo_path)
        else:
            logger.warning(f"Logo file not found: {logo_path}")
            logos_base64[key] = ""

    return logos_base64


def load_html_template(template_path: str) -> Template:
    """Load an HTML template from the given path.

    Args:
        template_path (str): The path to the HTML template file.

    Returns:
        Template: The loaded HTML template.
    """
    with open(template_path) as template_file:
        return Template(template_file.read())


def load_report_inputs(
    use_dummy_data: bool,  # noqa: FBT001
) -> Tuple[List[str], List[str], pd.DataFrame, List[str]]:
    """Load per-day inputs required to compute the report and risk scores.

    Depending on `use_dummy_data`, this loads:
      - Video list (filenames for the day)
      - GPS list (filenames/records for the day)
      - E-log catch dataframe
      - Processed video list (filenames already processed by the model)

    Returns:
        tuple: (video_list, gps_list, elog_catch_df, processed_video_list)
    """
    if use_dummy_data:
        base = Path(DUMMY_DATA_BASE_PATH)
        video_list = (base / "video_list.txt").read_text(encoding="utf-8").splitlines()
        gps_list = (base / "gps_list.txt").read_text(encoding="utf-8").splitlines()
        elog_catch_df = pd.read_csv(base / "elog_catch.csv")
        processed_video_list = (
            (base / "processed_video_list.txt").read_text(encoding="utf-8").splitlines()
        )
    else:
        video_list = get_todays_videos_from_server() or []
        gps_list = get_gps_records_from_server() or []
        elog_catch_df = load_elog_data_from_db()
        processed_video_list = get_processed_videos() or []

    return video_list, gps_list, elog_catch_df, processed_video_list


def compute_report_artifacts(
    catch_sequence: List[Dict],
    counts_by_species: List[Dict],
    report_path: str,
    use_dummy_data: bool,  # noqa: FBT001
    video_list: List[str],
    gps_list: List[str],
    elog_catch_df: pd.DataFrame,
    processed_video_list: List[str],
) -> Dict[str, Any]:
    """Compute map HTML and all risk scores, then aggregate them.

    This runs the full pipeline of “derived outputs” used in the report:
      - GPS match + map HTML
      - GPS risk score
      - Illegal species risk score
      - Operational risk score (video + GPS coverage/gaps)
      - E-logs risk score (model vs e-logs)
      - Model underprediction risk score (underprediction + unprocessed videos)
      - Aggregated risk score across all components

    Returns:
        dict: {
          "map_html", "risk_score_gps", "risk_score_illegal_species",
          "risk_score_operational", "risk_score_elogs",
          "risk_score_model_underprediction", "aggregated_risk_score"
        }
    """
    # GPS: match and map
    catches_with_gps = get_gps_data(catch_sequence, use_dummy_data=use_dummy_data)
    map_html = generate_map(catches_with_gps=catches_with_gps)

    # GPS risk
    risk_score_gps = calculate_risk_score_gps(
        catches_with_gps=catches_with_gps,
        risk_score_path=report_path,
    )

    # Illegal species risk
    counts_by_species_with_risk_features = get_illegal_species_risk_features(
        counts_by_species=counts_by_species
    )
    risk_score_illegal_species = calculate_risk_score_illegal_species(
        counts_by_species_with_risk_features=counts_by_species_with_risk_features,
        risk_score_path=report_path,
    )

    # Operational risk
    risk_score_operational = calculate_operational_risk_score(
        video_list=video_list,
        gps_list=gps_list,
        risk_score_path=report_path,
    )

    # E-logs risk
    risk_score_elogs = calculate_risk_score_elogs(
        counts_by_species=counts_by_species,
        elog_catch_df=elog_catch_df,
        risk_score_path=report_path,
    )

    # Model underprediction risk
    risk_score_model_underprediction = calculate_risk_score_model_underprediction(
        risk_score_elogs=risk_score_elogs,
        video_list=video_list,
        processed_video_list=processed_video_list,
        risk_score_path=report_path,
    )

    # Aggregated risk
    aggregated_risk_score = calculate_aggregated_risk_score(
        risk_score_gps=risk_score_gps,
        risk_score_illegal_species=risk_score_illegal_species,
        risk_score_elogs=risk_score_elogs,
        risk_score_model_underprediction=risk_score_model_underprediction,
        risk_score_operational=risk_score_operational,
    )

    return {
        "map_html": map_html,
        "risk_score_gps": risk_score_gps,
        "risk_score_illegal_species": risk_score_illegal_species,
        "risk_score_operational": risk_score_operational,
        "risk_score_elogs": risk_score_elogs,
        "risk_score_model_underprediction": risk_score_model_underprediction,
        "aggregated_risk_score": aggregated_risk_score,
    }


def map_events(
    catch_sequence: List[Dict], discarded_matching_thresh: int = DISCARDED_MATCHING_THRESH
) -> List[Dict]:
    """Map catch events to RETAINED, VESSEL_DISCARD, or WATER_DISCARD based on proximity in frames.

    - DISCARD events are mapped to WATER_DISCARD
    - IN events are paired with OUT events if they occur within the discarded_matching_thresh (regardless of the species) and mapped to VESSEL_DISCARD.
    - Unmatched IN events are mapped to RETAINED.

    Args:
        catch_sequence (list[dict]): List of catch events to map.
        discarded_matching_thresh (int): window in frames for matching IN and OUT events.

    Returns:
        list[dict]: The mapped catch events.
    """
    mapped_events: List[Dict] = []
    event_index = 0

    while event_index < len(catch_sequence):
        current_event = catch_sequence[event_index]
        current_type = current_event["event_type"]

        if current_type == "DISCARD":
            mapped = dict(current_event)
            mapped["event_type"] = "WATER_DISCARD"
            mapped_events.append(mapped)
            event_index += 1
            continue

        if current_type == "IN":
            next_event = (
                catch_sequence[event_index + 1] if event_index + 1 < len(catch_sequence) else None
            )
            if (
                next_event
                and next_event["event_type"] == "OUT"
                and (next_event["global_frame"] - current_event["global_frame"])
                <= discarded_matching_thresh
            ):
                # IN immediately followed by OUT within threshold, map to VESSEL_DISCARD
                mapped = dict(current_event)
                mapped["event_type"] = "VESSEL_DISCARD"
                mapped["estimated_catch_time"] = next_event.get("estimated_catch_time")
                mapped["frame_number"] = next_event.get("frame_number")
                mapped["video_filename"] = next_event.get("video_filename")
                mapped["global_frame"] = next_event.get("global_frame")
                # Keep IN event information in case we need it later
                mapped["_paired_in_estimated_catch_time"] = current_event.get(
                    "estimated_catch_time"
                )
                mapped["_paired_in_frame_number"] = current_event.get("frame_number")
                mapped["_paired_in_global_frame"] = current_event.get("global_frame")
                mapped["_paired_in_video_filename"] = current_event.get("video_filename")
                mapped_events.append(mapped)
                event_index += 2  # consume both IN and OUT
            else:
                # No matching OUT, map to RETAINED
                mapped = dict(current_event)
                mapped["event_type"] = "RETAINED"
                mapped_events.append(mapped)
                event_index += 1
            continue

        else:
            # OUT not directly after IN → ignore
            event_index += 1

    return mapped_events


def get_estimated_catch_time(event_data: dict, fps: int = EXPECTED_FPS) -> str:
    """Get estimated catch time in local timezone for catch event.

    Args:
        event_data: Dictionary containing catch event data.
        fps: Frames per second of the video.

    Returns:
        Estimated catch time in ISO format (str).
    """
    video_filename = event_data["video_filename"]
    frame_number = event_data["frame_number"]
    timestamp = extract_timestamp_from_video_filename(video_filename)
    if timestamp is not None:
        # In our case timestamps are in UTC
        timestamp = pytz.utc.localize(timestamp)
    else:
        logger.error(f"Failed to extract timestamp from video filename: {video_filename}")
        return ""

    estimated_catch_time = timestamp + timedelta(seconds=frame_number / fps)

    estimated_catch_time = estimated_catch_time.astimezone(LOCAL_TZ)

    return estimated_catch_time.isoformat()  # to be able to serialize to JSON
