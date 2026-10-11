# TTC flood rerouting simulation

Floods part of Toronto's street network and works out how a TTC route would have to detour: which stops close, which roads are cut, and how much longer the trip gets. Produces an interactive map.

Built on TTC GTFS schedule data and OpenStreetMap streets (via [OSMnx](https://osmnx.readthedocs.io/)).

Started as a first-year team design project for ES 1050 at Western Engineering (winter 2025): the brief was to take on a problem related to flooding or fires, and our team chose flooding in Toronto. The original team prototype is preserved in `legacy/`; the package in `floodsim/` is a 2026 rebuild. An interactive browser version runs on [my portfolio](https://yacoubderradji.dev/projects/ttc-flood-sim).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Put a TTC GTFS feed in `data/gtfs/` (the folder with `routes.txt`, `trips.txt`, `stop_times.txt`, `stops.txt`). The current feed is published on the City of Toronto Open Data portal ("TTC Routes and Schedules"). The feed this project was first built with dates from fall 2020.

## Usage

```bash
# Flood a 200 m circle at King & Bathurst
python -m floodsim --route 504 --flood-point 43.6440,-79.4026 --radius 200

# Flood around the 3rd stop of the route (0-based index)
python -m floodsim --route 504 --flood-stop-index 2 --radius 150

# Use real flood polygons (e.g. a floodplain map exported as GeoJSON)
python -m floodsim --route 504 --flood-file data/floodplain.geojson
```

The first run downloads the street network around the route and caches it in `data/osm/`; later runs are offline. The map is written to `output/flood_map.html` (change with `--out`).

Example output:

```
Flooded road segments: 32
Closed stops: KING ST WEST AT BATHURST ST EAST SIDE
Normal route length:   9.48 km
Route during flood:    11.25 km
  KING ST WEST AT TECUMSETH ST -> KING ST WEST AT PORTLAND ST EAST SIDE: detour 2.21 km vs normal 0.44 km (+1777 m)
```

## How it works

1. **Route**: picks the most common stop pattern for the route and direction from GTFS (so night variants and short turns don't distort it).
2. **Streets**: downloads the drivable network for a corridor around the route and keeps it *directed*, so one-way streets are respected.
3. **Flood**: a road segment is cut if its geometry intersects a flood zone (spatial index, so it's fast on city-scale networks). Stops inside a zone are closed.
4. **Routing**: shortest paths by road length between consecutive open stops, before and after the flood. Each diversion is compared with the normal path over the same span of stops.

Streetcar routes (like the 504) are modelled on the road network, i.e. as the replacement shuttle bus that would run during a closure.

## Tests

```bash
python -m pytest
```

The tests use small synthetic street grids, so they run offline in under a second.

## Changes from the 2025 version

The original prototype is kept in `legacy/` for reference. The rewrite fixes:

- `main.py` imported a function that didn't exist, and `_init_.py` was misnamed, so the package couldn't be imported.
- Every run downloaded Toronto's entire street network; now only the route corridor is fetched, and it's cached.
- Flooded roads were detected by checking only the two *endpoints* of each segment, with slow per-point geodesic math; long roads passing through a flood zone were missed.
- The graph was converted to undirected, ignoring one-way streets.
- "Total rerouted distance" was the number of path points times 0.01, not a distance.
- The 4-million-row `stop_times.txt` was loaded in full at import time.

## Ideas for next steps

- Real flood scenarios: TRCA regulatory floodplain polygons, or a rainfall-driven model.
- Multiple routes at once, to show network-wide impact.
- Travel time (using speed limits) instead of distance.
- Filter by branch/headsign (e.g. 504A vs 504B).
