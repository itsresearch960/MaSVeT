import traci
import math
import xml.etree.ElementTree as ET
import math
import random
'''
Charging station data for SUMO cs.add.xml is created.
'''
def parse_lane_shape(shape_input):
    """
    Parse a lane shape input which can be either:
      - A string of the format "x1,y1 x2,y2 ..." or
      - A tuple/list of coordinates.
    Returns a list of (x, y) float tuples.
    """
    if isinstance(shape_input, str):
        points = []
        segments = shape_input.strip().split()
        for seg in segments:
            x, y = seg.split(',')
            points.append((float(x), float(y)))
        return points
    elif isinstance(shape_input, (tuple, list)):
        if len(shape_input) > 0 and isinstance(shape_input[0], (tuple, list)):
            return list(shape_input)
        else:
            # If it's a flat list of coordinates, pair them up.
            it = iter(shape_input)
            return list(zip(it, it))
    else:
        raise ValueError("Unexpected lane shape input type: " + str(type(shape_input)))

def distance_point_to_segment(px, py, x1, y1, x2, y2):
    """
    Compute the Euclidean distance from point (px,py) to the segment (x1,y1)-(x2,y2).
    Returns:
      - The distance,
      - The projection point on the segment,
      - The parameter t (0<=t<=1) indicating the relative position.
    """
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1), (x1, y1), 0
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    dist = math.hypot(px - proj_x, py - proj_y)
    return dist, (proj_x, proj_y), t

def distance_point_to_polyline(px, py, polyline):
    """
    Compute the minimal distance from point (px,py) to a polyline (list of (x,y) points)
    and return that distance along with the cumulative position (in meters) along the polyline.
    """
    min_distance = float('inf')
    best_proj_length = 0
    total_length = 0
    for i in range(len(polyline) - 1):
        x1, y1 = polyline[i]
        x2, y2 = polyline[i+1]
        seg_length = math.hypot(x2 - x1, y2 - y1)
        dist, proj, t = distance_point_to_segment(px, py, x1, y1, x2, y2)
        if dist < min_distance:
            min_distance = dist
            best_proj_length = total_length + t * seg_length
        total_length += seg_length
    return min_distance, best_proj_length

def lane_length(polyline):
    """
    Compute the total length of a lane represented as a polyline (list of (x,y) points).
    """
    total = 0
    for i in range(len(polyline) - 1):
        total += math.hypot(polyline[i+1][0] - polyline[i][0],
                            polyline[i+1][1] - polyline[i][1])
    return total

def main():
    # Parse the charging station nodes from the XML file.
    cs_tree = ET.parse('charging_stations_xy.xml')
    cs_root = cs_tree.getroot()

    # Get lane shapes from SUMO TraCI.
    # Exclude internal lanes (IDs starting with ":")
    lane_shapes = {
        lane: parse_lane_shape(traci.lane.getShape(lane))
        for lane in traci.lane.getIDList() if not lane.startswith(":")
    }

    # Dictionary to store the generated charging stations.
    charging_stations = {}

    cs_file = "cs.add.xml"
    with open(cs_file, "w", encoding="utf-8") as f_cs:
        f_cs.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f_cs.write('<additional>\n')
        # Process each charging station node.
        for i, node in enumerate(cs_root.findall('node')):
            cs_x = float(node.get('x'))
            cs_y = float(node.get('y'))

            best_lane = None
            min_distance = float('inf')

            # Determine the nearest lane for this charging station.
            for lane_id, shape in lane_shapes.items():
                dist, _ = distance_point_to_polyline(cs_x, cs_y, shape)
                if dist < min_distance:
                    min_distance = dist
                    best_lane = lane_id

            # Compute the lane length.
            polyline = lane_shapes[best_lane]
            length = lane_length(polyline)
            # Determine startPos and endPos.
            start_pos = max(0.3 * length, 0)
            end_pos = min(0.7 * length, length)
            if end_pos - start_pos < 1:  # Ensure valid charging station length.
                start_pos = 0
                end_pos = 0.5 * length

            # Randomly choose a power level.
            power = random.choice([50000, 100000, 150000])
            efficiency = 1.0
            # Create a new charging station ID in the desired format.
            cs_new_id = f"cs{i}"
            f_cs.write(f'    <chargingStation id="{cs_new_id}" lane="{best_lane}" startPos="{start_pos:.2f}" endPos="{end_pos:.2f}" power="{power}" efficiency="{efficiency}" chargeInTransit="false"/>\n')
            charging_stations[cs_new_id] = best_lane
        f_cs.write('</additional>\n')

    print(f"Charging stations generated successfully: {cs_file}")
    print(f"Charging stations dictionary: {charging_stations}")

'''
The Charging policy implemetation and dynamic SUMO Simulation using Traci.
'''


if __name__ == "__main__":
    # Start SUMO with the given network file.
    net_file = "city.net.xml"
    traci.start(["sumo", "--net-file", net_file])
    try:
        main()
    finally:
        traci.close()



def get_distance(pos1, pos2):
    return math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])

def safe_float_param(vehID, param):
    try:
        val = traci.vehicle.getParameter(vehID, param)
        return float(val) if val else 0.0
    except Exception as e:
        print(f"[ERROR] Getting parameter {param}: {e}")
        return 0.0

def find_nearest_reachable_charging_station(vehID):
    min_distance = float('inf')
    best_station = None
    best_station_edge = None
    current_pos = traci.vehicle.getPosition(vehID)
    current_edge = traci.vehicle.getRoadID(vehID)

    for station_id in traci.chargingstation.getIDList():
        try:
            lane_id = traci.chargingstation.getLaneID(station_id)
            edge_id = traci.lane.getEdgeID(lane_id)
            xy = traci.simulation.convert2D(edge_id, traci.chargingstation.getStartPos(station_id))
            dist = get_distance(current_pos, xy)
            route = traci.simulation.findRoute(current_edge, edge_id)
            if route.edges and dist < min_distance:
                min_distance = dist
                best_station = station_id
                best_station_edge = edge_id
        except:
            continue

    return best_station, best_station_edge

def compute_charging_duration(vehID, stationID):
    current = safe_float_param(vehID, "device.battery.actualBatteryCapacity")
    maximum = safe_float_param(vehID, "device.battery.maximumBatteryCapacity")
    power = traci.chargingstation.getChargingPower(stationID)
    energy_needed = maximum - current
    duration = int((energy_needed / power) * 3600)
    return duration

def main():
    sumoCmd = ["sumo", "-c", "sumocon.sumocfg"]
    traci.start(sumoCmd)

    EV_TYPES = {"ev_car", "ev_truck", "ev_bus"}
    tracked_vehicles = {}
    step = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        for vehID in traci.vehicle.getIDList():
            vehType = traci.vehicle.getTypeID(vehID)
            if vehType not in EV_TYPES:
                continue

            if vehID not in tracked_vehicles:
                dest = traci.vehicle.getRoute(vehID)[-1]
                tracked_vehicles[vehID] = {
                    "detour_set": False,
                    "charged": False,
                    "original_destination": dest,
                    "cs_info": None
                }

            state = tracked_vehicles[vehID]
            if state["charged"]:
                continue

            soc = safe_float_param(vehID, "device.battery.actualBatteryCapacity") / \
                  safe_float_param(vehID, "device.battery.maximumBatteryCapacity")
            current_edge = traci.vehicle.getRoadID(vehID)

            # STEP 1: Set detour if SoC is low
            if soc < 0.47 and not state["detour_set"]:
                station_id, station_edge = find_nearest_reachable_charging_station(vehID)
                if not station_id:
                    print(f"[WARN] No reachable CS for {vehID}")
                    state["detour_set"] = True
                    continue

                try:
                    rt_to_cs = traci.simulation.findRoute(current_edge, station_edge).edges
                    rt_from_cs = traci.simulation.findRoute(station_edge, current_edge).edges
                    rt_to_dest = traci.simulation.findRoute(current_edge, state["original_destination"]).edges

                    if not rt_to_cs or not rt_from_cs or not rt_to_dest:
                        raise ValueError("One or more route segments are empty")

                    detour_route = rt_to_cs[:-1] + rt_from_cs[:-1] + rt_to_dest
                    traci.vehicle.setRoute(vehID, detour_route)
                    print(f"[INFO] {vehID} detouring via CS {station_id} | SoC: {soc:.2f}")
                    state["detour_set"] = True
                    state["cs_info"] = (station_id, station_edge)

                except (traci.TraCIException, ValueError) as e:
                    print(f"[FAIL] {vehID} detour via {station_id} failed: {e}")
                    state["detour_set"] = True
                    state["charged"] = False

            # STEP 2: Charge when vehicle reaches CS lane
            if state["detour_set"] and not state["charged"] and state["cs_info"]:
                cs_lane = traci.chargingstation.getLaneID(state["cs_info"][0])
                if traci.vehicle.getLaneID(vehID) == cs_lane:
                    soc_reach = safe_float_param(vehID, "device.battery.actualBatteryCapacity") / \
                                safe_float_param(vehID, "device.battery.maximumBatteryCapacity")
                    print(f"[ARRIVED] {vehID} reached CS lane {cs_lane} | SoC: {soc_reach:.2f}")
                    duration = compute_charging_duration(vehID, state["cs_info"][0])
                    try:
                        traci.vehicle.setChargingStationStop(vehID, state["cs_info"][0], duration)
                        print(f"[CHARGE] {vehID} charging at {state['cs_info'][0]} for {duration} sec")

                        state["charged"] = True
                        print(f"[DONE] {vehID} scheduled for full charge.")
                    except traci.TraCIException as e:
                        print(f"[SKIP] Failed to set charging stop for {vehID} | Reason: {e}")
                        state["charged"] = True  # skip further attempts

    print("[SIMULATION COMPLETE]")
    traci.close()

if __name__ == "__main__":
    main()

