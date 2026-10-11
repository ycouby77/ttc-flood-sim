"""Flood zones and the road segments they cut."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point
from shapely.ops import unary_union

WGS84 = "EPSG:4326"


def zones_from_points(points: list[tuple[float, float]], radius_m: float) -> gpd.GeoDataFrame:
    """Circular flood zones around (lat, lon) points, `radius_m` metres across each way."""
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    pts = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lat, lon in points], crs=WGS84)
    # Buffer in a metric CRS, not degrees.
    metric = pts.estimate_utm_crs()
    return gpd.GeoDataFrame(geometry=pts.to_crs(metric).buffer(radius_m), crs=metric).to_crs(WGS84)


def zones_from_file(path: str | Path) -> gpd.GeoDataFrame:
    """Flood polygons from GeoJSON / shapefile (e.g. a floodplain map export)."""
    zones = gpd.read_file(path)
    zones = zones[zones.geometry.notna() & zones.geom_type.isin(["Polygon", "MultiPolygon"])]
    if zones.empty:
        raise ValueError(f"No polygon geometry found in {path}")
    return zones.to_crs(WGS84)


def flooded_edges(edges: gpd.GeoDataFrame, zones: gpd.GeoDataFrame) -> list[tuple]:
    """Edges whose road geometry intersects any flood zone.

    `edges` is the edge GeoDataFrame from osmnx (index = (u, v, key)). The test is
    on the full road line, so a long segment passing through a zone is caught even
    when both of its intersections are dry.
    """
    zones = zones.to_crs(edges.crs)
    hit = edges.sindex.query(unary_union(zones.geometry.values), predicate="intersects")
    return list(edges.index[hit])


def stops_in_zones(stops: gpd.GeoDataFrame, zones: gpd.GeoDataFrame) -> set[int]:
    """Positional indices of stops that sit inside a flood zone (and so are closed)."""
    zones = zones.to_crs(stops.crs)
    inside = stops.geometry.intersects(unary_union(zones.geometry.values))
    return {i for i, flag in enumerate(inside) if flag}


def remove_edges(G: nx.MultiDiGraph, edges: list[tuple]) -> nx.MultiDiGraph:
    H = G.copy()
    H.remove_edges_from(edges)
    return H
