from pathlib import Path

import pytest

from floodsim.gtfs import load_route_stops


def write(dir: Path, name: str, text: str):
    (dir / f"{name}.txt").write_text(text.strip() + "\n")


@pytest.fixture
def feed(tmp_path):
    write(tmp_path, "routes", """
route_id,agency_id,route_short_name,route_long_name,route_desc,route_type
61388,1,504,KING,,0
""")
    write(tmp_path, "trips", """
route_id,service_id,trip_id,trip_headsign,direction_id
61388,1,A,EAST - 504 KING towards BROADVIEW,0
61388,1,B,EAST - 504 KING short turn,0
61388,1,C,WEST - 504 KING towards DUNDAS WEST,1
61388,1,N,EAST - 304 KING night,0
61388,1,A2,EAST - 504 KING towards BROADVIEW,0
""")
    write(tmp_path, "stop_times", """
trip_id,arrival_time,departure_time,stop_id,stop_sequence
B,08:00:00,08:00:00,s2,1
B,08:01:00,08:01:00,s3,2
A,08:00:00,08:00:00,s1,1
A,08:02:00,08:02:00,s3,3
A,08:01:00,08:01:00,s2,2
C,08:00:00,08:00:00,s3,1
N,02:00:00,02:00:00,s1,1
N,02:01:00,02:01:00,s2,2
N,02:02:00,02:02:00,s3,3
N,02:03:00,02:03:00,s4,4
A2,09:00:00,09:00:00,s1,1
A2,09:01:00,09:01:00,s2,2
A2,09:02:00,09:02:00,s3,3
""")
    write(tmp_path, "stops", """
stop_id,stop_code,stop_name,stop_lat,stop_lon
s1,101,King St West at Dufferin,43.638,-79.429
s2,102,King St West at Bathurst,43.643,-79.403
s3,103,King St East at Yonge,43.649,-79.378
s4,104,Night-only detour stop,43.655,-79.360
""")
    return tmp_path


def test_uses_most_common_pattern_not_longest(feed):
    # The single 4-stop night trip (N) is longest, but the 3-stop day pattern runs twice.
    route = load_route_stops(feed, "504", direction_id=0)
    assert route.stops.stop_id.tolist() == ["s1", "s2", "s3"]
    assert route.headsign.endswith("BROADVIEW")
    assert route.is_streetcar


def test_route_id_also_works(feed):
    assert load_route_stops(feed, "61388").short_name == "504"


def test_unknown_route_is_a_clear_error(feed):
    with pytest.raises(ValueError, match="not found"):
        load_route_stops(feed, "999")
