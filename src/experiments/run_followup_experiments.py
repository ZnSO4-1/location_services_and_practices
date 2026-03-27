import math
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.map_matching.hmm_map_matching_local_pbf import run_hmm_map_matching


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_GIOW_TRACK_SUBSET_CSV = BASE_DIR / "data" / "processed" / "gps_giow_window_0s_to_5000s_dt_1p0s.csv"

# 只保留当前仓库仍在维护的两个真实数据实验。
DATASET_CONFIG = {
    "giow_track_subset": {
        "input_csv": DEFAULT_GIOW_TRACK_SUBSET_CSV,
        "data_dir": BASE_DIR / "experiments" / "giow_track_subset" / "data",
        "result_dir": BASE_DIR / "experiments" / "giow_track_subset" / "results",
    },
    "kinematic": {
        "input_csv": BASE_DIR / "data" / "processed" / "gps_kinematic_match.csv",
        "data_dir": BASE_DIR / "experiments" / "kinematic" / "data",
        "result_dir": BASE_DIR / "experiments" / "kinematic" / "results",
    },
}

NOISE_LEVELS_M = [0, 5, 10, 20]
DOWNSAMPLE_STEPS = [1, 2, 3, 5]

TREND_LAMBDA = 1.5
RANDOM_SEED = 42
SAVE_HTML = True

REFERENCE_CASE_NAME = "reference_raw"
REFERENCE_ALGO_NAME = "trendHMM_reference"


def ensure_dirs(data_dir: Path, result_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)


def load_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"lat", "lon"}
    if not required.issubset(df.columns):
        raise ValueError(f"{csv_path} 必须包含列 {required}")
    return df


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def add_noise_to_csv(input_csv: Path, output_csv: Path, sigma_m: float, seed: int) -> None:
    rng = np.random.default_rng(seed)
    df = load_csv(input_csv).copy()

    lat_scale = 111000.0
    mean_lat = df["lat"].mean()
    lon_scale = 111000.0 * math.cos(math.radians(mean_lat))

    df["lat"] = df["lat"] + rng.normal(0, sigma_m / lat_scale, len(df))
    df["lon"] = df["lon"] + rng.normal(0, sigma_m / lon_scale, len(df))

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"已生成噪声数据: {output_csv}")


def downsample_csv(input_csv: Path, output_csv: Path, step: int) -> None:
    df = load_csv(input_csv).copy()
    df = df.iloc[::step].reset_index(drop=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"已生成降采样数据: {output_csv}, 点数={len(df)}")


def prepare_datasets(original_gps_csv: Path, data_dir: Path) -> None:
    # 噪声扰动组
    for sigma in NOISE_LEVELS_M:
        out_csv = data_dir / f"gps_noise_{sigma}m.csv"
        add_noise_to_csv(original_gps_csv, out_csv, sigma_m=sigma, seed=RANDOM_SEED + sigma)

    # 采样间隔组
    for step in DOWNSAMPLE_STEPS:
        out_csv = data_dir / f"gps_step_{step}.csv"
        downsample_csv(original_gps_csv, out_csv, step=step)


def collect_edges(matched_csv_path: Path) -> List[Tuple[int, int]]:
    df = pd.read_csv(matched_csv_path)
    if not {"edge_u", "edge_v"}.issubset(df.columns):
        return []
    return list(zip(df["edge_u"].tolist(), df["edge_v"].tolist()))


def compute_path_length(matched_csv_path: Path) -> float:
    df = pd.read_csv(matched_csv_path)
    if not {"matched_lat", "matched_lon"}.issubset(df.columns):
        return 0.0

    coords = list(zip(df["matched_lat"].tolist(), df["matched_lon"].tolist()))
    if len(coords) < 2:
        return 0.0

    total = 0.0
    for i in range(len(coords) - 1):
        total += haversine_m(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
    return total


def edge_overlap_ratio(ref_edges: List[Tuple[int, int]], pred_edges: List[Tuple[int, int]]) -> float:
    ref_set = set(ref_edges)
    pred_set = set(pred_edges)
    if not ref_set:
        return 0.0
    return len(ref_set & pred_set) / len(ref_set)


def relative_length_error(pred_len: float, ref_len: float) -> float:
    if ref_len == 0:
        return 0.0
    return abs(pred_len - ref_len) / ref_len


def run_one_case(
    case_name: str,
    gps_csv_path: Path,
    algo_name: str,
    use_trend: bool,
    result_dir: Path,
    trend_lambda: float = TREND_LAMBDA,
) -> Dict:
    case_dir = result_dir / case_name / algo_name
    case_dir.mkdir(parents=True, exist_ok=True)

    matched_csv_path = case_dir / "matched_points.csv"
    html_map_path = case_dir / "map_matching_result.html"

    print(f"\n===== 开始实验: {case_name} | {algo_name} =====")

    run_hmm_map_matching(
        gps_csv_path=str(gps_csv_path),
        matched_csv_path=str(matched_csv_path),
        html_map_path=str(html_map_path),
        use_trend=use_trend,
        trend_lambda=trend_lambda,
    )

    if not SAVE_HTML and html_map_path.exists():
        html_map_path.unlink()

    pred_edges = collect_edges(matched_csv_path)
    pred_len = compute_path_length(matched_csv_path)

    return {
        "case_name": case_name,
        "algorithm": algo_name,
        "gps_csv": str(gps_csv_path),
        "matched_csv": str(matched_csv_path),
        "html_map": str(html_map_path) if html_map_path.exists() else "",
        "pred_edge_count": len(pred_edges),
        "pred_path_length_m": pred_len,
        "pred_edges": pred_edges,
    }


def build_reference(original_gps_csv: Path, result_dir: Path) -> Dict:
    return run_one_case(
        case_name=REFERENCE_CASE_NAME,
        gps_csv_path=original_gps_csv,
        algo_name=REFERENCE_ALGO_NAME,
        use_trend=True,
        result_dir=result_dir,
        trend_lambda=TREND_LAMBDA,
    )


def evaluate_against_reference(results: List[Dict], ref_result: Dict) -> pd.DataFrame:
    ref_edges = ref_result["pred_edges"]
    ref_len = ref_result["pred_path_length_m"]

    rows = []
    for r in results:
        overlap = edge_overlap_ratio(ref_edges, r["pred_edges"])
        len_err = relative_length_error(r["pred_path_length_m"], ref_len)

        rows.append({
            "case_name": r["case_name"],
            "algorithm": r["algorithm"],
            "gps_csv": r["gps_csv"],
            "matched_csv": r["matched_csv"],
            "html_map": r["html_map"],
            "pred_edge_count": r["pred_edge_count"],
            "pred_path_length_m": r["pred_path_length_m"],
            "edge_overlap_ratio": overlap,
            "relative_length_error": len_err,
        })

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run map-matching follow-up experiments.")
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASET_CONFIG),
        default="giow_track_subset",
        help="Select which prepared real-world dataset to use.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = DATASET_CONFIG[args.dataset]
    original_gps_csv = config["input_csv"]
    data_dir = config["data_dir"]
    result_dir = config["result_dir"]

    ensure_dirs(data_dir, result_dir)

    if not original_gps_csv.exists():
        raise FileNotFoundError(f"未找到原始 GPS 文件: {original_gps_csv}")

    prepare_datasets(original_gps_csv, data_dir)

    ref_result = build_reference(original_gps_csv, result_dir)
    all_results: List[Dict] = []

    # 原始轨迹
    all_results.append(
        run_one_case(
            case_name="raw",
            gps_csv_path=original_gps_csv,
            algo_name="HMM",
            use_trend=False,
            result_dir=result_dir,
        )
    )
    all_results.append(
        run_one_case(
            case_name="raw",
            gps_csv_path=original_gps_csv,
            algo_name="trendHMM",
            use_trend=True,
            result_dir=result_dir,
            trend_lambda=TREND_LAMBDA,
        )
    )

    # 噪声实验
    for sigma in NOISE_LEVELS_M:
        gps_csv = data_dir / f"gps_noise_{sigma}m.csv"
        case_name = f"noise_{sigma}m"

        all_results.append(
            run_one_case(
                case_name=case_name,
                gps_csv_path=gps_csv,
                algo_name="HMM",
                use_trend=False,
                result_dir=result_dir,
            )
        )
        all_results.append(
            run_one_case(
                case_name=case_name,
                gps_csv_path=gps_csv,
                algo_name="trendHMM",
                use_trend=True,
                result_dir=result_dir,
                trend_lambda=TREND_LAMBDA,
            )
        )

    # 降采样实验
    for step in DOWNSAMPLE_STEPS:
        gps_csv = data_dir / f"gps_step_{step}.csv"
        case_name = f"step_{step}"

        all_results.append(
            run_one_case(
                case_name=case_name,
                gps_csv_path=gps_csv,
                algo_name="HMM",
                use_trend=False,
                result_dir=result_dir,
            )
        )
        all_results.append(
            run_one_case(
                case_name=case_name,
                gps_csv_path=gps_csv,
                algo_name="trendHMM",
                use_trend=True,
                result_dir=result_dir,
                trend_lambda=TREND_LAMBDA,
            )
        )

    summary_df = evaluate_against_reference(all_results, ref_result)

    summary_csv = result_dir / "results_summary.csv"
    summary_df.to_csv(summary_csv, index=False, encoding="utf-8-sig")

    pivot_overlap = summary_df.pivot_table(
        index="case_name", columns="algorithm", values="edge_overlap_ratio", aggfunc="first"
    )
    pivot_overlap.to_csv(result_dir / "pivot_edge_overlap.csv", encoding="utf-8-sig")

    pivot_len_err = summary_df.pivot_table(
        index="case_name", columns="algorithm", values="relative_length_error", aggfunc="first"
    )
    pivot_len_err.to_csv(result_dir / "pivot_length_error.csv", encoding="utf-8-sig")

    print("\n全部实验完成。")
    print(f"结果汇总已保存: {summary_csv}")
    print(summary_df)


if __name__ == "__main__":
    main()
