import argparse
from pathlib import Path

from src.simulation.jia_gao_si_zao_sheng import add_noise_to_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为轨迹 CSV 添加高斯噪声。")
    parser.add_argument("--input", type=Path, required=True, help="输入 CSV 路径（需含 lat/lon 列）")
    parser.add_argument("--output", type=Path, required=True, help="输出 CSV 路径")
    parser.add_argument("--sigma-m", type=float, default=10.0, help="噪声标准差（米）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    add_noise_to_csv(
        input_csv=str(args.input),
        output_csv=str(args.output),
        sigma_m=float(args.sigma_m),
        seed=int(args.seed),
    )


if __name__ == "__main__":
    main()
