import sumolib
import xml.etree.ElementTree as ET
from collections import defaultdict
import csv

def get_edges_from_net(net_file):
    """Returns a list of non-internal edge IDs from a SUMO network file."""
    net = sumolib.net.readNet(net_file)
    return [edge.getID() for edge in net.getEdges() if not edge.getID().startswith(":")]

def parse_fcd_and_write_congestion(fcd_file, net_file, output_csv):
    """Parses an FCD file and writes per-edge congestion data to a CSV file."""
    epsilon = 0.1  # To prevent division by zero
    valid_edges = set(get_edges_from_net(net_file))
    edge_data = defaultdict(lambda: defaultdict(list))  # edge -> time -> [speeds]

    context = sumolib.xml.parse(fcd_file, 'timestep')
    for timestep in context:
        t = float(timestep.time)
        vehicles = getattr(timestep, 'vehicle', [])
        if vehicles is None:
            continue
        if not isinstance(vehicles, list):
            vehicles = [vehicles]

        for v in vehicles:
            lane_id = getattr(v, 'lane', '')
            if not lane_id:
                continue
            edge_id = lane_id.split('_')[0]
            if edge_id in valid_edges:
                speed = float(getattr(v, 'speed', 0.0))
                edge_data[edge_id][t].append(speed)

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["edge_id", "time", "vehicle_count", "avg_speed", "congestion_index"])
        for edge_id, time_speeds in edge_data.items():
            for t, speeds in sorted(time_speeds.items()):
                count = len(speeds)
                avg_speed = sum(speeds) / count if count > 0 else 0.0
                congestion_index = count / (avg_speed + epsilon) if count > 0 else 0.0
                writer.writerow([edge_id, t, count, round(avg_speed, 2), round(congestion_index, 2)])

    print(f"Congestion data written to: {output_csv}")

# --- Run ---
fcd_file = "fcdZ.xml"
net_file = "new.net.xml"
output_csv = "edge_congestion_summary.csv"

parse_fcd_and_write_congestion(fcd_file, net_file, output_csv)
