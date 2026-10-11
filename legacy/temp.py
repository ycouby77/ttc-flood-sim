import pandas as pd

routes_df = pd.read_csv("gtfs/routes.txt")
trips_df = pd.read_csv("gtfs/trips.txt")

# Check which route_ids exist in both
valid_route_ids = routes_df[routes_df['route_id'].isin(trips_df['route_id'])]

print(valid_route_ids[['route_id', 'route_short_name', 'route_long_name']])
