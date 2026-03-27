import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_CSV = BASE_DIR / "data" / "processed" / "gps_giow_match.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

DEFAULT_WINDOW_SECONDS = 300
DEFAULT_TIME_STEP_SECONDS = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare smaller, contiguous GIOW subsets for map-matching experiments."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_CSV,
        help="Input full GIOW csv path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for generated subset csv files.",
    )
    parser.add_argument(
        "--start-seconds",
        type=float,
        default=0.0,
        help="Offset from the beginning of the full trajectory, in seconds.",
    )
    parser.add_argument(
        "--window-seconds",
        type=float,
        default=DEFAULT_WINDOW_SECONDS,
        help="Length of the contiguous time window to keep, in seconds.",
    )
    parser.add_argument(
        "--time-step-seconds",
        type=float,
        default=DEFAULT_TIME_STEP_SECONDS,
        help="Keep roughly one point every N seconds inside the window.",
    )
    parser.add_argument(
        "--row-step",
        type=int,
        default=0,
        help="Optional extra row-based downsampling after the time filter. 0 disables it.",
    )
    return parser.parse_args()


def crop_time_window(df: pd.DataFrame, start_seconds: float, window_seconds: float) -> pd.DataFrame:
    if "time" not in df.columns:
        raise ValueError("输入 CSV 缺少 time 列，无法按连续时间窗口裁剪。")

    start_time = float(df["time"].iloc[0]) + start_seconds
    end_time = start_time + window_seconds
    subset = df[(df["time"] >= start_time) & (df["time"] < end_time)].copy()
    return subset.reset_index(drop=True)


def downsample_by_time(df: pd.DataFrame, time_step_seconds: float) -> pd.DataFrame:
    if time_step_seconds <= 0:
        raise ValueError("time_step_seconds 必须大于 0。")

    kept_rows = []
    next_time = None

    for row in df.itertuples(index=False):
        row_time = float(row.time)
        if next_time is None or row_time >= next_time:
            kept_rows.append(row)
            next_time = row_time + time_step_seconds

    return pd.DataFrame(kept_rows, columns=df.columns)


def build_output_name(start_seconds: float, window_seconds: float, time_step_seconds: float, row_step: int) -> str:
    name = (
        f"gps_giow_window_{int(start_seconds)}s_to_{int(start_seconds + window_seconds)}s"
        f"_dt_{str(time_step_seconds).replace('.', 'p')}s"
    )
    if row_step and row_step > 1:
        name += f"_rowstep_{row_step}"
    return name + ".csv"


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    window_df = crop_time_window(df, args.start_seconds, args.window_seconds)
    if window_df.empty:
        raise ValueError("裁剪结果为空，请调整 start-seconds 或 window-seconds。")

    sampled_df = downsample_by_time(window_df, args.time_step_seconds)
    if args.row_step and args.row_step > 1:
        sampled_df = sampled_df.iloc[::args.row_step].reset_index(drop=True)

    output_name = build_output_name(
        start_seconds=args.start_seconds,
        window_seconds=args.window_seconds,
        time_step_seconds=args.time_step_seconds,
        row_step=args.row_step,
    )
    output_path = args.output_dir / output_name
    sampled_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("已生成连续时间窗口子集：")
    print(f"输入文件: {args.input}")
    print(f"输出文件: {output_path}")
    print(f"原始点数: {len(df)}")
    print(f"窗口点数: {len(window_df)}")
    print(f"输出点数: {len(sampled_df)}")
    print(f"起始偏移: {args.start_seconds:.1f} s")
    print(f"窗口时长: {args.window_seconds:.1f} s")
    print(f"时间降采样间隔: {args.time_step_seconds:.3f} s")
    print(f"额外行步长: {args.row_step}")


if __name__ == "__main__":
    main()
