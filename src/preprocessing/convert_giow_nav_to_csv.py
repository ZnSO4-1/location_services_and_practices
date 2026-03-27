from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_NAV = BASE_DIR / "data" / "raw" / "giow" / "reference_result.nav"
OUTPUT_RAW = BASE_DIR / "data" / "processed" / "gps_giow_raw.csv"
OUTPUT_MATCH = BASE_DIR / "data" / "processed" / "gps_giow_match.csv"


def load_nav_fixed_columns(nav_path: Path) -> pd.DataFrame:
    """
    按固定列解析 reference_result.nav

    根据当前文件内容，列顺序可按如下理解：
    0: flag / type
    1: sow
    2: latitude
    3: longitude
    4: height
    5: v_n / 或其他量
    6: v_e / 或其他量
    7: v_u / 或其他量
    8: roll / 或其他量
    9: pitch / 或其他量
    10: yaw / 或其他量
    """
    rows = []

    with open(nav_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 11:
                continue

            try:
                row = {
                    "flag": int(float(parts[0])),
                    "sow": float(parts[1]),
                    "lat": float(parts[2]),
                    "lon": float(parts[3]),
                    "height": float(parts[4]),
                    "v1": float(parts[5]),
                    "v2": float(parts[6]),
                    "v3": float(parts[7]),
                    "a1": float(parts[8]),
                    "a2": float(parts[9]),
                    "a3": float(parts[10]),
                }
                rows.append(row)
            except ValueError:
                continue

    if not rows:
        raise ValueError(f"未从文件中解析到有效数据: {nav_path}")

    df = pd.DataFrame(rows)
    return df


def main():
    if not INPUT_NAV.exists():
        raise FileNotFoundError(f"找不到文件: {INPUT_NAV}")

    OUTPUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    df = load_nav_fixed_columns(INPUT_NAV)

    # 1) 保留一份完整解析结果，便于后续排查或复算
    df.to_csv(OUTPUT_RAW, index=False, encoding="utf-8-sig")

    # 2) 地图匹配输入只保留 time/lat/lon 三列
    df_match = df[["sow", "lat", "lon"]].copy()
    df_match = df_match.rename(columns={"sow": "time"})
    df_match = df_match.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    df_match.to_csv(OUTPUT_MATCH, index=False, encoding="utf-8-sig")

    print(f"已保存原始解析结果: {OUTPUT_RAW}，共 {len(df)} 行")
    print(f"已保存地图匹配输入: {OUTPUT_MATCH}，共 {len(df_match)} 行")

    print("\n前5行：")
    print(df_match.head())

    print("\n统计信息：")
    print(df_match[["lat", "lon"]].describe())


if __name__ == "__main__":
    main()
