import pandas as pd
import os

# You may need to adjust this path depending on where your GTFS data lives
GTFS_PATH = os.path.join("gtfs")

# Load GTFS files
routes_df = pd.read_csv(os.path.join(GTFS_PATH, "routes.txt"))
trips_df = pd.read_csv(os.path.join(GTFS_PATH, "trips.txt"))
stop_times_df = pd.read_csv(os.path.join(GTFS_PATH, "stop_times.txt"))
stops_df = pd.read_csv(os.path.join(GTFS_PATH, "stops.txt"))


print("Route IDs in routes.txt:")
print(routes_df[['route_id', 'route_short_name', 'route_long_name']].head(20))

print("\nRoute IDs in trips.txt (unique):")
print(trips_df['route_id'].unique())


def get_route_stop_sequence_by_route_id(route_id="61388"):
    """
    Given a known GTFS route_id (e.g. '61388' for 504 King), return ordered stop list with lat/lon.
    """
    # Step 1: Get a sample trip_id for the route
    trip_row = trips_df[trips_df['route_id'] == int(route_id)]
    if trip_row.empty:
        raise ValueError(f"No trips found for route_id {route_id}.")
    
    sample_trip_id = trip_row.iloc[0]['trip_id']
    print(f"Using trip_id: {sample_trip_id}")

    # Step 2: Get ordered stop_ids for that trip
    trip_stops = stop_times_df[stop_times_df['trip_id'] == sample_trip_id].sort_values('stop_sequence')
    stop_ids = trip_stops['stop_id'].tolist()

    # Step 3: Map stop_ids to lat/lon + names
    stop_info = stops_df[stops_df['stop_id'].isin(stop_ids)][['stop_id', 'stop_name', 'stop_lat', 'stop_lon']]
    stop_info = stop_info.set_index('stop_id').loc[stop_ids].reset_index()

    return stop_info




if __name__ == "__main__":
    stop_info = get_route_stop_sequence_by_route_id("61388")
    print(stop_info.head(10))  # show first 10 stops for 504 King



