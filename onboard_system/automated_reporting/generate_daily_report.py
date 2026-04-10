import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytz

from logger import get_logger
from onboard_system.automated_reporting import settings
from onboard_system.automated_reporting.daily_report_utils import (
    compute_report_artifacts,
    display_event_type,
    encode_to_base64,
    extract_evidence_frames,
    get_estimated_catch_time,
    load_html_template,
    load_icons_as_base64,
    load_logos_as_base64,
    load_report_inputs,
    map_events,
)
from onboard_system.species_registry import FISH_MAPPING, ICON_MAPPING, ILLEGAL_SPECIES

EXPECTED_FPS = settings.EXPECTED_FPS
LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)
DUMMY_DATA_BASE_PATH = settings.DUMMY_DATA_BASE_PATH
REPORT_TEMPLATE_HTML = (
    "onboard_system/automated_reporting/daily_report_template/daily_fish_count_report_template.html"
)
REPORT_TEMPLATE_CSS = (
    "onboard_system/automated_reporting/daily_report_template/static/css/report_styles.css"
)

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily fish count report.")
    parser.add_argument(
        "--use_dummy_data",
        action="store_true",
        help="Use dummy data for testing purposes.",
    )
    parser.add_argument(
        "--inference_results_path",
        type=str,
        default="tests/dummy_data/fish_tracker_and_counter/output/catch_events",
        help="Path to the inference results.",
    )
    parser.add_argument(
        "--report_path",
        type=str,
        default="tests/dummy_data/fish_tracker_and_counter/output/daily_report",
        help="Path to the report output.",
    )

    args = parser.parse_args()
    os.makedirs(args.inference_results_path, exist_ok=True)
    os.makedirs(args.report_path, exist_ok=True)

    return args


def process_json_files(
    report_path: str,
    inference_results_path: str,
) -> None:
    """Process JSON files in todays folder and generate a daily report.

    Args:
        report_path (str): The path to save the daily report.
        inference_results_path (str): The path to the inference results.
    """
    total_counts = defaultdict(lambda: {"RETAINED": 0, "VESSEL_DISCARD": 0, "WATER_DISCARD": 0})
    counts_by_group = defaultdict(lambda: {"RETAINED": 0, "VESSEL_DISCARD": 0, "WATER_DISCARD": 0})
    counts_by_group_subcategory = defaultdict(
        lambda: {"RETAINED": 0, "VESSEL_DISCARD": 0, "WATER_DISCARD": 0}
    )
    counts_by_species = defaultdict(
        lambda: {"RETAINED": 0, "VESSEL_DISCARD": 0, "WATER_DISCARD": 0}
    )
    catch_sequence = []
    file_count = 0

    for filename in os.listdir(inference_results_path):
        if filename.endswith(".json"):
            file_path = os.path.join(inference_results_path, filename)
            with open(file_path) as file:
                data = json.load(file)

            label = data["label"]
            event_type = data["event_type"]
            avg_conf_score = data["avg_conf_score"]
            video_filename = data["video_filename"]
            frame_number = data["frame_number"]

            global_frame = data["global_frame"]

            catch_sequence.append(
                {
                    "label": label,
                    "scientific_name": FISH_MAPPING.get(label, {}).get(
                        "scientific_name", "Unknown"
                    ),
                    "name_en": FISH_MAPPING.get(label, {}).get("name_en", "Unknown"),
                    "name_es": FISH_MAPPING.get(label, {}).get("name_es", "Unknown"),
                    "illegal": bool(label in ILLEGAL_SPECIES),
                    "event_type": event_type,
                    "conf_score": avg_conf_score,
                    "video_filename": video_filename,
                    "frame_number": frame_number,
                    "global_frame": global_frame,
                    "estimated_catch_time": get_estimated_catch_time(data),
                }
            )

            file_count += 1

    # Sort catch sequence by global frame number
    catch_sequence.sort(key=lambda x: x["global_frame"])

    # Map events to RETAINED, VESSEL_DISCARD, or WATER_DISCARD
    catch_sequence = map_events(catch_sequence)

    # Update counts
    for event in catch_sequence:
        event_type = event["event_type"]
        label = event["label"]
        total_counts["Catches"][event_type] += 1

        group = FISH_MAPPING.get(label, {}).get("group", "UNKNOWN")
        counts_by_group[group][event_type] += 1

        subcategory = FISH_MAPPING.get(label, {}).get("group_subcategory", "UNKNOWN")
        counts_by_group_subcategory[subcategory][event_type] += 1

        if label in FISH_MAPPING:
            counts_by_species[label][event_type] += 1

    report_date = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    # Prepare output
    daily_report = {
        "date": report_date,
        "total_counts": {"label": "Catches", **total_counts["Catches"]},
        "counts_by_group": [
            {"label": group, **counts} for group, counts in counts_by_group.items()
        ],
        "counts_by_group_subcategory": [
            {"label": subcategory, **counts}
            for subcategory, counts in counts_by_group_subcategory.items()
        ],
        "counts_by_species": [
            {
                "fao_code": label,
                "common_name": FISH_MAPPING[label]["name_en"],
                "scientific_name": FISH_MAPPING[label]["scientific_name"],
                "iucn_category": FISH_MAPPING[label]["iucn_category"],
                **counts,
            }
            for label, counts in counts_by_species.items()
        ],
        "catch_sequence": catch_sequence,
    }

    # Save report to JSON file
    output_path = os.path.join(report_path, "daily_report.json")
    with open(output_path, "w") as output_file:
        json.dump(daily_report, output_file, indent=4)

    logger.info(f"Processed {file_count} files. Report saved to {output_path}.")


def generate_html_report(
    report_path: str,
    use_dummy_data: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Render the daily HTML report using precomputed JSON + derived artifacts.

    Steps:
      1) Load the persisted daily_report.json (counts + catch_sequence).
      2) Convert/annotate catch sequence (display fields, datetimes).
      3) Load runtime inputs (video/gps/e-logs/processed list).
      4) Compute map + all risk scores + aggregate.
      5) Encode assets and render the template to HTML.

    Args:
        report_path (str): The path to save the daily report.
        use_dummy_data (bool): Whether to use dummy data for testing purposes.
    """
    logger.info(f"Generating HTML report from {report_path}")

    if use_dummy_data:
        logger.info("Using dummy data for testing purposes.")
        json_file = os.path.join(DUMMY_DATA_BASE_PATH, "daily_report.json")
    else:
        json_file = os.path.join(report_path, "daily_report.json")
    if not os.path.exists(json_file):
        logger.error(f"File not found: {json_file}")
        return

    with open(json_file) as file:
        daily_report = json.load(file)
        logger.info(f"Loaded daily report json from {json_file}")

    # Extract data from the report
    date = daily_report["date"]
    total_counts = daily_report["total_counts"]
    counts_by_group = daily_report["counts_by_group"]
    counts_by_group_subcategory = daily_report["counts_by_group_subcategory"]
    counts_by_species = daily_report["counts_by_species"]
    catch_sequence = daily_report["catch_sequence"]

    # Convert estimated catch times to datetime objects
    for event in catch_sequence:
        event["estimated_catch_time"] = datetime.fromisoformat(event["estimated_catch_time"])
        event["event_type_display"] = display_event_type(event["event_type"])

    # Load runtime inputs (video/gps/elogs/processed list)
    video_list, gps_list, elog_catch_df, processed_video_list = load_report_inputs(use_dummy_data)

    # Compute artifacts (map + all risk scores + aggregate)
    artifacts = compute_report_artifacts(
        catch_sequence=catch_sequence,
        counts_by_species=counts_by_species,
        report_path=report_path,
        use_dummy_data=use_dummy_data,
        video_list=video_list,
        gps_list=gps_list,
        elog_catch_df=elog_catch_df,
        processed_video_list=processed_video_list,
    )
    # Extract evidence frames
    if catch_sequence:
        if use_dummy_data:
            # When using dummy data, skip extraction and use play-circle.png as fallback
            for catch in catch_sequence:
                catch["evidence_image"] = None
        else:
            evidence_dir = os.path.join(report_path, "evidence_frames")
            extract_evidence_frames(catch_sequence=catch_sequence, output_dir=evidence_dir)
            for catch in catch_sequence:
                video_filename_base = catch["video_filename"]
                frame_number = catch["frame_number"]
                evidence_filename = f"{video_filename_base}_frame_{frame_number}.jpg"
                evidence_path = os.path.join(evidence_dir, evidence_filename)
                if os.path.exists(evidence_path):
                    catch["evidence_image"] = encode_to_base64(evidence_path)
                else:
                    logger.warning(f"File not found: {evidence_path}")
                    catch["evidence_image"] = None

    for catch in catch_sequence:
        label = catch["label"]
        group = FISH_MAPPING.get(label, {}).get("group", "UNKNOWN")
        catch["group"] = str(group).upper() if group is not None else "UNKNOWN"

    # Assets
    css_base64 = encode_to_base64(file_path=REPORT_TEMPLATE_CSS)
    icons_base64 = load_icons_as_base64()
    logos_base64 = load_logos_as_base64()

    # Template
    html_template = load_html_template(template_path=REPORT_TEMPLATE_HTML)

    # Render HTML
    html_content = html_template.render(
        date=date,
        use_dummy_data=use_dummy_data,
        total_counts=total_counts,
        counts_by_group=counts_by_group,
        counts_by_group_subcategory=counts_by_group_subcategory,
        counts_by_species=counts_by_species,
        catch_sequence=catch_sequence,
        map_html=artifacts["map_html"],
        risk_score_gps=artifacts["risk_score_gps"],
        risk_score_illegal_species=artifacts["risk_score_illegal_species"],
        risk_score_elogs=artifacts["risk_score_elogs"],
        risk_score_model_underprediction=artifacts["risk_score_model_underprediction"],
        risk_score_operational=artifacts["risk_score_operational"],
        aggregated_risk_score=artifacts["aggregated_risk_score"],
        ICON_MAPPING=ICON_MAPPING,
        ICONS_BASE64=icons_base64,
        LOGOS_BASE64=logos_base64,
        CSS_BASE64=css_base64,
    )

    # Save HTML to file
    output_html_path = Path(report_path) / "daily_report.html"
    with open(output_html_path, "w") as html_file:
        html_file.write(html_content)

    logger.info(f"HTML report saved to {output_html_path}")


def main() -> None:
    """Main function to be called when running this script directly."""
    args = parse_args()

    if args.use_dummy_data:
        generate_html_report(
            report_path=args.report_path,
            use_dummy_data=True,
        )
    else:
        process_json_files(
            report_path=args.report_path,
            inference_results_path=args.inference_results_path,
        )
        generate_html_report(
            report_path=args.report_path,
            use_dummy_data=False,
        )


if __name__ == "__main__":
    main()
