import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point, LineString
import folium
from pyrosm import OSM

warnings.filterwarnings("ignore")
pd.options.mode.copy_on_write = False

# -----------------------------
# 参数配置
# -----------------------------
GPS_SIGMA = 20.0
TRANS_BETA = 50.0
CANDIDATES_K = 5
MAX_ROUTE_DIST_M = 5000.0
MAP_ZOOM_START = 15

OSM_PBF_FILE = "hubei-260315.osm.pbf"
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OSM_PBF_FILE = BASE_DIR / "data" / "raw" / "osm" / OSM_PBF_FILE

# 武汉大学附近范围
NORTH = 30.56
SOUTH = 30.52
EAST = 114.39
WEST = 114.34

USE_TREND = True
TREND_LAMBDA = 1.5          # 趋势项权重，可调
TREND_SIGMA_DEG = 30.0      # 方向差容忍度（度）


@dataclass
class Candidate:
    obs_idx: int
    edge_u: int
    edge_v: int
    edge_key: int
    edge_id: Tuple[int, int, int]
    snapped_point_proj: Point
    snapped_point_wgs84: Point
    distance_to_gps_m: float
    line_proj: LineString
    line_length_m: float
    proj_dist_along_line_m: float
    start_node_geom_proj: Point
    end_node_geom_proj: Point
    start_node_geom_wgs84: Point
    end_node_geom_wgs84: Point


def gaussian_logpdf(x: float, sigma: float) -> float:
    return -0.5 * (x / sigma) ** 2 - math.log(sigma * math.sqrt(2 * math.pi))


def exponential_logpdf(x: float, beta: float) -> float:
    x = max(0.0, x)
    return -x / beta - math.log(beta)


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_gps_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"lat", "lon"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV必须至少包含列: {required}")
    df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    if len(df) < 2:
        raise ValueError("GPS点数量至少需要2个。")
    return df


def load_local_road_network(osm_pbf_file: str):
    print("正在从本地 PBF 读取道路网络...")
    osm_pbf_path = Path(osm_pbf_file)
    if not osm_pbf_path.exists():
        raise FileNotFoundError(f"未找到本地路网文件: {osm_pbf_path}")
    osm = OSM(str(osm_pbf_path))

    result = osm.get_network(network_type="driving", nodes=True)
    a, b = result

    if a.geometry.iloc[0].geom_type == "Point":
        nodes, edges = a, b
    else:
        edges, nodes = a, b

    print(f"全部 nodes: {len(nodes)}")
    print(f"全部 edges: {len(edges)}")

    # 裁剪武汉大学附近范围
    nodes_clip = nodes[
        (nodes["lat"] <= NORTH) &
        (nodes["lat"] >= SOUTH) &
        (nodes["lon"] <= EAST) &
        (nodes["lon"] >= WEST)
    ].copy()

    edges_clip = edges[
        edges["u"].isin(nodes_clip["id"]) &
        edges["v"].isin(nodes_clip["id"])
    ].copy()

    print(f"裁剪后 nodes: {len(nodes_clip)}")
    print(f"裁剪后 edges: {len(edges_clip)}")

    if len(nodes_clip) == 0 or len(edges_clip) == 0:
        raise RuntimeError("裁剪后的本地路网为空，请扩大范围。")

    # 设置坐标系
    if nodes_clip.crs is None:
        nodes_clip = nodes_clip.set_crs(epsg=4326)
    if edges_clip.crs is None:
        edges_clip = edges_clip.set_crs(epsg=4326)

    # 投影到米制坐标
    utm_crs = nodes_clip.estimate_utm_crs()
    nodes_proj = nodes_clip.to_crs(utm_crs)
    edges_proj = edges_clip.to_crs(utm_crs)

    nodes_wgs = nodes_clip.to_crs(epsg=4326)
    edges_wgs = edges_clip.to_crs(epsg=4326)

    # 构图
    G = nx.DiGraph()

    for _, row in nodes_proj.iterrows():
        node_id = row["id"]
        geom = row.geometry
        G.add_node(node_id, x=geom.x, y=geom.y)

    for _, row in edges_proj.iterrows():
        u = row["u"]
        v = row["v"]
        length = float(row["length"]) if "length" in row and pd.notna(row["length"]) else row.geometry.length
        G.add_edge(u, v, length=length)

    print(f"图构建成功: graph_nodes={G.number_of_nodes()}, graph_edges={G.number_of_edges()}")

    # 构造 MultiIndex，兼容后续候选边处理
    edges_proj = edges_proj.copy()
    edges_wgs = edges_wgs.copy()
    edges_proj["key"] = 0
    edges_wgs["key"] = 0
    edges_proj = edges_proj.set_index(["u", "v", "key"])
    edges_wgs = edges_wgs.set_index(["u", "v", "key"])

    nodes_proj = nodes_proj.set_index("id", drop=False)
    nodes_wgs = nodes_wgs.set_index("id", drop=False)

    return G, nodes_proj, edges_proj, nodes_wgs, edges_wgs


def gps_points_to_gdf(gps_df: pd.DataFrame, target_crs):
    gdf_wgs = gpd.GeoDataFrame(
        gps_df.copy(),
        geometry=gpd.points_from_xy(gps_df["lon"], gps_df["lat"]),
        crs="EPSG:4326"
    )
    gdf_proj = gdf_wgs.to_crs(target_crs)
    return gdf_wgs, gdf_proj


def build_candidates_for_point(
    point_proj: Point,
    obs_idx: int,
    edges_proj: gpd.GeoDataFrame,
    nodes_proj: gpd.GeoDataFrame,
    nodes_wgs: gpd.GeoDataFrame,
    k: int = CANDIDATES_K
) -> List[Candidate]:
    edges_tmp = edges_proj.copy()
    edges_tmp["dist_to_gps"] = edges_tmp.geometry.distance(point_proj)
    nearest = edges_tmp.nsmallest(k, "dist_to_gps")

    candidates = []
    for edge_idx, row in nearest.iterrows():
        u, v, key = edge_idx
        line_proj = row.geometry
        dist_m = float(row["dist_to_gps"])

        if line_proj is None or line_proj.is_empty:
            continue

        s = line_proj.project(point_proj)
        snapped_proj = line_proj.interpolate(s)
        snapped_wgs = gpd.GeoSeries([snapped_proj], crs=edges_proj.crs).to_crs(epsg=4326).iloc[0]

        start_proj = nodes_proj.loc[u].geometry
        end_proj = nodes_proj.loc[v].geometry
        start_wgs = nodes_wgs.loc[u].geometry
        end_wgs = nodes_wgs.loc[v].geometry

        candidates.append(
            Candidate(
                obs_idx=obs_idx,
                edge_u=u,
                edge_v=v,
                edge_key=key,
                edge_id=(u, v, key),
                snapped_point_proj=snapped_proj,
                snapped_point_wgs84=snapped_wgs,
                distance_to_gps_m=dist_m,
                line_proj=line_proj,
                line_length_m=float(line_proj.length),
                proj_dist_along_line_m=float(s),
                start_node_geom_proj=start_proj,
                end_node_geom_proj=end_proj,
                start_node_geom_wgs84=start_wgs,
                end_node_geom_wgs84=end_wgs,
            )
        )

    return candidates


def build_all_candidates(gps_gdf_proj, edges_proj, nodes_proj, nodes_wgs, k=CANDIDATES_K):
    all_candidates = []
    for i in range(len(gps_gdf_proj)):
        point_proj = gps_gdf_proj.geometry.iloc[i]
        cands = build_candidates_for_point(
            point_proj=point_proj,
            obs_idx=i,
            edges_proj=edges_proj,
            nodes_proj=nodes_proj,
            nodes_wgs=nodes_wgs,
            k=k
        )
        if len(cands) == 0:
            raise RuntimeError(f"第 {i} 个GPS点未找到候选道路。")
        all_candidates.append(cands)
    return all_candidates


def shortest_path_length_safe(G, source: int, target: int) -> float:
    if source == target:
        return 0.0
    try:
        return float(nx.shortest_path_length(G, source=source, target=target, weight="length"))
    except Exception:
        return float("inf")


def route_distance_between_candidates(G, c1: Candidate, c2: Candidate) -> float:
    c1_to_start = c1.proj_dist_along_line_m
    c1_to_end = c1.line_length_m - c1.proj_dist_along_line_m

    c2_from_start = c2.proj_dist_along_line_m
    c2_from_end = c2.line_length_m - c2.proj_dist_along_line_m

    options = []

    d_ss = shortest_path_length_safe(G, c1.edge_u, c2.edge_u)
    options.append(c1_to_start + d_ss + c2_from_start)

    d_se = shortest_path_length_safe(G, c1.edge_u, c2.edge_v)
    options.append(c1_to_start + d_se + c2_from_end)

    d_es = shortest_path_length_safe(G, c1.edge_v, c2.edge_u)
    options.append(c1_to_end + d_es + c2_from_start)

    d_ee = shortest_path_length_safe(G, c1.edge_v, c2.edge_v)
    options.append(c1_to_end + d_ee + c2_from_end)

    return min(options)


def transition_log_prob(G, prev_cand, curr_cand, prev_gps_latlon, curr_gps_latlon, beta=TRANS_BETA):
    route_dist = route_distance_between_candidates(G, prev_cand, curr_cand)
    if not np.isfinite(route_dist) or route_dist > MAX_ROUTE_DIST_M:
        return -1e15

    gps_dist = haversine_m(
        prev_gps_latlon[0], prev_gps_latlon[1],
        curr_gps_latlon[0], curr_gps_latlon[1]
    )
    diff = abs(route_dist - gps_dist)
    return exponential_logpdf(diff, beta)


def bearing_from_points(p1: Point, p2: Point) -> float:
    """
    在投影坐标系下计算两点方向角（弧度）
    """
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.atan2(dy, dx)


def angle_diff_rad(a: float, b: float) -> float:
    """
    方向角差值，返回 [0, pi]
    """
    d = abs(a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)

def get_trend_bearing(gps_gdf_proj, t: int) -> Optional[float]:
    """
    用 g(t-1), g(t), g(t+1) 估计局部趋势方向
    边界处退化为相邻两点
    """
    n = len(gps_gdf_proj)

    if n < 2:
        return None

    if t == 0:
        p1 = gps_gdf_proj.geometry.iloc[0]
        p2 = gps_gdf_proj.geometry.iloc[1]
        return bearing_from_points(p1, p2)

    if t == n - 1:
        p1 = gps_gdf_proj.geometry.iloc[n - 2]
        p2 = gps_gdf_proj.geometry.iloc[n - 1]
        return bearing_from_points(p1, p2)

    p_prev = gps_gdf_proj.geometry.iloc[t - 1]
    p_next = gps_gdf_proj.geometry.iloc[t + 1]
    return bearing_from_points(p_prev, p_next)

def get_candidate_bearing(cand: Candidate) -> Optional[float]:
    """
    在候选道路上，以投影点附近的局部线段方向作为道路方向
    """
    line = cand.line_proj
    s = cand.proj_dist_along_line_m

    if line.length < 1e-6:
        return None

    eps = min(5.0, line.length / 10.0)
    s1 = max(0.0, s - eps)
    s2 = min(line.length, s + eps)

    p1 = line.interpolate(s1)
    p2 = line.interpolate(s2)

    if p1.equals(p2):
        return None

    return bearing_from_points(p1, p2)

def trend_log_prob(gps_gdf_proj, t: int, cand: Candidate, sigma_deg: float = TREND_SIGMA_DEG) -> float:
    """
    趋势项：轨迹局部方向 与 候选道路局部方向 越一致，概率越大
    """
    trend_bearing = get_trend_bearing(gps_gdf_proj, t)
    cand_bearing = get_candidate_bearing(cand)

    if trend_bearing is None or cand_bearing is None:
        return 0.0

    dtheta = angle_diff_rad(trend_bearing, cand_bearing)
    sigma = math.radians(sigma_deg)

    # 高斯型方向一致性
    return -0.5 * (dtheta / sigma) ** 2

def viterbi_match(
    G,
    gps_df: pd.DataFrame,
    gps_gdf_proj,
    all_candidates,
    gps_sigma=GPS_SIGMA,
    trans_beta=TRANS_BETA,
    use_trend=USE_TREND,
    trend_lambda=TREND_LAMBDA
):
    n = len(all_candidates)
    dp = []
    parent = []

    # 初始化
    first_scores = []
    first_parent = []
    for c in all_candidates[0]:
        obs_logp = gaussian_logpdf(c.distance_to_gps_m, gps_sigma)
        trend_logp = trend_log_prob(gps_gdf_proj, 0, c) if use_trend else 0.0
        first_scores.append(obs_logp + trend_lambda * trend_logp)
        first_parent.append(None)
    dp.append(first_scores)
    parent.append(first_parent)

    # 递推
    for t in range(1, n):
        curr_scores = []
        curr_parent = []

        prev_latlon = (gps_df.loc[t - 1, "lat"], gps_df.loc[t - 1, "lon"])
        curr_latlon = (gps_df.loc[t, "lat"], gps_df.loc[t, "lon"])

        for j, curr_c in enumerate(all_candidates[t]):
            obs_logp = gaussian_logpdf(curr_c.distance_to_gps_m, gps_sigma)
            trend_logp = trend_log_prob(gps_gdf_proj, t, curr_c) if use_trend else 0.0

            best_score = -1e18
            best_parent_idx = None

            for i, prev_c in enumerate(all_candidates[t - 1]):
                trans_logp = transition_log_prob(
                    G, prev_c, curr_c, prev_latlon, curr_latlon, beta=trans_beta
                )

                score = dp[t - 1][i] + trans_logp + obs_logp + trend_lambda * trend_logp

                if score > best_score:
                    best_score = score
                    best_parent_idx = i

            curr_scores.append(best_score)
            curr_parent.append(best_parent_idx)

        dp.append(curr_scores)
        parent.append(curr_parent)

    # 回溯
    last_idx = int(np.argmax(dp[-1]))
    best_path_indices = [last_idx]

    for t in range(n - 1, 0, -1):
        last_idx = parent[t][last_idx]
        best_path_indices.append(last_idx)

    best_path_indices.reverse()
    return [all_candidates[t][best_path_indices[t]] for t in range(n)]


def best_route_nodes_between_candidates(G, c1: Candidate, c2: Candidate) -> List[int]:
    c1_to_start = c1.proj_dist_along_line_m
    c1_to_end = c1.line_length_m - c1.proj_dist_along_line_m
    c2_from_start = c2.proj_dist_along_line_m
    c2_from_end = c2.line_length_m - c2.proj_dist_along_line_m

    combos = [
        (c1.edge_u, c2.edge_u, c1_to_start, c2_from_start),
        (c1.edge_u, c2.edge_v, c1_to_start, c2_from_end),
        (c1.edge_v, c2.edge_u, c1_to_end, c2_from_start),
        (c1.edge_v, c2.edge_v, c1_to_end, c2_from_end),
    ]

    best_total = float("inf")
    best_nodes = []

    for s, t, d1, d2 in combos:
        try:
            route = nx.shortest_path(G, source=s, target=t, weight="length")
            route_len = nx.shortest_path_length(G, source=s, target=t, weight="length")
            total = d1 + route_len + d2
            if total < best_total:
                best_total = total
                best_nodes = route
        except Exception:
            continue

    return best_nodes


def save_matched_points_csv(matched_candidates: List[Candidate], output_csv: str):
    rows = []
    for i, c in enumerate(matched_candidates):
        rows.append({
            "obs_idx": i,
            "matched_lat": c.snapped_point_wgs84.y,
            "matched_lon": c.snapped_point_wgs84.x,
            "edge_u": c.edge_u,
            "edge_v": c.edge_v,
            "edge_key": c.edge_key,
            "gps_to_road_distance_m": c.distance_to_gps_m
        })
    pd.DataFrame(rows).to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"已保存匹配点结果: {output_csv}")


def build_route_latlon_sequence(G, matched_candidates: List[Candidate], nodes_proj) -> List[Tuple[float, float]]:
    coords = []
    first = matched_candidates[0]
    coords.append((first.snapped_point_wgs84.y, first.snapped_point_wgs84.x))

    node_crs = nodes_proj.crs

    for i in range(len(matched_candidates) - 1):
        c1 = matched_candidates[i]
        c2 = matched_candidates[i + 1]
        route_nodes = best_route_nodes_between_candidates(G, c1, c2)

        if route_nodes:
            for node in route_nodes:
                pt_proj = nodes_proj.loc[node].geometry
                pt_wgs = gpd.GeoSeries([pt_proj], crs=node_crs).to_crs(epsg=4326).iloc[0]
                latlon = (pt_wgs.y, pt_wgs.x)
                if not coords or coords[-1] != latlon:
                    coords.append(latlon)

        latlon2 = (c2.snapped_point_wgs84.y, c2.snapped_point_wgs84.x)
        if not coords or coords[-1] != latlon2:
            coords.append(latlon2)

    return coords


def save_interactive_map(gps_df, matched_candidates, route_latlon, html_path: str):
    center_lat = gps_df["lat"].mean()
    center_lon = gps_df["lon"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=MAP_ZOOM_START, control_scale=True)

    raw_coords = list(zip(gps_df["lat"], gps_df["lon"]))
    folium.PolyLine(raw_coords, color="red", weight=4, opacity=0.8, tooltip="原始GPS轨迹").add_to(m)

    for i, (lat, lon) in enumerate(raw_coords):
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color="red",
            fill=True,
            fill_opacity=0.9,
            popup=f"原始点 {i}"
        ).add_to(m)

    matched_coords = [(c.snapped_point_wgs84.y, c.snapped_point_wgs84.x) for c in matched_candidates]
    folium.PolyLine(matched_coords, color="blue", weight=4, opacity=0.8, tooltip="匹配点连线").add_to(m)

    for i, c in enumerate(matched_candidates):
        folium.CircleMarker(
            location=[c.snapped_point_wgs84.y, c.snapped_point_wgs84.x],
            radius=4,
            color="blue",
            fill=True,
            fill_opacity=0.9,
            popup=f"匹配点 {i}<br>GPS到道路距离: {c.distance_to_gps_m:.2f} m"
        ).add_to(m)

    if route_latlon and len(route_latlon) >= 2:
        folium.PolyLine(route_latlon, color="green", weight=5, opacity=0.7, tooltip="HMM恢复路径").add_to(m)

    folium.LayerControl().add_to(m)
    m.save(html_path)
    print(f"已保存交互式地图: {html_path}")


def run_hmm_map_matching(
    gps_csv_path: str,
    matched_csv_path: str = "matched_points.csv",
    html_map_path: str = "map_matching_result.html",
    osm_pbf_path: str = str(DEFAULT_OSM_PBF_FILE),
    use_trend: bool = True,
    trend_lambda: float = 1.5
):
    gps_df = load_gps_csv(gps_csv_path)
    print(f"GPS点数量: {len(gps_df)}")

    matched_csv_path = str(Path(matched_csv_path))
    html_map_path = str(Path(html_map_path))
    Path(matched_csv_path).parent.mkdir(parents=True, exist_ok=True)
    Path(html_map_path).parent.mkdir(parents=True, exist_ok=True)

    G, nodes_proj, edges_proj, nodes_wgs, edges_wgs = load_local_road_network(osm_pbf_path)

    gps_gdf_wgs, gps_gdf_proj = gps_points_to_gdf(gps_df, nodes_proj.crs)

    print("正在生成候选道路...")
    all_candidates = build_all_candidates(
        gps_gdf_proj=gps_gdf_proj,
        edges_proj=edges_proj,
        nodes_proj=nodes_proj,
        nodes_wgs=nodes_wgs,
        k=CANDIDATES_K
    )

    print(f"正在执行 {'trendHMM' if use_trend else 'HMM'} 地图匹配...")
    matched_candidates = viterbi_match(
        G=G,
        gps_df=gps_df,
        gps_gdf_proj=gps_gdf_proj,
        all_candidates=all_candidates,
        gps_sigma=GPS_SIGMA,
        trans_beta=TRANS_BETA,
        use_trend=use_trend,
        trend_lambda=trend_lambda
    )

    save_matched_points_csv(matched_candidates, matched_csv_path)

    print("正在恢复匹配路径...")
    route_latlon = build_route_latlon_sequence(G, matched_candidates, nodes_proj)

    save_interactive_map(
        gps_df=gps_df,
        matched_candidates=matched_candidates,
        route_latlon=route_latlon,
        html_path=html_map_path
    )

    print("地图匹配完成。")


if __name__ == "__main__":
    run_hmm_map_matching(
        gps_csv_path=str(BASE_DIR / "data" / "processed" / "gps_points.csv"),
        matched_csv_path=str(BASE_DIR / "results" / "matched_points.csv"),
        html_map_path=str(BASE_DIR / "results" / "map_matching_result.html"),
        use_trend=True,
        trend_lambda=1.5
    )
