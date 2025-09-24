# 🎣 Fish Tracker & Counter

This directory contains code to track, classify, and count fish in EM footage using your trained detector. 

The system follows each fish across frames, and records when it crosses a counting line drawn on the edge of the vessel's deck. It can then:

- Save an annotated video showing the tracks and counts
- Export JSON event files that log each IN/OUT crossing

It builds on Ultralytics YOLO’s tracking (BoT-SORT by default) and adds custom counting logic designed for longline fisheries.

## 🔧 Setup

Before running the scripts, ensure you have:

- Installed all dependencies (see the root-level `README.md`)
- A trained fish detector (e.g., `fish_detector_model/baseline_model/baseline_fish_detector.pt`)
- Optional: Adjusted tracker settings in `config/botsort.yaml` or pass your own YAML path via `--tracker_config`

## 🚀 Quick start

### ▶️ Run on a test video

Try the included test clip (download it [here](https://github.com/user-attachments/assets/220d572c-adcc-4f01-aa8f-32b0d2c56112))

```bash
uv run onboard_system/ai_powered_system/fish_tracker_and_counter/vessel_retained_discard_analysis.py \
  --video_path path/to/your/test_video.mov \
  --model_path fish_detector_model/baseline_model/baseline_fish_detector.pt \
  --write_results_video
```

Flags:
- `--video_path` Path to input video (example: path/to/your/test_video.mov)
- `--model_path` Path to YOLO model `.pt` (default: `fish_detector_model/baseline_model/baseline_fish_detector.pt`)
- `--write_results_video` Add this flag if you want an annotated video saved
- `--output_video_folder` Folder where annotated videos are saved (default: `tests/dummy_data/fish_tracker_and_counter/output/video`)
- `--output_json_folder` Folder where JSON events are saved (default: `tests/dummy_data/fish_tracker_and_counter/output/catch_events`)
- `--conf` Detection confidence threshold (default `0.30`)
- `--iou` Intersection-over-Union threshold for non-maximum suppression (default `0.10`)
- `--tracker_config` Path to tracker YAML (default BoT-SORT at `config/botsort.yaml`)
- `--device` Specifies the device for inference (e.g., cpu, cuda:0 or 0) (default `"0"`)

### 📦 Outputs

- Annotated video (if `--write_results_video`):

  `tests/dummy_data/fish_tracker_and_counter/output/video/counts_<original_name>.mov`

- Event JSONs per finalized crossing:

  `tests/dummy_data/fish_tracker_and_counter/output/catch_events/<video_stem>_catch_<track>_<label>_<IN|OUT>.json`

Example JSON:

```json
{
    "track_id": 2,
    "global_track_id": 2,
    "label": "DOL",
    "event_type": "IN",
    "avg_conf_score": 0.8194466039760789,
    "video_filename": "test_video",
    "frame_number": 69,
    "global_frame": 69
}
```

This means a fish labeled "DOL" (dolphinfish) was counted as IN at frame 69 of the video, with an average model confidence of ~82%.

## 📁 Configuration

The tracker settings are in `config/botsort.yaml`
Override at runtime with `--tracker_config /path/to/your.yaml`.

If tracking seems unstable, try tuning:

- `track_high_thresh` — confidence threshold for first association
- `track_low_thresh` — threshold for second association
- `new_track_thresh` — threshold for starting a new track
- `track_buffer` — how long to keep a track after it disappears
- `match_thresh` — matching threshold for associations

For a deeper explanation, see:
- 📄 [BoT-SORT paper](https://arxiv.org/abs/2206.14651) — details the underlying algorithm  
- 📘 [Ultralytics tracking docs](https://docs.ultralytics.com/modes/track/#tracker-arguments) — practical guidance on usage

## 💡 Notes

- By default, the tracker runs on GPU 0 (`device=0`). 
  For CPU-only systems, run with `--device cpu`(slower runtime).

- The counting line must be **manually placed along the edge of the vessel’s deck**.
  - In the provided `test_video`, the line is already set for its camera angle.
  - For your own videos, you might need to adjust the y-coordinate of the line in `utils/calculate_line_coordinates.py` so it aligns with your vessel’s deck in your camera feed.
