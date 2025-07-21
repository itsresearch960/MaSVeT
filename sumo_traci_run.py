import traci
import math

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
