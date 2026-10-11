from geopy.distance import geodesic

def block_flooded_segments(G, flooded_coords, threshold=50):
    """
    flooded_coords: list of (lat, lon) for flooded points
    threshold: meters from edge to be considered flooded
    """
    edges_to_remove = []

    
    for u, v, data in G.edges(data=True):
        coord_u = G.nodes[u]['pos']
        coord_v = G.nodes[v]['pos']

        for flood_point in flooded_coords:
            dist_u = geodesic(coord_u, flood_point).meters
            dist_v = geodesic(coord_v, flood_point).meters

            if dist_u < threshold or dist_v < threshold:
                print(f"Edge ({u}, {v}) is {dist_u:.1f}m and {dist_v:.1f}m from flood → REMOVED")
                edges_to_remove.append((u, v))
                break



    G.remove_edges_from(edges_to_remove)
    return G, edges_to_remove
