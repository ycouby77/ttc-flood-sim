"""Interactive Leaflet map of a simulation result."""
from __future__ import annotations

import folium
import geopandas as gpd
import networkx as nx
import osmnx as ox

from .routing import Leg, SimResult


def _leg_lines(G: nx.MultiDiGraph, legs: list[Leg]) -> list[list[tuple[float, float]]]:
    lines = []
    for leg in legs:
        if not leg.nodes or len(leg.nodes) < 2:
            continue
        gdf = ox.routing.route_to_gdf(G, leg.nodes, weight="length")
        for geom in gdf.geometry:
            lines.append([(y, x) for x, y in geom.coords])
    return lines


def render_map(G: nx.MultiDiGraph, stops: gpd.GeoDataFrame, zones: gpd.GeoDataFrame, result: SimResult, title: str) -> folium.Map:
    center = stops.union_all().centroid
    fmap = folium.Map(location=(center.y, center.x), zoom_start=14, tiles="OpenStreetMap", control_scale=True)

    folium.GeoJson(
        zones.to_json(),
        name="Flood zones",
        style_function=lambda _: {"color": "#1f6feb", "weight": 1, "fillOpacity": 0.25},
    ).add_to(fmap)

    base = folium.FeatureGroup(name="Normal route")
    for line in _leg_lines(G, result.baseline):
        folium.PolyLine(line, color="#555555", weight=5, opacity=0.6).add_to(base)
    base.add_to(fmap)

    H = G.copy()
    H.remove_edges_from(result.removed_edges)
    detour = folium.FeatureGroup(name="Route during flood")
    for line in _leg_lines(H, result.flooded):
        folium.PolyLine(line, color="#e8590c", weight=4).add_to(detour)
    detour.add_to(fmap)

    cut = folium.FeatureGroup(name="Flooded road segments")
    edges = ox.graph_to_gdfs(G, nodes=False)
    for geom in edges.loc[result.removed_edges].geometry:
        folium.PolyLine([(y, x) for x, y in geom.coords], color="#c92a2a", weight=3).add_to(cut)
    cut.add_to(fmap)

    marks = folium.FeatureGroup(name="Stops")
    closed = set(result.closed_stops)
    for i, row in stops.reset_index(drop=True).iterrows():
        is_closed = i in closed
        folium.CircleMarker(
            (row.geometry.y, row.geometry.x),
            radius=5,
            color="#c92a2a" if is_closed else "#212529",
            fill=True,
            fill_opacity=1,
            tooltip=f"{row.stop_name}{' (closed)' if is_closed else ''}",
        ).add_to(marks)
    marks.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.get_root().html.add_child(folium.Element(f"<title>{title}</title>"))
    return fmap
