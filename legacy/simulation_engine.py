import networkx as nx
import osmnx as ox
import folium
from geopy.distance import geodesic
from folium import Marker, PolyLine

from simulation.flood_blocker import block_flooded_segments

def simulate_reroute(stops, flooded_stop_ids, threshold=150):
    """
    Simulate rerouting a TTC route using A* pathfinding around flooded areas.
    Shows original path (following roads) and rerouted path on a folium map.
    """
    stop_coords = [(s['stop_lat'], s['stop_lon']) for s in stops]
    flooded_coords = [(s['stop_lat'], s['stop_lon']) for s in stops if s['stop_id'] in flooded_stop_ids]
    safe_stops = [s for s in stops if s['stop_id'] not in flooded_stop_ids]

    if not safe_stops:
        raise ValueError("No remaining stops after flood filtering.")

    # Get bounding box for all stops (min/max lat/lon)
    lats = [s['stop_lat'] for s in stops]
    lons = [s['stop_lon'] for s in stops]
    north, south = max(lats) + 0.005, min(lats) - 0.005
    east, west = max(lons) + 0.005, min(lons) - 0.005

    # Create a polygon that covers the whole area
    polygon = ox.geocode_to_gdf("Toronto, Ontario").geometry[0]

    # Load the entire graph covering the polygon
    G = ox.graph_from_polygon(polygon, network_type='drive')
    G = nx.Graph(G)

    # Add position to each node
    for node_id in G.nodes:
        G.nodes[node_id]['pos'] = (G.nodes[node_id]['y'], G.nodes[node_id]['x'])

    # Block flooded segments
    G, removed_edges = block_flooded_segments(G, flooded_coords, threshold=threshold)

    # Prepare the folium map
    fmap = folium.Map(location=[lats[len(lats) // 2], lons[len(lons) // 2]], zoom_start=13)

    def plot_route(path_coords, color, tooltip):
        """Helper to plot a route."""
        if path_coords:
            PolyLine(path_coords, color=color, weight=5, tooltip=tooltip).add_to(fmap)

    # Function to find the shortest path between stops
    def find_path(G, start, end):
        try:
            start_node = ox.distance.nearest_nodes(G, start[1], start[0])
            end_node = ox.distance.nearest_nodes(G, end[1], end[0])
            if start_node == end_node:
                print(f"Start and end nodes are the same: {start_node}")
                return []
            path = nx.shortest_path(G, start_node, end_node, weight='length', method='dijkstra')
            return [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
        except Exception as e:
            print(f"Error finding path from {start} to {end}: {e}")
            return []

    # Plot original path using A* between stops
    original_segments = []
    for i in range(len(stop_coords) - 1):
        start = stop_coords[i]
        end = stop_coords[i + 1]
        segment = find_path(G, start, end)
        if segment:
            original_segments.extend(segment)

    plot_route(original_segments, color="black", tooltip="Original Path")

    # Rerouted path using A* avoiding flooded segments
    rerouted_segments = []
    for i in range(len(safe_stops) - 1):
        start = (safe_stops[i]['stop_lat'], safe_stops[i]['stop_lon'])
        end = (safe_stops[i + 1]['stop_lat'], safe_stops[i + 1]['stop_lon'])
        segment = find_path(G, start, end)
        if segment:
            rerouted_segments.extend(segment)

    plot_route(rerouted_segments, color="blue", tooltip="Rerouted Path")

    # Plot all stops
    for s in stops:
        icon_color = "red" if s['stop_id'] in flooded_stop_ids else "blue"
        Marker(
            location=(s['stop_lat'], s['stop_lon']),
            popup=s['stop_name'],
            icon=folium.Icon(color=icon_color)
        ).add_to(fmap)

    # Plot flooded segments
    for u, v in removed_edges:
        try:
            coord_u = G.nodes[u]['pos']
            coord_v = G.nodes[v]['pos']
            PolyLine([coord_u, coord_v], color="red", weight=3, opacity=0.8, tooltip="Flooded Road").add_to(fmap)
        except:
            continue

    print(f"Total rerouted distance: {len(rerouted_segments) * 0.01:.2f} km")
    print(f"Flooded roads removed: {len(removed_edges)}")

    return fmap
