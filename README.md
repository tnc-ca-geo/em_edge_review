# Monitoring fishing activity on the edge: mobilizing AI and edge technologies to advance near real-time electronic monitoring footage review

This repository contains the public release of an AI‑powered system developed to analyze electronic monitoring (EM) footage of longline fishing activity directly onboard vessels. By combining edge computing, computer vision, and automated reporting, this system replaces time-intensive manual review of EM footage with same-day, actionable intelligence.

It can:

- Detect, identify, and count catch in near real time using edge computing and computer vision

- Automate structured reporting of fishing activity

- Deliver actionable intelligence to fishery managers within hours of fishing events


## 📢 About this repository

This project and its outcomes were designed to be reproducible and adaptable to other fisheries.
All source code, model weights, and deployment instructions will be **progressively released** here as components are documented, anonymized, and adapted for broader use.

The scope and sequence of these releases may evolve, but the intent is to make the most reusable parts of the system publicly available so others can adapt the workflow to their own vessels, species, and regulations.


## 📦 Released components

### `cvat/` – Annotation platform setup

This folder contains instructions and scripts for installing [CVAT](https://cvat.org/), an open-source platform for video and image annotation. In this pilot project, CVAT was used to annotate EM footage for training the fish detector model.

> 📘 See `cvat/README.md` for installation and usage instructions


### `fish_detector_model/` – Fish detector training pipeline

This directory contains all necessary scripts and configuration files to **fine-tune and evaluate a fish detection model** using your own annotated dataset. It includes a baseline model (`baseline_fish_detector.pt`) and guidance on customizing for your fishery.

> 📘 See `fish_detector_model/README.md` for detailed training instructions

### `onboard_system/ai_powered_system/fish_tracker_and_counter/` – Fish Tracking & Counting

This directory provides code to **track, classify, and count fish** in EM footage using a trained fish detector.
It uses multi-object tracking (BoT-SORT by default) and custom counting logic to detect IN/OUT events when fish cross a user-defined counting line along the vessel’s deck.

Outputs include:

- Annotated videos with bounding boxes and counts
- JSON event files for each detected crossing

> 📘 See `onboard_system/ai_powered_system/fish_tracker_and_counter/README.md` for usage instructions and details on adjusting the counting line for your vessel’s camera setup.

### `onboard_system/automated_reporting/` - Automated Daily Report & Risk Scoring

This directory contains the components used to generate a daily summary of fishing activity from the AI system’s outputs. It combines catch detections, GPS tracks, and e-log data into a clear, shareable report designed to provide actionable insight to fishery managers.

The reporting system includes:
- Daily Catch Report, featuring:
  - Total retained and discarded catch
  - A timestamped catch sequence with species identification and evidence frames
  - Catch breakdowns by group, subgroup, and species
  - A map showing the location of catch events
- Daily Risk Score, highlighting potential compliance or operational concerns, including:
  - Retention of prohibited species
  - Fishing near or inside restricted areas
  - Potential under-reporting of catch
  - Operational data gaps (e.g., missing GPS or video)

Outputs are provided as:
- A human-readable HTML report
- A structured JSON summary for further analysis

> 📘 See `onboard_system/automated_reporting/README.md` for setup instructions and guidance on customizing reporting and risk scoring for your fishery.

## 🌐 Project page

For an overview of the project’s motivation, design, and impact, visit the **Project Showcase**:

🔗 **[Project Page](https://tnc-ca-geo.github.io/em_edge_review/)**


## 📄 Technical report

The full technical report provides **end‑to‑end details** on the AI-powered system:

📥 **[Download Technical Report (PDF)](LINK_TO_FINAL_REPORT)**

## 🚀 Installation

To get started with the project, follow these steps:

1. Install the [`uv`](https://docs.astral.sh/uv/getting-started/installation/) Python project manager.

2. Sync project dependencies using the `pyproject.toml` file:

    ```bash
    uv sync
    ```

3. Create a `.env` file from the provided `.env.template`. Remember to replace all placeholder values with actual values.

## 🐳 Docker deployment

For production deployment or containerized environments, you can use Docker to run the system components.

### Prerequisites

- Docker and Docker Compose installed on your system
- Raw video files placed in the `./videos` directory
- Model weights in `./fish_detector_model/baseline_model/`

### Building the Docker image

Build the container image from the root directory:
```bash
docker compose build
```

This creates the `ai-powered-system:latest` image with all dependencies installed.

### Running the system

The system provides two main services that can be run independently:

#### 1. Fish Tracking & Counting

Process videos to detect, track, and count fish:
```bash
docker compose run --rm inference
```

This will:
- Process videos from `./videos/` directory
- Use the model at `./fish_detector_model/baseline_model/baseline_fish_detector.pt`
- Save annotated videos to `./tests/dummy_data/fish_tracker_and_counter/output/video/`
- Save catch event JSONs to `./tests/dummy_data/fish_tracker_and_counter/output/catch_events/`

#### 2. Daily Report generation

Generate the automated daily report:
```bash
docker compose run --rm reporting
```

This will:
- Process catch events from the inference output
- Generate HTML and JSON reports in `./tests/dummy_data/fish_tracker_and_counter/output/daily_report/`

### Customizing for your deployment

Edit `docker-compose.yml` to adjust:
- **Video input path:** Change `./videos` to your video directory
- **Output paths:** Modify volume mounts to match your preferred locations
- **Model path:** Update if using a custom trained model

> 💡 The Docker image uses CPU-only PyTorch by default. For GPU acceleration, modify the Dockerfile to install CUDA-enabled PyTorch and ensure the NVIDIA Container Toolkit is installed on your host system.