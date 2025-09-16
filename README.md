# Monitoring fishing activity on the edge: mobilizing AI and edge technologies to advance near real-time electronic monitoring footage review

This repository contains the public release of an AI‑powered system developed to analyze electronic monitoring (EM) footage of longline fishing activity directly onboard vessels. By combining edge computing, computer vision, and automated reporting, this system replaces time-intensive manual review of EM footage with same-day, actionable intelligence.

It can:

- Detect, identify, and count catch in near real time using edge computing and computer vision

- Automate structured reporting of fishing activity

- Deliver actionable intelligence to fishery managers within hours of fishing events


## 📢 About This Repository

This project and its outcomes were designed to be reproducible and adaptable to other fisheries.
All source code, model weights, and deployment instructions will be **progressively released** here as components are documented, anonymized, and adapted for broader use.

The scope and sequence of these releases may evolve, but the intent is to make the most reusable parts of the system publicly available so others can adapt the workflow to their own vessels, species, and regulations.


## 📦 Released Components

### `cvat/` – Annotation Platform Setup

This folder contains instructions and scripts for installing [CVAT](https://cvat.org/), an open-source platform for video and image annotation. In this pilot project, CVAT was used to annotate EM footage for training the fish detector model.

> 📘 See `cvat/README.md` for installation and usage instructions


### `fish_detector_model/` – Fish Detector Training Pipeline

This directory contains all necessary scripts and configuration files to **fine-tune and evaluate a fish detection model** using your own annotated dataset. It includes a baseline model (`baseline_fish_detector.pt`) and guidance on customizing for your fishery.

> 📘 See `fish_detector_model/README.md` for detailed training instructions

### `onboard_system/ai_powered_system/fish_tracker_and_counter/` – Fish Tracking & Counting

This directory provides code to **track, classify, and count fish** in EM footage using a trained fish detector.
It uses multi-object tracking (BoT-SORT by default) and custom counting logic to detect IN/OUT events when fish cross a user-defined counting line along the vessel’s deck.

Outputs include:

- Annotated videos with bounding boxes and counts
- JSON event files for each detected crossing

> 📘 See `onboard_system/ai_powered_system/fish_tracker_and_counter/README.md` for usage instructions and details on adjusting the counting line for your vessel’s camera setup.


## 🌐 Project Page

For an overview of the project’s motivation, design, and impact, visit the **Project Showcase**:

🔗 **[Project Page](https://tnc-ca-geo.github.io/em_edge_review/)**


## 📄 Technical Report

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
