def get_processed_videos() -> list:
    """Placeholder: implement in your environment-specific layer."""
    msg = "Provide get_processed_videos() in your project."
    raise NotImplementedError(msg)


def check_unprocessed_videos(processed_list: list, video_list: list) -> list:
    """Return videos present in `video_list` that are not in `processed_list`.

    Args:
        processed_list (list): A list of processed video file names.
        video_list (list): A list of video file names.

    Returns:
        unprocessed_videos (list): A list of unprocessed video file names.
    """
    unprocessed_videos = [video for video in video_list if video not in processed_list]

    return unprocessed_videos


def calculate_unprocessed_percentage(unprocessed_videos: list, video_list: list) -> float:
    """Calculate the percentage of unprocessed videos.

    Args:
        unprocessed_videos (list): A list of unprocessed video file names.
        video_list (list): A list of video file names.

    Returns:
        float: The percentage of unprocessed videos.
    """
    if len(video_list) == 0 or len(unprocessed_videos) == 0:
        return 0.0
    return (len(unprocessed_videos) / len(video_list)) * 100
