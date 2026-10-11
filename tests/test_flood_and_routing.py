import math

import networkx as nx
import osmnx as ox
import pytest

from floodsim import flood
from floodsim.routing import simulate

from .conftest import LAT0, LON0, M_PER_DEG_LAT, make_grid, offset, stops_at


def test_zone_radius_is_in_metres():
    zones = flood.zones_from_points([(LAT0, LON0)], radius_m=150)
    near = stops_at_points([offset(0, 100)])
    far = stops_at_points([offset(0, 200)])
    assert flood.stops_in_zones(near, zones) == {0}
    assert flood.stops_in_zones(far, zones) == set()


def stops_at_points(lonlats):
    import geopandas as gpd
    from shapely.geometry import Point

    return gpd.GeoDataFrame({"stop_name": ["x"] * len(lonlats)}, geometry=[Point(*p) for p in lonlats], crs="EPSG:4326")


def test_edge_crossing_zone_is_cut_even_when_both_ends_are_dry():
    # One long 1 km street; the flood sits in the middle, 500 m from either end.
    G = nx.MultiDiGraph(crs="EPSG:4326")
    (x0, y0), (x1, y1) = offset(0, 0), offset(1000, 0)
    G.add_node(1, x=x0, y=y0)
    G.add_node(2, x=x1, y=y1)
    G.add_edge(1, 2, key=0, length=1000.0)
    lon, lat = offset(500, 0)
    zones = flood.zones_from_points([(lat, lon)], radius_m=50)

    cut = flood.flooded_edges(ox.graph_to_gdfs(G, nodes=False), zones)

    assert cut == [(1, 2, 0)]  # the old endpoint-distance check missed this


def test_detour_around_flooded_middle_stop(grid):
    # Route runs along the middle row: (0,1) -> (1,1) -> (2,1). Flood the centre.
    stops = stops_at(grid, [1, 11, 21])
    lon, lat = grid.nodes[11]["x"], grid.nodes[11]["y"]
    zones = flood.zones_from_points([(lat, lon)], radius_m=60)
    cut = flood.flooded_edges(ox.graph_to_gdfs(grid, nodes=False), zones)
    closed = flood.stops_in_zones(stops, zones)

    result = simulate(grid, stops, closed, cut)

    assert closed == {1}
    assert result.baseline_m == pytest.approx(400)
    # Around the block: up/down 200, across 400, back 200.
    assert result.flooded_m == pytest.approx(800)
    [d] = result.diversions
    assert (d.from_stop, d.to_stop, d.closed_stops) == (0, 2, [1])
    assert d.extra_m == pytest.approx(400)


def test_one_way_streets_are_respected():
    # Make the direct street 0 -> 10 one-way the wrong way (10 -> 0 only).
    G = make_grid(one_way={(10, 0)})
    stops = stops_at(G, [0, 10])

    result = simulate(G, stops, closed_stops=set(), removed_edges=[])

    assert result.baseline_m == pytest.approx(600)  # forced around the block


def test_no_path_is_reported_not_hidden(grid):
    stops = stops_at(grid, [0, 22])
    every_edge = list(ox.graph_to_gdfs(grid, nodes=False).index)

    result = simulate(grid, stops, closed_stops=set(), removed_edges=every_edge)

    assert len(result.unreachable) == 1
    assert result.diversions[0].detour_m is None
    assert math.isnan(result.flooded[0].length_m)
