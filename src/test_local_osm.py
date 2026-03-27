import warnings
from pathlib import Path
import pandas as pd
from pyrosm import OSM

# 关闭 pyrosm + pandas 的链式赋值警告
warnings.filterwarnings("ignore")
pd.options.mode.copy_on_write = False

BASE_DIR = Path(__file__).resolve().parents[1]
OSM_PBF_PATH = BASE_DIR / "data" / "raw" / "osm" / "hubei-260315.osm.pbf"

osm = OSM(str(OSM_PBF_PATH))

# 关键：加 nodes=True
result = osm.get_network(network_type="driving", nodes=True)

print("返回对象类型:", type(result))
print("返回长度:", len(result))

# 不同 pyrosm 版本有时返回顺序不同，这里做兼容判断
a, b = result

# 一般 edges 的 geometry 是 LineString，nodes 的 geometry 是 Point
if a.geometry.iloc[0].geom_type == "Point":
    nodes, edges = a, b
else:
    edges, nodes = a, b

print("全部 nodes:", len(nodes))
print("全部 edges:", len(edges))
print("nodes 列名:", list(nodes.columns))
print("edges 列名:", list(edges.columns))

# 武汉大学附近范围
north = 30.56
south = 30.52
east = 114.39
west = 114.34

# 兼容不同列名
lat_col = "lat" if "lat" in nodes.columns else "y"
lon_col = "lon" if "lon" in nodes.columns else "x"

nodes_clip = nodes[
    (nodes[lat_col] <= north) &
    (nodes[lat_col] >= south) &
    (nodes[lon_col] <= east) &
    (nodes[lon_col] >= west)
].copy()

# 兼容不同 id 列名
node_id_col = "id" if "id" in nodes_clip.columns else nodes_clip.columns[0]

edges_clip = edges[
    edges["u"].isin(nodes_clip[node_id_col]) &
    edges["v"].isin(nodes_clip[node_id_col])
].copy()

print("裁剪后 nodes:", len(nodes_clip))
print("裁剪后 edges:", len(edges_clip))
