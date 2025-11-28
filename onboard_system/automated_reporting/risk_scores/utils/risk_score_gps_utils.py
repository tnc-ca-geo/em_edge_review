import json
import os
import sys
from datetime import datetime
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import pytz
from dotenv import load_dotenv
from folium.plugins import BeautifyIcon

from logger import get_logger
from onboard_system.automated_reporting import settings
from onboard_system.species_registry import FISH_MAPPING, ILLEGAL_SPECIES

load_dotenv(override=True)

DUMMY_DATA_BASE_PATH = settings.DUMMY_DATA_BASE_PATH
LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)
GPS_TIME_DIFF_THRESHOLD = settings.GPS_MAX_TIME_DIFF_MINUTES
GPS_DEFAULT_MAP_CENTER_LAT = settings.GPS_DEFAULT_MAP_CENTER_LAT
GPS_DEFAULT_MAP_CENTER_LON = settings.GPS_DEFAULT_MAP_CENTER_LON
GPS_DEFAULT_MAP_ZOOM = settings.GPS_DEFAULT_MAP_ZOOM
EEZ_PATH = settings.EEZ_PATH
MPA_PATH = settings.MPA_PATH
COAST_BUFFER_PATH = settings.COAST_BUFFER_PATH

logger = get_logger(__name__)

def _load_gps_data_from_db() -> pd.DataFrame:
    """Placeholder: implement in your environment-specific layer."""
    msg = "Provide _load_gps_data_from_db() in your project."
    raise NotImplementedError(msg)


def _find_nearest_gps(catch_time: datetime, gps_df: pd.DataFrame) -> dict:
    """Find the nearest GPS data point to a given catch time.

    Args:
        catch_time (datetime): The time of the catch event.
        gps_df (pd.DataFrame): DataFrame containing GPS data

    Returns:
        dict: A dictionary containing the nearest GPS data point and the confidence of the match.
    """
    gps_df = gps_df.copy()
    gps_df["time_diff"] = (gps_df["gps_datetime"] - catch_time).abs()
    nearest = gps_df.loc[gps_df["time_diff"].idxmin()]

    time_diff_minutes = nearest["time_diff"].total_seconds() / 60

    confidence = "low" if time_diff_minutes >= GPS_TIME_DIFF_THRESHOLD else "high"

    return {
        "lat": nearest["lat"],
        "lon": nearest["lon"],
        "gps_datetime": nearest["gps_datetime"],
        "outside_mpa": nearest["outside_mpa"],
        "in_eez": nearest["in_eez"],
        "outside_coast_buffer": nearest["outside_coast_buffer"],
        "dist_to_mpa_km": nearest["dist_to_mpa_km"],
        "dist_to_eez_km": nearest["dist_to_eez_km"],
        "dist_to_coast_buffer_km": nearest["dist_to_coast_buffer_km"],
        "confidence": confidence,
    }


def get_gps_data(
    catch_sequence: list,
    use_dummy_data: bool = False,  # noqa: FBT001, FBT002
) -> list:
    """Match GPS data with catch times and return a list of dictionaries containing the matched data.

    Args:
    catch_sequence (list): List of catch events.
    use_dummy_data (bool): Flag to use dummy data instead of real GPS data.

    Returns:
    list: List of dictionaries containing the matched GPS data for each catch event.
    """
    # Load GPS Data
    if use_dummy_data:
        base = Path(DUMMY_DATA_BASE_PATH)
        gps_df = pd.read_csv(base / "gps_data.csv")
        gps_df["gps_datetime"] = pd.to_datetime(gps_df["gps_datetime"]).dt.tz_convert(LOCAL_TZ)
    else:
        logger.info("Initializing database connection pool.")
        gps_df = _load_gps_data_from_db()

    gps_df = get_gps_risk_features(gps_df=gps_df)

    catches_with_gps = []
    for catch in catch_sequence:
        gps_info = _find_nearest_gps(catch_time=catch["estimated_catch_time"], gps_df=gps_df)
        label = catch["label"]
        catches_with_gps.append(
            {
                "label": label,
                "scientific_name": FISH_MAPPING.get(label, {}).get("scientific_name", "Unknown"),
                "name_en": FISH_MAPPING.get(label, {}).get("name_en", "Unknown"),
                "name_es": FISH_MAPPING.get(label, {}).get("name_es", "Unknown"),
                "illegal": bool(label in ILLEGAL_SPECIES),
                "event_type": catch["event_type"],
                "estimated_catch_time": catch["estimated_catch_time"],
                "lat": gps_info["lat"],
                "lon": gps_info["lon"],
                "gps_time": gps_info["gps_datetime"],
                "outside_mpa": gps_info["outside_mpa"],
                "in_eez": gps_info["in_eez"],
                "outside_coast_buffer": gps_info["outside_coast_buffer"],
                "dist_to_mpa_km": gps_info["dist_to_mpa_km"],
                "dist_to_eez_km": gps_info["dist_to_eez_km"],
                "dist_to_coast_buffer_km": gps_info["dist_to_coast_buffer_km"],
                "confidence": gps_info["confidence"],
            }
        )
    logger.info(f"Matched GPS data for {len(catches_with_gps)} catch events.")

    return catches_with_gps


def generate_map(catches_with_gps: list) -> str:  # noqa: PLR0915
    """Generates an interactive map with markers for each catch event and saves it to an HTML file.

    Args:
        catches_with_gps (list): List of dictionaries containing GPS data for each catch event.

    Returns:
        str: The HTML string of the generated map.
    """
    if not catches_with_gps:
        logger.warning(
            "Warning: No GPS data found for catches. Generating empty map with default location."
        )
        map_center = [GPS_DEFAULT_MAP_CENTER_LAT, GPS_DEFAULT_MAP_CENTER_LON]
        m = folium.Map(
            location=map_center,
            zoom_start=GPS_DEFAULT_MAP_ZOOM,
            width="100%",
            height="500px",
            control=True,
        )
    else:
        logger.info("Generating map with catch markers.")
        map_center = [
            sum(d["lat"] for d in catches_with_gps) / len(catches_with_gps),
            sum(d["lon"] for d in catches_with_gps) / len(catches_with_gps),
        ]
        m = folium.Map(
            location=map_center,
            zoom_start=6,
            width="100%",
            height="500px",
            control=True,
        )

    # Add Esri Ocean Basemap tiles (visible only up to zoom level 10)
    folium.TileLayer(
        tiles="Esri.OceanBasemap",
        name="Esri Ocean Basemap",
        overlay=False,
        control=True,
        min_zoom=0,
        max_zoom=10,
        opacity=0.8,
    ).add_to(m)

    # Add EEZ, Coastline and MPA layers
    try:
        with open(EEZ_PATH, encoding="utf-8") as f:
            eez_data = json.load(f)

        folium.GeoJson(
            eez_data,
            name="EEZ",
            style_function=lambda feature: {  # noqa: ARG005
                "fillColor": "green",
                "color": "green",
                "weight": 2,
                "fillOpacity": 0.2,
            },
        ).add_to(m)
        logger.info("Added EEZ layer")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to add EEZ layer")

    try:
        with open(MPA_PATH, encoding="utf-8") as f:
            mpa_data = json.load(f)

        folium.GeoJson(
            mpa_data,
            name="MPA",
            style_function=lambda feature: {  # noqa: ARG005
                "fillColor": "red",
                "color": "red",
                "weight": 2,
                "fillOpacity": 0.2,
            },
        ).add_to(m)
        logger.info("Added MPA layer")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to add MPA layer")

    try:
        with open(COAST_BUFFER_PATH, encoding="utf-8") as f:
            coast_buffer_data = json.load(f)

        folium.GeoJson(
            coast_buffer_data,
            name="Coastline buffer",
            style_function=lambda feature: {  # noqa: ARG005
                "color": "red",
                "weight": 2,
            },
        ).add_to(m)
        logger.info("Added coastline buffer layer")
    except Exception:  # noqa: BLE001
        logger.exception("Failed to add coastline buffer layer")

    folium.LayerControl().add_to(m)

    group_colors = {
        "fish": "#F21564",
        "shark": "#3C5BFF",
        "ray": "#782EF0",
        "turtle": "#00B594",
        "bird": "#F0C1D2",
        "mammal": "#0D1673",
        "other": "#808080",
    }

    # Dictionary to track counts of markers per coordinate.
    if catches_with_gps:
        coord_counts = {}
        for catch in catches_with_gps:
            fish_label = catch["label"]
            fish_info = FISH_MAPPING.get(fish_label, {})
            group = fish_info.get("group", "other")
            html_color = group_colors.get(group)

            custom_icon = BeautifyIcon(
                icon="fish",
                prefix="fa",
                icon_shape="marker",
                background_color=html_color,
                text_color="white",
                border_width=1,
            )

            original_coords = (catch["lat"], catch["lon"])
            lat_offset, lon_offset = catch["lat"], catch["lon"]

            # Check if this coordinate already has one or more markers.
            if original_coords in coord_counts:
                logger.info(f"Overlapping markers at {original_coords}, applying offset.")
                # Apply an offset that increases with the number of overlapping markers.
                offset_multiplier = coord_counts[original_coords]
                offset_value = 0.0001 * offset_multiplier
                lat_offset += offset_value
                lon_offset += offset_value
                coord_counts[original_coords] += 1
            else:
                coord_counts[original_coords] = 1

            if catch["confidence"] == "low":
                logger.info(
                    f"Low confidence for catch at {original_coords}, creating background marker to show uncertainty."
                )
                # Create a faint background CircleMarker for low-confidence points
                folium.CircleMarker(
                    location=[lat_offset, lon_offset],
                    radius=25,
                    stroke=False,
                    fill=True,
                    fill_color=html_color,
                    fill_opacity=0.1,
                ).add_to(m)

            folium.Marker(
                location=[lat_offset, lon_offset],
                popup=folium.Popup(
                    f'<div style="white-space: nowrap;">Catch: {catch["name_en"]} {catch["event_type"]}<br>Catch Time: {catch["estimated_catch_time"].strftime("%d/%b %H:%M")}<br>GPS Time: {catch["gps_time"].strftime("%d/%b %H:%M")}</div>',
                    max_width=300,
                ),
                tooltip=f"{catch['name_en']} {catch['event_type']} catch at {catch['estimated_catch_time'].strftime('%d/%b %H:%M')}",
                icon=custom_icon,
            ).add_to(m)

    legend_html = f"""
    <div style="
        position: absolute;
        top: 10px;
        left: 50px;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.8);
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 5px;
        white-space: nowrap;
        font-size: 12px;">
        <span style="display: inline-block; margin-right: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["fish"]}; margin-right: 5px; border: 1px solid #000;"></span>Fish
        </span>
        <span style="display: inline-block; margin-right: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["shark"]}; margin-right: 5px; border: 1px solid #000;"></span>Shark
        </span>
        <span style="display: inline-block; margin-right: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["ray"]}; margin-right: 5px; border: 1px solid #000;"></span>Ray
        </span>
        <span style="display: inline-block; margin-right: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["turtle"]}; margin-right: 5px; border: 1px solid #000;"></span>Turtle
        </span>
        <span style="display: inline-block; margin-right: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["bird"]}; margin-right: 5px; border: 1px solid #000;"></span>Bird
        </span>
        <span style="display: inline-block; margin-right: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["mammal"]}; margin-right: 5px; border: 1px solid #000;"></span>Mammal
        </span>
        <span style="display: inline-block;">
            <span style="display: inline-block; width: 12px; height: 12px; background-color: {group_colors["other"]}; margin-right: 5px; border: 1px solid #000;"></span>Other
        </span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    logger.info("Generated map with catch markers.")

    return m._repr_html_()  # return the HTML string of the map


def get_gps_risk_features(gps_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate GPS risk features with respect to EEZ, MPA, and coastline buffer.

    Args:
    gps_df (pd.DataFrame): DataFrame containing GPS coordinates with 'lon' and 'lat' columns.

    Returns:
    pd.DataFrame: DataFrame with the following additional columns:
        - 'in_eez': Boolean indicating if the point is within the EEZ.
        - 'outside_mpa': Boolean indicating if the point is outside the MPA.
        - 'outside_coast_buffer': Boolean indicating if the point is outside the coastline buffer.
        - 'dist_to_eez_km': Distance in kilometers from the point to the boundary of the EEZ.
        - 'dist_to_mpa_km': Distance in kilometers from the point to the boundary of the MPA, or 0 if within the MPA.
        - 'dist_to_coast_buffer_km': Distance in kilometers from the point to the coastline buffer.
    """
    gps_gdf = gpd.GeoDataFrame(
        gps_df, geometry=gpd.points_from_xy(gps_df.lon, gps_df.lat), crs="EPSG:4326"
    )

    eez = gpd.read_file(EEZ_PATH)
    mpa = gpd.read_file(MPA_PATH)
    coast_buffer = gpd.read_file(COAST_BUFFER_PATH)

    # Define a projected CRS for distance calculations
    target_crs = "EPSG:32617"

    # Reproject the dataframes to the target CRS
    eez = eez.to_crs(target_crs)
    eez["geometry"] = eez.geometry.buffer(0)  # Fix invalid geometries

    mpa = mpa.to_crs(target_crs)
    coast_buffer = coast_buffer.to_crs(target_crs)
    gps_gdf = gps_gdf.to_crs(target_crs)

    eez_union = eez.geometry.unary_union
    coast_buffer_union = coast_buffer.geometry.unary_union
    mpa_union = mpa.geometry.unary_union

    # Check if each point is within the EEZ zone, outside the MPA zone, and outside the coastline buffer
    gps_df["in_eez"] = gps_gdf.geometry.within(eez_union)
    gps_df["outside_mpa"] = ~gps_gdf.geometry.within(mpa_union)
    gps_df["outside_coast_buffer"] = ~gps_gdf.geometry.within(coast_buffer_union)

    # Calculate distance (in km) from each point to the boundary of each zone
    gps_df["dist_to_eez_km"] = gps_gdf.geometry.apply(
        lambda point: 0
        if point.within(eez_union)
        else point.distance(eez_union.boundary) / 1000
    )
    gps_df["dist_to_mpa_km"] = gps_gdf.geometry.apply(
        lambda point: 0
        if point.within(mpa_union)
        else point.distance(mpa_union.boundary) / 1000
    )
    gps_df["dist_to_coast_buffer_km"] = gps_gdf.geometry.apply(
        lambda point: 0
        if point.within(coast_buffer_union)
        else point.distance(coast_buffer_union.boundary) / 1000
    )
    return gps_df
