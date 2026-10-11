import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.gtfs_parser import get_route_stop_sequence
from simulation.graph_builder import build_route_graph
from simulation.flood_blocker import block_flooded_segments

def main():
    # Load ordered stop data for Route 504 King
    stops_504 = get_route_stop_sequence("61388")  # ✅ Use route_id
    print("First 5 stops on Route 504 King:")
    print(stops_504.head())

if __name__ == "__main__":
    main()
