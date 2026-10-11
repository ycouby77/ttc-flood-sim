"""Export a route + its street network as compact JSON for the in-browser simulator.

  python -m floodsim.export_web --route 504 --out ../portfolio-site/public/data/flood/route504.json

Format (all coordinates [lon, lat], rounded to ~10 cm):
  nodes:  [[lon, lat], ...]
  edges:  [[u, v, length_m, geom_id, reversed], ...]   directed, u/v index into nodes
  geoms:  [[lon, lat, lon, lat, ...], ...]              street centrelines, shared by both directions
  stops:  [{name, node, lon, lat}, ...]                 in route order, node = snapped graph node
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import osmnx as ox

from .gtfs import load_route_stops
from .network import drive_graph_around
from .routing import snap_to_nodes


def _r(v: float) -> float:
    return round(v, 6)


def export(gtfs: str, route_id: str, direction: int, buffer_m: float) -> dict:
    route = load_route_stops(gtfs, route_id, direction)
    G = drive_graph_around(route.stops, buffer_m=buffer_m)
    edges = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)

    node_ids = list(G.nodes)
    index = {n: i for i, n in enumerate(node_ids)}
    nodes = [[_r(G.nodes[n]["x"]), _r(G.nodes[n]["y"])] for n in node_ids]

    geoms, geom_key = [], {}
    out_edges = []
    for (u, v, _k), row in edges.iterrows():
        coords = [c for xy in row.geometry.simplify(0.00001).coords for c in (_r(xy[0]), _r(xy[1]))]
        fwd, rev = tuple(coords), tuple(coords[i] for j in range(len(coords) - 2, -1, -2) for i in (j, j + 1))
        if fwd in geom_key:
            gid, flipped = geom_key[fwd], 0
        elif rev in geom_key:
            gid, flipped = geom_key[rev], 1
        else:
            gid, flipped = len(geoms), 0
            geom_key[fwd] = gid
            geoms.append(coords)
        out_edges.append([index[u], index[v], round(float(row["length"]), 1), gid, flipped])

    snapped = snap_to_nodes(G, route.stops)
    stops = [
        {"name": row.stop_name.title(), "node": index[n], "lon": _r(row.geometry.x), "lat": _r(row.geometry.y)}
        for row, n in zip(route.stops.itertuples(), snapped)
    ]
    return {
        "route": {
            "number": route.short_name,
            "name": route.long_name.title(),
            "headsign": route.headsign,
            "streetcar": route.is_streetcar,
        },
        "nodes": nodes,
        "edges": out_edges,
        "geoms": geoms,
        "stops": stops,
        "attribution": "Street data (c) OpenStreetMap contributors (ODbL). Schedule data: TTC GTFS.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gtfs", default="data/gtfs")
    p.add_argument("--route", required=True)
    p.add_argument("--direction", type=int, default=0)
    p.add_argument("--buffer", type=float, default=1000)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    data = export(a.gtfs, a.route, a.direction, a.buffer)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, separators=(",", ":")))
    print(f"{len(data['nodes'])} nodes, {len(data['edges'])} edges, {len(data['geoms'])} geometries, "
          f"{len(data['stops'])} stops -> {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
