import numpy as np
import pandas as pd


def add_noise_to_csv(input_csv, output_csv, sigma_m, seed=42):
    """给经纬度轨迹添加高斯噪声（单位：米）。"""
    rng = np.random.default_rng(seed)
    df = pd.read_csv(input_csv).copy()

    lat_scale = 111000.0
    mean_lat = df["lat"].mean()
    lon_scale = 111000.0 * np.cos(np.radians(mean_lat))

    df["lat"] = df["lat"] + rng.normal(0, sigma_m / lat_scale, len(df))
    df["lon"] = df["lon"] + rng.normal(0, sigma_m / lon_scale, len(df))

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"saved: {output_csv}")
