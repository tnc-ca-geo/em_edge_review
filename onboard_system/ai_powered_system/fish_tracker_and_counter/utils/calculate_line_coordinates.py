import os
from typing import List, Tuple

import cv2
import paramiko

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


def get_video_resolution_remote(
    remote_path: str, sftp: paramiko.SFTPClient, local_folder: str
) -> Tuple[int, int, float]:
    """Download a remote video, get its resolution/FPS, then delete it.

    Args:
        remote_path (str): The path to the video on the remote server.
        sftp (paramiko.SFTPClient): The SFTP client to use for downloading the video.
        local_folder (str): The local folder to save the downloaded video.

    Returns:
        tuple[int, int, float]: The width, height, and FPS of the video.
    """
    local_path = os.path.join(local_folder, os.path.basename(remote_path))
    sftp.get(remote_path, local_path)
    try:
        return get_video_resolution(local_path)
    finally:
        os.remove(local_path)


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
