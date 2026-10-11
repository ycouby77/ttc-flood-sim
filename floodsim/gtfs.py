"""Load a TTC route's ordered stop list from a GTFS feed."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

WGS84 = "EPSG:4326"


@dataclass
class RouteStops:
    route_id: str
    short_name: str
    long_name: str
    route_type: int  # GTFS: 0 = streetcar, 3 = bus, 1 = subway
    direction_id: int
    headsign: str
    stops: gpd.GeoDataFrame  # ordered; columns: stop_id, stop_code, stop_name, geometry

    @property
    def is_streetcar(self) -> bool:
        return self.route_type == 0


def _read(gtfs_dir: Path, name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(gtfs_dir / f"{name}.txt", dtype=str, **kw)


def load_route_stops(gtfs_dir: str | Path, route: str, direction_id: int = 0) -> RouteStops:
    """Return the stop sequence for one direction of a route.

    `route` may be the public route number ("504") or the GTFS route_id ("61388").
    Uses the most common stop pattern in that direction (ties go to the longer
    pattern), so night variants like the 304 and short turns don't win.
    """
    gtfs_dir = Path(gtfs_dir)
    routes = _read(gtfs_dir, "routes")
    match = routes[(routes.route_short_name == route) | (routes.route_id == route)]
    if match.empty:
        raise ValueError(f"Route {route!r} not found in {gtfs_dir / 'routes.txt'}")
    r = match.iloc[0]

    trips = _read(gtfs_dir, "trips", usecols=["route_id", "trip_id", "direction_id", "trip_headsign"])
    trips = trips[(trips.route_id == r.route_id) & (trips.direction_id == str(direction_id))]
    if trips.empty:
        raise ValueError(f"No trips for route {route} in direction {direction_id}")

    # stop_times is the big file (millions of rows); read only the columns we need.
    st = _read(gtfs_dir, "stop_times", usecols=["trip_id", "stop_id", "stop_sequence"])
    st = st[st.trip_id.isin(set(trips.trip_id))]
    st["stop_sequence"] = st.stop_sequence.astype(int)

    st = st.sort_values(["trip_id", "stop_sequence"])
    patterns = st.groupby("trip_id").stop_id.agg(tuple)
    counts = patterns.value_counts()
    best = max(counts.index, key=lambda p: (counts[p], len(p)))
    chosen_trip = patterns[patterns == best].index[0]
    seq = st[st.trip_id == chosen_trip]

    stops = _read(gtfs_dir, "stops", usecols=lambda c: c in {"stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon"})
    seq = seq.merge(stops, on="stop_id", how="left")
    if seq.stop_lat.isna().any():
        missing = seq.loc[seq.stop_lat.isna(), "stop_id"].tolist()
        raise ValueError(f"stops.txt is missing coordinates for stop_ids {missing[:5]}")

    gdf = gpd.GeoDataFrame(
        seq[["stop_id", "stop_code", "stop_name"]].reset_index(drop=True),
        geometry=gpd.points_from_xy(seq.stop_lon.astype(float), seq.stop_lat.astype(float)),
        crs=WGS84,
    )
    headsign = trips.loc[trips.trip_id == chosen_trip, "trip_headsign"].iloc[0]
    return RouteStops(
        route_id=r.route_id,
        short_name=r.route_short_name,
        long_name=r.route_long_name,
        route_type=int(r.route_type),
        direction_id=direction_id,
        headsign=headsign,
        stops=gdf,
    )
