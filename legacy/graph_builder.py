import networkx as nx
from geopy.distance import geodesic  # For real-world distance

def build_route_graph(stops_df):
    G = nx.Graph()

    for i in range(len(stops_df) - 1):
        stop_a = stops_df.iloc[i]
        stop_b = stops_df.iloc[i + 1]

        coord_a = (stop_a['stop_lat'], stop_a['stop_lon'])
        coord_b = (stop_b['stop_lat'], stop_b['stop_lon'])
        distance = geodesic(coord_a, coord_b).meters

        G.add_node(stop_a['stop_id'], pos=coord_a, name=stop_a['stop_name'])
        G.add_node(stop_b['stop_id'], pos=coord_b, name=stop_b['stop_name'])
        G.add_edge(stop_a['stop_id'], stop_b['stop_id'], weight=distance)

    return G
