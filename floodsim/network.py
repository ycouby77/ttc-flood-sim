"""Road network around a route, from OpenStreetMap (cached on disk)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox


def drive_graph_around(stops: gpd.GeoDataFrame, buffer_m: float = 1000, cache_dir: str | Path = "data/osm") -> nx.MultiDiGraph:
    """Directed drivable street network covering the stops plus a detour margin.

    Only downloads the corridor the route needs (not the whole city), keeps one-way
    streets directed, and caches the result as GraphML so later runs are offline.
    """
    metric = stops.estimate_utm_crs()
    area = stops.to_crs(metric).union_all().convex_hull.buffer(buffer_m)
    polygon = gpd.GeoSeries([area], crs=metric).to_crs("EPSG:4326").iloc[0]

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(polygon.wkb).hexdigest()[:12]
    path = cache_dir / f"drive_{key}.graphml"
    if path.exists():
        return ox.load_graphml(path)

    G = ox.graph_from_polygon(polygon, network_type="drive", retain_all=False)
    ox.save_graphml(G, path)
    return G
