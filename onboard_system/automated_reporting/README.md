# 📊 Automated Daily Reporting & Risk Scoring

This directory contains code to generate a daily summary of fishing activity based on the outputs of the AI-powered system. The report combines:

- Catch detections (from the Fish Tracker & Counter)
- GPS vessel locations
- Electronic logbook data (e-logs)
- Video processing metadata (processed vs expected videos)

The output is a shareable daily report designed to provide actionable insight to fishery managers.

## 🔧 Setup

Before running the scripts, ensure you have:

- Installed all dependencies (see the root-level `README.md`)
- A trained fish detector (e.g., `fish_detector_model/baseline_model/baseline_fish_detector.pt`)
- Run the Fish Tracker & Counter to produce catch event files
- Optional: Adjusted `settings.py` to match your fishery’s policies and operational expectations
- Optional: Implemented integrations for your existing Electronic Monitoring infraestructure (see “Environment-Specific Integration” below)

## 🚀 Quick start
### 🧪 Run with test data

You can preview the daily report without connecting to real vessel systems:

```bash
uv run onboard_system/automated_reporting/generate_daily_report.py --use_dummy_data
```

This produces:

```bash
tests/dummy_data/automated_reporting/output/
 ├── daily_report.json
 └── daily_report.html   ← open this in your browser
```

This is the fastest way to understand the report structure and visuals before integrating real data.

### 📦 Outputs

The daily report includes:
- Summary statistics (retained, discarded, and total catch)
- Timestamped catch sequence, with species identification and evidence frame previews
- Breakdowns by species, species group, and subgroup
- GPS map of catch events
- A Daily Risk Score based on:

  | **Risk Component**          | **Description**                                                       | **Primary Concern**                                   |
  |-----------------------------|-----------------------------------------------------------------------|--------------------------------------------------------|
  | E-Log Risk              | Discrepancy between AI-identified catches and captain’s e-log records | Potential under-reporting of catch            |
  | Illegal Species Risk    | Detection of illegal or ETP species in the catch                      | Retention or interaction with protected species        |
  | GPS Risk                | Geolocation of fishing activity relative to regulated areas           | Fishing in MPAs / restricted zones / sensitive habitat |
  | Model Underprediction Risk | Signs the AI system may have missed catch events                    | Reduced reliability of automated monitoring            |
  | Operational Risk        | Missing or inconsistent video/GPS data                                | Loss of monitoring coverage enabling non-compliance    |

Outputs are saved as:

| **File**            | **Purpose**                                  |
|---------------------|----------------------------------------------|
| daily_report.html   | For human review and communication           |
| daily_report.json   | For analytics, dashboards, or logging        |

## 🐟 Adapt to your fishery

### Species definitions
Species metadata and display settings are configured in:

```bash
onboard_system/species_registry.py
```

This file defines:
- FAO code → species name (EN/ES/scientific)
- Species grouping (used in summary tables)
- Which species are considered illegal in the fishery
- Icon sets used in the daily report UI

Example entry:
```bash
FISH_MAPPING = {
    "ALB": {
        "scientific_name": "Thunnus alalunga",
        "name_en": "Albacore",
        "group": "fish",
        "group_subcategory": "tuna",
        "iucn_category": "LC",
        ...
    },
}

ILLEGAL_SPECIES = ["OCS", "MAN", "SPL", ...]
```

> 💡 You will need to create or modify this mapping to match the species present in your fishery.

### Configuration and thresholds
All report behavior and risk scoring thresholds are defined in:

```bash
onboard_system/automated_reporting/settings.py
```

This file lets you tune the reporting system to the rules, vessel operations, and monitoring expectations of your fishery. Key configuration categories include:
| ***Category***                      | ***Controls***                                             |
| --------------------------------- | -------------------------------------------------------- |
| Risk score weighting              | How much each component contributes to the overall score |
| E-log discrepancy tolerance       | Thresholds for under-reporting alerts                |
| Operational coverage              | Minimum acceptable video/GPS uptime and gap thresholds   |
| Mapping defaults                  | Map zoom, center, and distance alerts                    |
| Model underprediction sensitivity | When to flag model underprediction risk
| Timezone & FPS                    | Local time conversion and expected recording rate        |



> 💡 These values are meant to be tailored to each fishery’s rules and monitoring objectives.

### 🧩 Environment-Specific Integration

To use this system with real vessel infrastructure, implement the following placeholders:

```bash
def extract_evidence_frames(...)
def load_elog_data_from_db(...)
def _load_gps_data_from_db(...)
def get_processed_videos(...)
def get_todays_videos_from_server(...)
def get_gps_records_from_server(...)
```

You will need to implement these functions so they connect to **your actual data sources**.  
For example, depending on your setup, you might:

- Query a database where GPS or e-logs are stored
- Fetch video or metadata from a vessel server or cloud bucket
- Read `.json` or `.csv` files from a synchronized onboard storage directory
- Use an API provided by your monitoring system

> 💡 These functions are contained in clear, isolated modules so you can integrate without modifying the reporting core.

### Run with live data sources
Once configured, generate the real daily report:

```bash
uv run onboard_system/automated_reporting/generate_daily_report.py --inference_results_path /path/to/fish_tracker_and_counter/inference/results
```

Flags:
-  `--report_path`: Folder where the report will be saved (default: `tests/dummy_data/fish_tracker_and_counter/output/daily_report`)
- `--inference_results_path`: Folder where the inference results are saved (default: `tests/dummy_data/fish_tracker_and_counter/output/catch_events`)
