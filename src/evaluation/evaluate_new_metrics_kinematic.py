import math
from pathlib import Path
from typing import List, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
RESULT_DIR = BASE_DIR / "experiments" / "kinematic" / "results"
REFERENCE_CASE = RESULT_DIR / "reference_raw" / "trendHMM_reference" / "matched_points.csv"


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_matched_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def get_edge_sequence(df: pd.DataFrame) -> List[Tuple[int, int]]:
    return list(zip(df["edge_u"].tolist(), df["edge_v"].tolist()))


def exact_edge_sequence_ratio(ref_edges: List[Tuple[int, int]], pred_edges: List[Tuple[int, int]]) -> float:
    n = min(len(ref_edges), len(pred_edges))
    if n == 0:
        return 0.0
    same = sum(1 for i in range(n) if ref_edges[i] == pred_edges[i])
    return same / n


def edge_set_overlap_ratio(ref_edges: List[Tuple[int, int]], pred_edges: List[Tuple[int, int]]) -> float:
    ref_set = set(ref_edges)
    pred_set = set(pred_edges)
    if not ref_set:
        return 0.0
    return len(ref_set & pred_set) / len(ref_set)


def is_exact_same_sequence(ref_edges: List[Tuple[int, int]], pred_edges: List[Tuple[int, int]]) -> bool:
    return ref_edges == pred_edges


def mean_matched_point_distance(ref_df: pd.DataFrame, pred_df: pd.DataFrame) -> float:
    n = min(len(ref_df), len(pred_df))
    if n == 0:
        return 0.0

    dists = []
    for i in range(n):
        d = haversine_m(
            ref_df.loc[i, "matched_lat"],
            ref_df.loc[i, "matched_lon"],
            pred_df.loc[i, "matched_lat"],
            pred_df.loc[i, "matched_lon"],
        )
        dists.append(d)
    return sum(dists) / len(dists)


def compare_with_reference(ref_path: Path, pred_path: Path) -> dict:
    # 以 reference_raw/trendHMM_reference 作为统一基准。
    ref_df = load_matched_csv(ref_path)
    pred_df = load_matched_csv(pred_path)

    ref_edges = get_edge_sequence(ref_df)
    pred_edges = get_edge_sequence(pred_df)

    return {
        "exact_edge_sequence_ratio": exact_edge_sequence_ratio(ref_edges, pred_edges),
        "edge_set_overlap_ratio": edge_set_overlap_ratio(ref_edges, pred_edges),
        "mean_matched_point_distance_m": mean_matched_point_distance(ref_df, pred_df),
        "is_exact_same_sequence": is_exact_same_sequence(ref_edges, pred_edges),
        "ref_n": len(ref_df),
        "pred_n": len(pred_df),
    }


def main():
    if not REFERENCE_CASE.exists():
        raise FileNotFoundError(f"未找到参考文件: {REFERENCE_CASE}")

    rows = []

    for case_dir in RESULT_DIR.iterdir():
        if not case_dir.is_dir():
            continue

        if case_dir.name == "reference_raw":
            continue

        for algo_dir in case_dir.iterdir():
            if not algo_dir.is_dir():
                continue

            pred_csv = algo_dir / "matched_points.csv"
            if not pred_csv.exists():
                continue

            metrics = compare_with_reference(REFERENCE_CASE, pred_csv)
            rows.append({
                "case_name": case_dir.name,
                "algorithm": algo_dir.name,
                "matched_csv": str(pred_csv),
                **metrics
            })

    df = pd.DataFrame(rows)

    out_csv = RESULT_DIR / "results_new_metrics.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    pivot_exact = df.pivot_table(
        index="case_name", columns="algorithm", values="exact_edge_sequence_ratio", aggfunc="first"
    )
    pivot_exact.to_csv(RESULT_DIR / "pivot_exact_edge_sequence_ratio.csv", encoding="utf-8-sig")

    pivot_overlap = df.pivot_table(
        index="case_name", columns="algorithm", values="edge_set_overlap_ratio", aggfunc="first"
    )
    pivot_overlap.to_csv(RESULT_DIR / "pivot_edge_set_overlap_ratio.csv", encoding="utf-8-sig")

    pivot_dist = df.pivot_table(
        index="case_name", columns="algorithm", values="mean_matched_point_distance_m", aggfunc="first"
    )
    pivot_dist.to_csv(RESULT_DIR / "pivot_mean_matched_point_distance.csv", encoding="utf-8-sig")

    print("新指标结果已保存：", out_csv)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
