import argparse
import os
from typing import List, Tuple, Union

import cv2

from logger import get_logger
from onboard_system.ai_powered_system.fish_tracker_and_counter.utils.calculate_line_coordinates import (
    calculate_coordinates,
    get_video_resolution,
)
from onboard_system.ai_powered_system.fish_tracker_and_counter.utils.custom_object_counter import (
    CustomObjectCounter,
)

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process video for fish counting.")

    parser.add_argument(
        "--video_path",
        type=str,
        required=True,
        help="Path to the input video file.",
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default="fish_detector_model/baseline_model/baseline_fish_detector.pt",
        help="Path to the trained YOLO model file.",
    )
    parser.add_argument(
        "--output_video_folder",
        type=str,
        default="tests/dummy_data/fish_tracker_and_counter/output/video",
        help="Directory where processed videos will be saved.",
    )
    parser.add_argument(
        "--output_json_folder",
        type=str,
        default="tests/dummy_data/fish_tracker_and_counter/output/catch_events",
        help="Directory where JSON catch events will be saved.",
    )
    parser.add_argument(
        "--write_results_video",
        action="store_true",
        help="Flag to indicate whether to save processed videos with object counts.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.3,
        help="Confidence threshold for object detection.",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.1,
        help="Intersection Over Union threshold for Non-Maximum Suppression.",
    )
    parser.add_argument(
        "--tracker_config",
        type=str,
        default="onboard_system/ai_powered_system/fish_tracker_and_counter/config/botsort.yaml",
        help="Path to the tracker YAML (e.g., BoT-SORT).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help='Compute device for Ultralytics: "cpu", "0", "cuda:0", etc. (default: "0").',
    )

    args = parser.parse_args()

    os.makedirs(args.output_video_folder, exist_ok=True)
    os.makedirs(args.output_json_folder, exist_ok=True)

    return args


def count_fish_in_video(
    video_file: str,
    counter: CustomObjectCounter,
    output_video_folder: str,
    write_results_video: bool,  # noqa: FBT001
) -> None:
    """Process a single video file for fish counting.

    Reads a video file frame by frame, applies object detection and counting,
    and optionally saves the processed video with detection overlays.

    Args:
        video_file: Path to the input video file to process
        counter: CustomObjectCounter instance for fish detection and counting
        output_video_folder: Directory where processed videos will be saved
        write_results_video: If True, saves processed video with detection overlays

    Returns:
        None
    """
    logger.info(f"Processing video: {video_file}")
    counter.video_filename = os.path.basename(video_file).split(".")[0]

    frame_width, frame_height, fps = get_video_resolution(video_file)

    if write_results_video:
        output_video_path = os.path.join(
            output_video_folder, f"counts_{os.path.basename(video_file)}"
        )
        logger.info(f"Saving video to: {output_video_path}")
        video_writer = cv2.VideoWriter(
            output_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame_width, frame_height)
        )
    else:
        video_writer = None

    cap = cv2.VideoCapture(video_file)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            logger.info("Reached end of video or no more frames to process.")
            break

        try:
            frame = counter.count(frame)
            if write_results_video and video_writer:
                video_writer.write(frame)

        except Exception:
            logger.exception("Unexpected error during frame processing. Skipping frame.")
            continue

    cap.release()

    counter.verify_and_finalize_counts(force_finalize=True)

    if write_results_video and video_writer:
        video_writer.release()

    return None


def main() -> None:
    """Main function to be called when running this script directly."""
    args = parse_args()

    width, height, _ = get_video_resolution(args.video_path)
    counting_region = calculate_coordinates(height, width)

    logger.info(f"Counting region coordinates set to: {counting_region}")

    logger.info("Initializing CustomObjectCounter...")
    counter = CustomObjectCounter(
        show=False,
        region=counting_region,
        model=args.model_path,
        show_in=True,
        show_out=True,
        line_width=2,
        tracker=args.tracker_config,
        device=args.device,
        persist=True,
        agnostic_nms=True,
        conf=args.conf,
        iou=args.iou,
        output_json_folder=args.output_json_folder,
    )

    count_fish_in_video(
        video_file=args.video_path,
        counter=counter,
        output_video_folder=args.output_video_folder,
        write_results_video=args.write_results_video,
    )


if __name__ == "__main__":
    main()
