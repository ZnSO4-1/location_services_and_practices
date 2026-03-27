from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_POS = BASE_DIR / "data" / "raw" / "gnss" / "lj010617k_kinematic2.1.pos"
OUTPUT_RAW = BASE_DIR / "data" / "processed" / "gps_kinematic_raw.csv"
OUTPUT_Q12 = BASE_DIR / "data" / "processed" / "gps_kinematic_q1q2.csv"


def parse_pos_file(pos_path: Path) -> pd.DataFrame:
    """
    解析 RTKLIB .pos 文件
    输出列：
    time, lat, lon, height, Q, ns, sdn, sde, sdu, sdne, sdeu, sdun, age, ratio
    """
    rows = []

    with open(pos_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            # 跳过空行和注释行
            if not line or line.startswith("%"):
                continue

            parts = line.split()
            if len(parts) < 15:
                continue

            # RTKLIB POS 行格式：
            # 0: date
            # 1: time
            # 2: lat
            # 3: lon
            # 4: height
            # 5: Q
            # 6: ns
            # 7~14: 其他精度信息
            try:
                row = {
                    "time": f"{parts[0]} {parts[1]}",
                    "lat": float(parts[2]),
                    "lon": float(parts[3]),
                    "height": float(parts[4]),
                    "Q": int(parts[5]),
                    "ns": int(parts[6]),
                    "sdn": float(parts[7]),
                    "sde": float(parts[8]),
                    "sdu": float(parts[9]),
                    "sdne": float(parts[10]),
                    "sdeu": float(parts[11]),
                    "sdun": float(parts[12]),
                    "age": float(parts[13]),
                    "ratio": float(parts[14]),
                }
                rows.append(row)
            except ValueError:
                # 遇到格式异常行就跳过
                continue

    if not rows:
        raise ValueError(f"未从文件中解析到有效数据: {pos_path}")

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time", "lat", "lon"]).reset_index(drop=True)
    return df


def main():
    if not INPUT_POS.exists():
        raise FileNotFoundError(f"找不到文件: {INPUT_POS}")

    OUTPUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    df = parse_pos_file(INPUT_POS)

    # 1) 原始输出
    df.to_csv(OUTPUT_RAW, index=False, encoding="utf-8-sig")

    # 2) 只保留 Q=1 和 Q=2
    df_q12 = df[df["Q"].isin([1, 2])].copy()
    df_q12.to_csv(OUTPUT_Q12, index=False, encoding="utf-8-sig")

    print(f"原始动态轨迹已保存: {OUTPUT_RAW}，共 {len(df)} 行")
    print(f"高质量(Q=1/2)轨迹已保存: {OUTPUT_Q12}，共 {len(df_q12)} 行")

    print("\nQ 值统计：")
    print(df["Q"].value_counts().sort_index())

    print("\n前5行：")
    print(df.head())


if __name__ == "__main__":
    main()
