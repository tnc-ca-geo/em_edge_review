from datetime import timedelta

# ----------------------------------------------------------------------
# Aggregated Risk Score Configuration
# ----------------------------------------------------------------------
AGGREGATED_SCORE_MIN = 1
AGGREGATED_SCORE_MAX = 3
AGGREGATED_SCORE_ROUND_DECIMALS = 2
AGGREGATED_RISK_WEIGHTS = {
    "gps": 4,
    "illegal_species": 4,
    "elogs": 4,
    "model_underprediction": 1,
    "operational": 1,
}

# ----------------------------------------------------------------------
# Elogs Risk Score Configuration
# ----------------------------------------------------------------------
ELOGS_OVERPREDICTION_LOW_PERCENT = 10
ELOGS_OVERPREDICTION_MED_PERCENT = 30
ELOGS_UNDERPREDICTION_FLAG_PERCENT = 10

# ----------------------------------------------------------------------
# Operational Risk Score Configuration
# ----------------------------------------------------------------------
OPERATIONAL_GAP_THRESHOLD = timedelta(minutes=5, seconds=30)
EXPECTED_VIDEO_LENGTH = timedelta(minutes=5)
EXPECTED_RECORD_INTERVAL = timedelta(minutes=5)
OPERATIONAL_COVERAGE_MIN_DURATION = timedelta(hours=5, minutes=30)
OPERATIONAL_GAPS_PERCENT_LOW = 5
OPERATIONAL_GAPS_PERCENT_HIGH = 10

# ----------------------------------------------------------------------
# Timezone and Localization
# ----------------------------------------------------------------------
LOCAL_TZ_NAME = "America/Costa_Rica"

# ----------------------------------------------------------------------
# GPS Risk Score Configuration
# ----------------------------------------------------------------------
GPS_MAX_TIME_DIFF_MINUTES = 30
GPS_DEFAULT_MAP_CENTER_LAT = 9.7489
GPS_DEFAULT_MAP_CENTER_LON = -83.7534
GPS_DEFAULT_MAP_ZOOM = 6
GPS_DISTANCE_TO_BOUNDARY_KM_THRESHOLD = 10
EEZ_PATH = "tests/dummy_data/automated_reporting/geospatial_layers/eez.geojson"
MPA_PATH = "tests/dummy_data/automated_reporting/geospatial_layers/mpa.geojson"
COAST_BUFFER_PATH = "tests/dummy_data/automated_reporting/geospatial_layers/coast_buffer.geojson"

# ----------------------------------------------------------------------
# Model Underprediction Risk Score Configuration
# ----------------------------------------------------------------------
MODEL_UNDERPREDICTION_THRESHOLD_HIGH_PERCENT = 10
MODEL_UNDERPREDICTION_THRESHOLD_LOW_PERCENT = 5
MODEL_UNDERPREDICTION_UNDER_RATIO_HIGH_PERCENT = 30

# ----------------------------------------------------------------------
# Daily Report Generation Configuration
# ----------------------------------------------------------------------
DUMMY_DATA_BASE_PATH = "tests/dummy_data/automated_reporting"
EXPECTED_FPS = 12
DISCARDED_MATCHING_THRESH = 1440  # 2 minutes
