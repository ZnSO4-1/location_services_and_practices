from pathlib import Path

import numpy as np
import pandas as pd


# 生成一段武汉大学附近的示例轨迹，作为流程联调用的模拟输入。
START_LAT = 30.5365
START_LON = 114.3648
END_LAT = 30.5415
END_LON = 114.3690
N_POINTS = 30
NOISE_STD_M = 10
RANDOM_SEED = 42
METERS_PER_DEG = 111000

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "gps_points.csv"


def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)

    lats = np.linspace(START_LAT, END_LAT, N_POINTS)
    lons = np.linspace(START_LON, END_LON, N_POINTS)

    # 简单高斯噪声：纬度和经度按不同尺度折算米制误差。
    noise_lat = rng.normal(0, NOISE_STD_M / METERS_PER_DEG, N_POINTS)
    noise_lon = rng.normal(
        0,
        NOISE_STD_M / (METERS_PER_DEG * np.cos(np.radians(START_LAT))),
        N_POINTS,
    )

    df = pd.DataFrame(
        {
            "lat": lats + noise_lat,
            "lon": lons + noise_lon,
        }
    )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"已生成模拟轨迹: {OUTPUT_CSV} (点数={len(df)})")


if __name__ == "__main__":
    main()
