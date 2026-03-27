import pandas as pd
from pathlib import Path

# 从 RTKLIB 预处理结果中抽出地图匹配真正需要的三列。
BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_CSV = BASE_DIR / "data" / "processed" / "gps_kinematic_q1q2.csv"
OUTPUT_CSV = BASE_DIR / "data" / "processed" / "gps_kinematic_match.csv"


def main() -> None:
    df = pd.read_csv(INPUT_CSV)

    df_match = df[["time", "lat", "lon"]].copy()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_match.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"已生成: {OUTPUT_CSV}，共 {len(df_match)} 行")
    print(df_match.head())


if __name__ == "__main__":
    main()
