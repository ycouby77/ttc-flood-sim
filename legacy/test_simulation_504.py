from simulation.gtfs_parser import get_route_stop_sequence_by_route_id
from simulation.simulation_engine import simulate_reroute

stop_info = get_route_stop_sequence_by_route_id("61388")
stops_list = stop_info.to_dict(orient="records")

# Pick a flooded stop (3rd one)
flooded_stops = [stops_list[2]['stop_id']]
print(f"Flooded: {stops_list[2]['stop_name']}")

rerouted_map = simulate_reroute(stops_list, flooded_stops)
rerouted_map.save("reroute_test_504.html")
print("Saved map to reroute_test_504.html")
