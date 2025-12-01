from typing import List, Tuple

import cv2

from logger import get_logger

logger = get_logger(__name__)


def get_video_resolution(video_file: str) -> Tuple[int, int, float]:
    """Get resolution and FPS of a local video file.

    Args:
        video_file (str): Path to the local video file.

    Returns:
        tuple[int, int, float]: The width, height, and FPS of the video.
    """
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_file}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    cap.release()

    logger.info(f"Video properties: width={width}, height={height}, fps={fps}")
    return width, height, fps


def calculate_coordinates(height: int, width: int) -> List[Tuple[int, int]]:
    """Calculate the coordinates for a line based on the video dimensions.

    Args:
        height (int): The height of the video.
        width (int): The width of the video.

    Returns:
        list[tuple[int, int]]: A list containing the coordinates of the line.
    """
    x1 = 3
    x2 = width - 3

    y = int(3 * height / 4)

    return [(x1, y), (x2, y)]
