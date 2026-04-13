"""
Custom Object Counter Module - MODIFIED ULTRALYTICS WORK

This module provides the CustomObjectCounter class, which extends the BaseObjectCounter
from Ultralytics to implement specific IN and OUT counting logic based on y-coordinate crossings
in a video stream.

MODIFICATION NOTICE:
- This work is derived from Ultralytics ObjectCounter (https://github.com/ultralytics/ultralytics)
- Modifications made: January 7, 2025
- Modified components: Extended BaseObjectCounter with deferred counting logic, track history storage,
  and custom bounding box label formatting for fish detection tracking

LICENSE COMPLIANCE:
This work is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
As per AGPL-3.0 terms, any derivative works must also be licensed under AGPL-3.0.
Original Ultralytics code is licensed under AGPL-3.0.

For full license details, see: https://www.gnu.org/licenses/agpl-3.0.html
"""


import json
import os
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
from ultralytics.solutions import ObjectCounter as BaseObjectCounter
from ultralytics.utils.plotting import Annotator, colors

from logger import get_logger

DISAPPEARANCE_THRESHOLD = 30  # Allow up to 30 frames of disappearance before finalizing
MIN_TRACK_LENGTH_THRESHOLD = 1 * 12  # Minimum number of frames to consider a track for counting
DEFERRED_COUNTING_THRESHOLD = 30 * 12  # Number of frames to wait before finalizing counts

class CustomObjectCounter(BaseObjectCounter):
    """CustomObjectCounter extends BaseObjectCounter to implement specific IN and OUT counting logic.

    This class tracks objects in a video stream and counts when they enter ("IN") or exit ("OUT")
    a designated region based on their movement across a predefined counting line. It introduces
    deferred counting to improve accuracy by waiting for a clearer detection of the object before
    finalizing the count and assigning the most frequent label across its tracking history.
    """

    def __init__(self, output_json_folder: str, **kwargs) -> None:  # noqa: ANN003
        """Initializes the CustomObjectCounter.

        Args:
            output_json_folder (str): Directory where JSON output files will be saved.
            **kwargs: Additional keyword arguments passed to the BaseObjectCounter.
        """
        super().__init__(**kwargs)
        self.logger = get_logger(__name__)
        self.track_history = defaultdict(
            lambda: {"positions": [], "labels": [], "confidences": []}
        )  # Extend the track history to also store class labels
        self.pending_counts = defaultdict(list)  # Stores crossing events to defer counting
        self.missing_frames = defaultdict(int)  # Track how long each object has been missing
        self.origin_above = defaultdict(
            bool
        )  # Track if the object originated above the counting line
        self.output_json_folder = output_json_folder
        self.video_filename = ""
        self.video_frame_count = 0  # Per-video frame counter
        self.global_frame_count = 0  # Global frame counter across all videos
        self.tracker = kwargs.get("tracker")
        self.device = kwargs.get("device")
        self.tracking_data = []
        self.id_offset = 0

    def count(self, im0: np.ndarray) -> np.ndarray:  # noqa: ANN101
        """Overrides the count method in BaseObjectCounter to process a video frame for object detection, tracking, and counting.

        Enhancements include:
        - Add track ID and confidence score in bounding box labels.
        - Store cross events for deferred counting.
        - Finalize counts only after a delay to improve accuracy.

        Args:
            im0 (numpy.ndarray): The input image or frame to be processed.

        Returns:
            (numpy.ndarray): The processed image with annotations and count information.
        """
        self.video_frame_count += 1
        self.global_frame_count += 1
        if not self.region_initialized:
            self.initialize_region()
            self.region_initialized = True

        self.annotator = Annotator(im=im0, line_width=self.line_width)
        self.extract_tracks(im0=im0)

        self.annotator.draw_region(
            reg_pts=self.region, color=(104, 0, 123), thickness=self.line_width * 2
        )

        for box, track_id, cls, conf in zip(
            self.boxes, self.track_ids, self.clss, self.confidences
        ):
            label = f"ID {track_id}-{self.names[cls]}-{conf:.2f}"

            # Draw bounding box and counting region
            self.annotator.box_label(box=box, label=label, color=colors(cls, True))
            self.store_extended_tracking_history(track_id=track_id, box=box, cls=cls, conf=conf)
            self.store_classwise_counts(cls=cls)

            # Draw tracks of objects
            self.annotator.draw_centroid_and_tracks(
                track=self.track_line, color=colors(int(cls), True), track_thickness=self.line_width
            )

            # Store previous position of track for object counting
            prev_position = None
            if (
                track_id in self.track_history
                and len(self.track_history[track_id]["positions"]) > 1
            ):
                prev_position = self.track_history[track_id]["positions"][-2]

            self.detect_cross_events(
                box=box, track_id=track_id, prev_position=prev_position, cls=cls
            )

            x1, y1, x2, y2 = (float(x) for x in box)
            detection_info = {
                "video_filename": self.video_filename,
                "frame_number": self.video_frame_count,
                "global_frame": self.global_frame_count,
                "track_id": track_id,
                "class": self.names[cls],  # using the name of the class
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "confidence": conf,
            }
            self.tracking_data.append(detection_info)

        self.verify_and_finalize_counts()

        self.display_counts(im0=im0)
        self.display_output(im0=im0)

        return im0

    def extract_tracks(self, im0: np.ndarray) -> None:
        """Run the tracker on the current frame and cache boxes/classes/ids/confidences.

        Args:
            im0 (ndarray): The input image or frame.
        """
        self.tracks = self.model.track(
            source=im0,
            persist=True,
            classes=self.CFG["classes"],
            conf=self.CFG["conf"],
            iou=self.CFG["iou"],
            agnostic_nms=self.CFG["agnostic_nms"],
            tracker=self.tracker,
            verbose=False,
            device=self.device,
        )

        # Extract tracks for OBB or object detection
        self.track_data = self.tracks[0].obb or self.tracks[0].boxes

        if self.track_data and self.track_data.id is not None:
            self.boxes = self.track_data.xyxy.cpu()
            self.clss = self.track_data.cls.cpu().tolist()
            self.track_ids = self.track_data.id.int().cpu().tolist()
            self.confidences = self.track_data.conf.cpu().tolist()
        else:
            self.boxes, self.clss, self.track_ids, self.confidences = [], [], [], []

    def store_extended_tracking_history(
        self,
        track_id: int,
        box: List[float],
        cls: int,
        conf: float,
    ) -> None:
        """Stores the tracking history for a given track ID, including positions, class labels, and confidence scores.

        Args:
            track_id (int): The unique identifier for the tracked object.
            box (List[float]): The bounding box coordinates [x1, y1, x2, y2].
            cls (int): The class index of the detected object.
            conf (float): The confidence score of the detection.

        """
        n_frames_history = DEFERRED_COUNTING_THRESHOLD  # Store up to 30 seconds of tracking history
        track_info = self.track_history[track_id]
        self.track_line = track_info["positions"]
        self.track_line.append(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
        if len(self.track_line) > n_frames_history:
            self.track_line.pop(0)

        track_info["labels"].append(cls)
        if len(track_info["labels"]) > n_frames_history:
            track_info["labels"].pop(0)

        track_info["confidences"].append(conf)
        if len(track_info["confidences"]) > n_frames_history:
            track_info["confidences"].pop(0)

        # Check and store the origin position (first detected position)
        if track_id not in self.origin_above:
            first_y_center = (box[1] + box[3]) / 2
            line_y = self.region[0][1]
            self.origin_above[track_id] = (
                first_y_center < line_y
            )  # True if it originated above the line

    def detect_cross_events(
        self,
        box: List[float],
        track_id: int,
        prev_position: Optional[Tuple[float, float]],
        cls: int,
    ) -> None:
        """Queue a crossing event if the motion segment intersects the counting line.

        Args:
            box (List[float]): Bounding box coordinates [x1, y1, x2, y2].
            track_id (int): Unique identifier for the tracked object.
            prev_position (Tuple[float, float]): Previous center position (x, y) of the object.
            cls (int): Class index of the object.
        """
        if prev_position is None:
            return None  # Cannot determine movement without previous position

        # Calculate the center of the bounding box for the current frame
        cur_x_center = (box[0] + box[2]) / 2.0
        cur_y_center = (box[1] + box[3]) / 2.0

        # Extract previous center positions
        prev_x, prev_y = prev_position

        # Create a line segment from the previous position to the current center
        crossed_line = self.LineString([(prev_x, prev_y), (cur_x_center, cur_y_center)]).intersects(
            self.r_s
        )

        if not crossed_line:
            return None  # No crossing detected

        # Store the event instead of counting immediately
        self.pending_counts[track_id].append(
            {
                "frame": self.video_frame_count,
                "global_frame": self.global_frame_count,
                "position": (cur_x_center, cur_y_center),
                "cls": cls,
                "box": box,
                "video_filename": self.video_filename,
            }
        )

    def verify_and_finalize_counts(self, force_finalize: bool = False) -> None:  # noqa: FBT001, FBT002
        """Processes pending crossing events and finalizes counts for disappeared or completed tracks.

        Args:
            force_finalize (bool): If True, all pending tracks will be forcefully terminated and counted.
        """
        to_delete = []

        for track_id, events in self.pending_counts.items():
            if not self.should_finalize_track(
                track_id=track_id, events=events, force_finalize=force_finalize
            ):
                continue

            self.finalize_track(track_id=track_id, events=events)
            to_delete.append(track_id)

        for track_id in to_delete:
            self.cleanup_finalized_track(track_id=track_id)

    def should_finalize_track(
        self,
        track_id: int,
        events: List[Dict],
        force_finalize: bool,  # noqa: FBT001
    ) -> bool:
        """Determines whether a track should be finalized.

        A track is finalized if:
        - It has been missing for a certain number of frames (DISAPPEARANCE_THRESHOLD), or
        - It has been pending for a certain number of frames (DEFERRED_COUNTING_THRESHOLD), or
        - The force_finalize flag is set to True.
        Additionally, the track must have a minimum length (MIN_TRACK_LENGTH_THRESHOLD) to be considered valid.

        Args:
            track_id (int): Unique identifier for the tracked object.
            events (List[Dict]): List of crossing events for the track.
            force_finalize (bool): If True, the track will be finalized regardless of other conditions.

        Returns:
            bool: True if the track should be finalized, False otherwise.
        """
        # If track_id is still in self.track_ids (visible in the frame), reset its disappearance counter
        if track_id in self.track_ids and not force_finalize:
            self.missing_frames[track_id] = 0
            return False  # Shouldn't finalize if the object is still being tracked

        # If track_id is missing, increment its disappearance counter
        self.missing_frames[track_id] += 1

        track_info = self.track_history[track_id]
        track_length = len(track_info["positions"])
        frames_since_crossing = self.video_frame_count - events[0]["frame"]

        gone_too_long = self.missing_frames[track_id] >= DISAPPEARANCE_THRESHOLD
        counted_delay = frames_since_crossing >= DEFERRED_COUNTING_THRESHOLD
        long_enough = track_length >= MIN_TRACK_LENGTH_THRESHOLD

        return (gone_too_long or counted_delay or force_finalize) and long_enough

    def finalize_track(self, track_id: int, events: List[Dict]) -> None:
        """Finalizes a track and records IN/OUT events. Uses the latest crossing to decide IN vs OUT, and the track's origin to avoid double counts.

        Args:
            track_id (int): Unique identifier for the tracked object.
            events (List[Dict]): List of crossing events for the track.
        """
        mode_label = self.get_mode_label(track_id=track_id)
        if mode_label is None or mode_label not in self.names:
            self.logger.warning(f"Invalid mode label for track {track_id}: {mode_label}")
            return

        avg_conf_score = self.get_avg_conf_score(track_id=track_id)

        # Use the latest crossing position for counting direction
        last_event = events[-1]
        cur_y_center = last_event["position"][1]
        line_y = self.region[0][1]
        class_name = self.names[mode_label]
        from_above = self.origin_above.get(track_id, False)

        self.logger.debug(f"Track {track_id} current center Y: {cur_y_center}, line Y: {line_y}")
        if cur_y_center < line_y:  # IN event
            # Check if fish originated above the line
            if not from_above:  # Only count IN if it did NOT originate above
                self.in_count += 1
                self.classwise_counts[class_name]["IN"] += 1
                self.save_catch_to_json(
                    track_id=track_id,
                    label=class_name,
                    event_type="IN",
                    avg_conf_score=avg_conf_score,
                )
                self.logger.info(f"Track {track_id} finalized as IN ({class_name})")
            else:
                self.logger.info(f"Track {track_id} NOT counted as IN (originated above)")

        else:  # OUT event
            # If the fish originated below the line count it IN FIRST
            if not from_above:
                self.in_count += 1
                self.classwise_counts[class_name]["IN"] += 1
                self.save_catch_to_json(
                    track_id=track_id,
                    label=class_name,
                    event_type="IN",
                    avg_conf_score=avg_conf_score,
                )
                self.logger.info(f"Track {track_id} first counted as IN (originated below).")
            self.out_count += 1
            self.classwise_counts[class_name]["OUT"] += 1
            self.save_catch_to_json(
                track_id=track_id,
                label=class_name,
                event_type="OUT",
                avg_conf_score=avg_conf_score,
            )
            self.logger.info(f"Track {track_id} finalized as OUT ({class_name})")

    def cleanup_finalized_track(self, track_id: int) -> None:
        """Removes tracking data for a finalized track.

        Args:
            track_id (int): Unique identifier for the tracked object.
        """
        self.pending_counts.pop(track_id, None)
        self.missing_frames.pop(track_id, None)
        self.track_history.pop(track_id, None)
        self.origin_above.pop(track_id, None)

    def get_mode_label(self, track_id: int) -> Optional[int]:
        """Returns the most frequent label for a given track ID.

        Args:
            track_id (int): Unique identifier for the tracked object.

        Returns:
            int: Most frequent class label.
        """
        if track_id in self.track_history and "labels" in self.track_history[track_id]:
            label_history = self.track_history[track_id]["labels"]
            mode = Counter(label_history).most_common(1)[0][0]
            return mode
        return None

    def get_avg_conf_score(self, track_id: int) -> float:
        """Returns the average confidence score for a given track ID.

        Args:
            track_id (int): Unique identifier for the tracked object.

        Returns:
            float: Average confidence score.
        """
        if track_id in self.track_history and "confidences" in self.track_history[track_id]:
            confidence_history = self.track_history[track_id]["confidences"]
            avg_conf_score = sum(confidence_history) / len(confidence_history)
            return avg_conf_score
        return 0.0

    def save_catch_to_json(
        self,
        track_id: int,
        label: str,
        event_type: str,
        avg_conf_score: float,
    ) -> None:
        """Saves the detected catch event as a JSON file.

        Args:
            track_id (int): Unique identifier for the tracked object.
            label (str): Class label of the detected object.
            event_type (str): Type of event ("IN" or "OUT").
            avg_conf_score (float): Average confidence score of the detections for this track.
        """
        event = {}
        # Determine which event to use based on event_type
        if event_type == "IN":
            event = (
                self.pending_counts[track_id][0] if track_id in self.pending_counts else {}
            )  # if count is IN, use the first event
        elif event_type == "OUT":
            event = (
                self.pending_counts[track_id][-1] if track_id in self.pending_counts else {}
            )  # if count is OUT, use the last event

        # Extract the frame number and filename
        event_frame = event.get("frame", "unknown")
        event_global_frame = event.get("global_frame", "unknown")
        event_filename = event.get("video_filename", "unknown")

        output_file = os.path.join(
            self.output_json_folder,
            f"{event_filename}_catch_{track_id}_{label}_{event_type}.json",
        )

        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        data = {
            "track_id": track_id,
            "global_track_id": track_id + self.id_offset,
            "label": label,
            "event_type": event_type,
            "avg_conf_score": avg_conf_score,
            "video_filename": event_filename,
            "frame_number": event_frame,
            "global_frame": event_global_frame,
            # gps coordinates
            # fish size
        }

        with open(output_file, "w") as json_file:
            json.dump(data, json_file, indent=4)

        self.logger.info(f"Saved catch data to {output_file}")
