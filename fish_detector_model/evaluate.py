import argparse
from datetime import datetime

import yaml
from dotenv import load_dotenv
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate model performance")

    parser.add_argument(
        "--config",
        type=str,
        default="fish_detector_model/config/eval_args.yaml",
        help="Path to args.yaml with evaluation settings",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="fish_detector_model/baseline_model/baseline_fish_detector.pt",
        help="Path to YOLO model to evaluate",
    )
    parser.add_argument(
        "--data", type=str, required=True, help="Path to data.yaml with your custom dataset"
    )

    return parser.parse_args()


def main() -> None:
    """Main function to evaluate the YOLO model with custom settings."""
    args = parse_args()
    load_dotenv(override=True)

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    model = YOLO(args.model_path)

    model.val(
        data=args.data,
        project=cfg["project"],
        name=datetime.now().strftime("date_%Y%m%d_%H%M%S"),
        save_json=cfg["save_json"],
        conf=cfg["conf"],
        split=cfg["split"],
        agnostic_nms=cfg["agnostic_nms"],
    )


if __name__ == "__main__":
    main()
