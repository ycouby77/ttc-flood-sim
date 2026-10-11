"""Synthetic street grids so tests run offline and fast."""
import math

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import Point

LAT0, LON0 = 43.65, -79.40  # downtown Toronto
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))


def offset(east_m: float, north_m: float) -> tuple[float, float]:
    """(lon, lat) of a point east/north of the origin, in metres."""
    return LON0 + east_m / M_PER_DEG_LON, LAT0 + north_m / M_PER_DEG_LAT


def make_grid(n: int = 3, spacing: float = 200.0, one_way: set[tuple] | None = None) -> nx.MultiDiGraph:
    """n x n grid of two-way streets, `spacing` metres apart. Node id = (col, row) -> col*10+row.

    `one_way` lists (u, v) pairs that may only be driven u -> v.
    """
    one_way = one_way or set()
    G = nx.MultiDiGraph(crs="EPSG:4326")
    for c in range(n):
        for r in range(n):
            x, y = offset(c * spacing, r * spacing)
            G.add_node(c * 10 + r, x=x, y=y)
    for c in range(n):
        for r in range(n):
            for dc, dr in ((1, 0), (0, 1)):
                if c + dc < n and r + dr < n:
                    u, v = c * 10 + r, (c + dc) * 10 + (r + dr)
                    if (v, u) not in one_way:
                        G.add_edge(u, v, key=0, length=spacing)
                    if (u, v) not in one_way:
                        G.add_edge(v, u, key=0, length=spacing)
    return G


def stops_at(G: nx.MultiDiGraph, nodes: list[int]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"stop_id": [str(n) for n in nodes], "stop_code": [str(n) for n in nodes], "stop_name": [f"Stop {n}" for n in nodes]},
        geometry=[Point(G.nodes[n]["x"], G.nodes[n]["y"]) for n in nodes],
        crs="EPSG:4326",
    )


@pytest.fixture
def grid():
    return make_grid()
