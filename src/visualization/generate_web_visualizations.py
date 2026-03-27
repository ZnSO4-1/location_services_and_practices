from __future__ import annotations

import os
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
# 网页已经迁到 docs，这里直接输出到 docs/images，方便 GitHub Pages 引用。
WEB_IMAGE_DIR = BASE_DIR / "docs" / "images"
TMP_DIR = BASE_DIR / "tmp_visualization"

OSM_PBF = DATA_DIR / "raw" / "osm" / "hubei-260315.osm.pbf"
SIM_CSV = DATA_DIR / "processed" / "gps_points.csv"
KINEMATIC_CSV = DATA_DIR / "processed" / "gps_kinematic_match.csv"
GIOW_CSV = DATA_DIR / "processed" / "gps_giow_match.csv"

ROAD_NETWORK_PNG = WEB_IMAGE_DIR / "road_network_overview.png"
SIM_PNG = WEB_IMAGE_DIR / "overlay_simulated.png"
KINEMATIC_PNG = WEB_IMAGE_DIR / "overlay_kinematic.png"
GIOW_PNG = WEB_IMAGE_DIR / "overlay_giow.png"

BBOX = (114.34, 30.52, 114.39, 30.56)


def ensure_dirs() -> None:
    WEB_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def extract_road_network() -> gpd.GeoDataFrame:
    lines_geojson = TMP_DIR / "road_lines.geojson"
    if lines_geojson.exists():
        lines_geojson.unlink()

    min_lon, min_lat, max_lon, max_lat = BBOX
    cmd = [
        "ogr2ogr",
        "-f",
        "GeoJSON",
        str(lines_geojson),
        str(OSM_PBF),
        "lines",
        "-spat",
        str(min_lon),
        str(min_lat),
        str(max_lon),
        str(max_lat),
        "-where",
        "highway IS NOT NULL",
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    roads = gpd.read_file(lines_geojson)
    roads = roads[roads.geometry.notna()].copy()
    roads = roads[~roads.geometry.is_empty].copy()
    return roads


def load_track(csv_path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(csv_path)
    return gpd.GeoDataFrame(
        df.copy(),
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
    )


def setup_axes(title: str):
    fig, ax = plt.subplots(figsize=(9, 7), dpi=160)
    fig.patch.set_facecolor("#f8fbff")
    ax.set_facecolor("#ffffff")
    ax.set_title(title, fontsize=18, weight="bold", pad=14, color="#1f2937")
    ax.tick_params(labelsize=10, colors="#64748b")
    for spine in ax.spines.values():
        spine.set_color("#d9e2f1")
        spine.set_linewidth(1.2)
    ax.grid(True, color="#e5e7eb", linewidth=0.8, alpha=0.7)
    return fig, ax


def save_figure(fig, output_path: Path) -> None:
    fig.tight_layout()
    fig.savefig(output_path, format="png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_road_network(roads: gpd.GeoDataFrame) -> None:
    fig, ax = setup_axes("Local Road Network near Wuhan University")
    roads.plot(ax=ax, color="#94a3b8", linewidth=0.8, alpha=0.9)
    ax.set_xlabel("Longitude", fontsize=11, color="#475569")
    ax.set_ylabel("Latitude", fontsize=11, color="#475569")
    save_figure(fig, ROAD_NETWORK_PNG)


def draw_overlay(
    roads: gpd.GeoDataFrame,
    track: gpd.GeoDataFrame,
    output_path: Path,
    title: str,
    line_color: str,
    point_color: str,
    road_color: str = "#cbd5e1",
    road_linewidth: float = 1.0,
    road_alpha: float = 0.8,
    track_linewidth: float = 2.2,
    point_size: float = 16,
) -> None:
    fig, ax = setup_axes(title)
    roads.plot(ax=ax, color=road_color, linewidth=road_linewidth, alpha=road_alpha, zorder=1)

    ax.plot(track["lon"], track["lat"], color=line_color, linewidth=track_linewidth, zorder=3)
    ax.scatter(track["lon"], track["lat"], s=point_size, color=point_color, alpha=0.92, edgecolor="white", linewidth=0.45, zorder=4)

    pad_x = (track["lon"].max() - track["lon"].min()) * 0.25 or 0.001
    pad_y = (track["lat"].max() - track["lat"].min()) * 0.25 or 0.001
    ax.set_xlim(track["lon"].min() - pad_x, track["lon"].max() + pad_x)
    ax.set_ylim(track["lat"].min() - pad_y, track["lat"].max() + pad_y)
    ax.set_xlabel("Longitude", fontsize=11, color="#475569")
    ax.set_ylabel("Latitude", fontsize=11, color="#475569")
    ax.set_aspect("equal", adjustable="box")
    save_figure(fig, output_path)


def main() -> None:
    ensure_dirs()
    roads = extract_road_network()
    sim_track = load_track(SIM_CSV)
    kinematic_track = load_track(KINEMATIC_CSV)
    giow_track = load_track(GIOW_CSV)

    draw_road_network(roads)
    draw_overlay(
        roads,
        sim_track,
        SIM_PNG,
        "Simulated Trajectory over Local Road Network",
        line_color="#ef4444",
        point_color="#2563eb",
    )
    draw_overlay(
        roads,
        kinematic_track,
        KINEMATIC_PNG,
        "Kinematic Trajectory over Local Road Network",
        line_color="#2563eb",
        point_color="#0f766e",
    )
    draw_overlay(
        roads,
        giow_track,
        GIOW_PNG,
        "GIOW Full Trajectory over Local Road Network",
        line_color="#c1121f",
        point_color="#1d4ed8",
        road_color="#64748b",
        road_linewidth=1.25,
        road_alpha=0.92,
        track_linewidth=2.9,
        point_size=18,
    )

    print(f"saved: {ROAD_NETWORK_PNG}")
    print(f"saved: {SIM_PNG}")
    print(f"saved: {KINEMATIC_PNG}")
    print(f"saved: {GIOW_PNG}")


if __name__ == "__main__":
    main()
