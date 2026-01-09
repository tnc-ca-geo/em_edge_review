import argparse
import os
from datetime import datetime

import mlflow
import yaml
from dotenv import load_dotenv
from ultralytics import YOLO, settings

from logger import get_logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Finetune the fish detector with your custom dataset"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="fish_detector_model/config/train_args.yaml",
        help="Path to args.yaml configuration file",
    )
    parser.add_argument(
        "--data",
        required=True,
        type=str,
        help="Path to data.yaml with your custom dataset",
    )
    parser.add_argument(
        "--mlflow", dest="mlflow", action="store_true", help="Enable MLflow tracking"
    )
    parser.set_defaults(mlflow=False)
    return parser.parse_args()


def main() -> None:
    """Main function to train the YOLO model with custom settings."""
    logger = get_logger(__name__)

    args = parse_args()
    load_dotenv(override=True)

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    if args.mlflow:
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if not tracking_uri:
            logger.error("MLFLOW_TRACKING_URI is not set in environment variables.")
        settings.update({"mlflow": True})
        mlflow.set_tracking_uri(tracking_uri)
    else:
        settings.update({"mlflow": False})

    model = YOLO(cfg["model"])
    
    cfg.pop("model")
    cfg["data"] = args.data
    cfg["name"] = datetime.now().strftime("date_%Y%m%d_%H%M%S")

    model.train(**cfg)


if __name__ == "__main__":
    main()
