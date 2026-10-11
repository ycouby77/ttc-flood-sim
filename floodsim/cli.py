"""Command line: simulate a flood on a TTC route and write a map.

Examples:
  python -m floodsim --route 504 --flood-stop-index 20 --radius 150
  python -m floodsim --route 504 --flood-point 43.6487,-79.3960 --radius 200
  python -m floodsim --route 504 --flood-file data/floodplain.geojson
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import osmnx as ox

from . import flood
from .gtfs import load_route_stops
from .network import drive_graph_around
from .routing import simulate
from .viz import render_map


def _point(s: str) -> tuple[float, float]:
    lat, lon = (float(v) for v in s.split(","))
    return lat, lon


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="floodsim", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gtfs", default="data/gtfs", help="GTFS folder (default: data/gtfs)")
    p.add_argument("--route", required=True, help='route number or GTFS route_id, e.g. "504"')
    p.add_argument("--direction", type=int, default=0, choices=[0, 1])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--flood-point", type=_point, action="append", help="flood centre as LAT,LON (repeatable)")
    src.add_argument("--flood-stop-index", type=int, action="append", help="flood centred on the Nth stop of the route (0-based, repeatable)")
    src.add_argument("--flood-file", help="GeoJSON/shapefile of flood polygons")
    p.add_argument("--radius", type=float, default=150, help="flood radius in metres for point/stop floods (default 150)")
    p.add_argument("--buffer", type=float, default=1000, help="street network margin around the route in metres (default 1000)")
    p.add_argument("--out", default="output/flood_map.html")
    args = p.parse_args(argv)

    route = load_route_stops(args.gtfs, args.route, args.direction)
    stops = route.stops
    print(f"Route {route.short_name} {route.long_name} -> {route.headsign}: {len(stops)} stops")
    if route.is_streetcar:
        print("Note: this is a streetcar route. Detours are modelled on the road network, i.e. as a replacement shuttle bus.")

    if args.flood_file:
        zones = flood.zones_from_file(args.flood_file)
    else:
        if args.flood_stop_index:
            bad = [i for i in args.flood_stop_index if not 0 <= i < len(stops)]
            if bad:
                p.error(f"--flood-stop-index must be between 0 and {len(stops) - 1}; got {bad}")
            centres = [(stops.geometry.iloc[i].y, stops.geometry.iloc[i].x) for i in args.flood_stop_index]
        else:
            centres = args.flood_point
        zones = flood.zones_from_points(centres, args.radius)

    print("Loading street network (cached after the first run)...")
    G = drive_graph_around(stops, buffer_m=args.buffer)
    edges = ox.graph_to_gdfs(G, nodes=False)
    cut = flood.flooded_edges(edges, zones)
    closed = flood.stops_in_zones(stops, zones)

    result = simulate(G, stops, closed, cut)

    km = lambda m: f"{m / 1000:.2f} km"
    print(f"\nFlooded road segments: {len(cut)}")
    print(f"Closed stops: {', '.join(stops.stop_name.iloc[i] for i in result.closed_stops) or 'none'}")
    print(f"Normal route length:   {km(result.baseline_m)}")
    print(f"Route during flood:    {km(result.flooded_m)}")
    for d in result.diversions:
        a, b = stops.stop_name.iloc[d.from_stop], stops.stop_name.iloc[d.to_stop]
        if d.detour_m is None:
            print(f"  {a} -> {b}: NO drivable path around the flood")
        else:
            print(f"  {a} -> {b}: detour {km(d.detour_m)} vs normal {km(d.normal_m)} ({d.extra_m:+.0f} m)")
    if result.unreachable:
        print(f"Warning: {len(result.unreachable)} leg(s) have no drivable path.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_map(G, stops, zones, result, f"Route {route.short_name} flood simulation").save(out)
    print(f"\nMap written to {out}")
    return 0 if not any(math.isnan(l.length_m) for l in result.baseline) else 1
