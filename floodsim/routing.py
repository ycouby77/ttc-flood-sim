"""Route a vehicle through its stops before and after a flood."""
from __future__ import annotations

from dataclasses import dataclass, field

import geopandas as gpd
import networkx as nx
import osmnx as ox


@dataclass
class Leg:
    from_stop: int  # index into the stop list
    to_stop: int
    nodes: list | None  # None = no drivable path
    length_m: float


@dataclass
class Diversion:
    """One stretch where flooded stops are skipped and the vehicle detours."""

    from_stop: int  # last dry stop before the closure
    to_stop: int  # first dry stop after it
    closed_stops: list[int]
    normal_m: float  # normal path over the same span (through the closed stops)
    detour_m: float | None  # None = no path exists around the flood

    @property
    def extra_m(self) -> float | None:
        return None if self.detour_m is None else self.detour_m - self.normal_m


@dataclass
class SimResult:
    baseline: list[Leg]
    flooded: list[Leg]
    closed_stops: list[int]
    removed_edges: list[tuple]
    diversions: list[Diversion] = field(default_factory=list)

    @property
    def baseline_m(self) -> float:
        return sum(l.length_m for l in self.baseline if l.nodes)

    @property
    def flooded_m(self) -> float:
        return sum(l.length_m for l in self.flooded if l.nodes)

    @property
    def unreachable(self) -> list[Leg]:
        return [l for l in self.flooded if l.nodes is None]


def snap_to_nodes(G: nx.MultiDiGraph, points: gpd.GeoDataFrame) -> list:
    """Nearest graph node to each point (spatial index; no extra dependencies)."""
    nodes = ox.graph_to_gdfs(G, edges=False)
    metric = points.estimate_utm_crs()
    nodes_m = nodes.to_crs(metric)
    _, idx = nodes_m.sindex.nearest(points.to_crs(metric).geometry, return_all=False)
    return list(nodes_m.index[idx])


def _leg(G: nx.MultiDiGraph, a: int, b: int, na, nb) -> Leg:
    if na == nb:
        return Leg(a, b, [na], 0.0)
    try:
        path = nx.shortest_path(G, na, nb, weight="length")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return Leg(a, b, None, float("nan"))
    return Leg(a, b, path, nx.path_weight(G, path, weight="length"))


def route_through(G: nx.MultiDiGraph, stop_nodes: list, order: list[int]) -> list[Leg]:
    """Shortest drivable legs visiting `order` (indices into stop_nodes) in sequence."""
    return [_leg(G, a, b, stop_nodes[a], stop_nodes[b]) for a, b in zip(order, order[1:])]


def simulate(G: nx.MultiDiGraph, stops: gpd.GeoDataFrame, closed_stops: set[int], removed_edges: list[tuple]) -> SimResult:
    """Compare the normal route with the route after `removed_edges` are flooded.

    Closed stops (inside a flood zone) are skipped; every other stop is still served.
    """
    stop_nodes = snap_to_nodes(G, stops)
    everyone = list(range(len(stops)))
    baseline = route_through(G, stop_nodes, everyone)

    H = G.copy()
    H.remove_edges_from(removed_edges)
    open_stops = [i for i in everyone if i not in closed_stops]
    flooded = route_through(H, stop_nodes, open_stops)

    base_len = {(l.from_stop, l.to_stop): l.length_m for l in baseline}
    diversions = []
    for leg in flooded:
        skipped = list(range(leg.from_stop + 1, leg.to_stop))
        normal = sum(base_len[(i, i + 1)] for i in range(leg.from_stop, leg.to_stop))
        # A leg is a diversion if it skips stops or its path changed length.
        changed = leg.nodes is None or abs(leg.length_m - normal) > 1.0
        if skipped or changed:
            diversions.append(Diversion(leg.from_stop, leg.to_stop, skipped, normal, None if leg.nodes is None else leg.length_m))

    return SimResult(baseline, flooded, sorted(closed_stops), removed_edges, diversions)
