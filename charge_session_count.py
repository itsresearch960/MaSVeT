import xml.etree.ElementTree as ET
from collections import defaultdict
import matplotlib.pyplot as plt

def parse_charging_sessions(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    sessions = defaultdict(list)  # cs_id -> list of (start_time, end_time)
    active_sessions = {}  # vid -> (cs_id, start_time)

    for timestep in root.findall('timestep'):
        time = float(timestep.get("time"))
        for vehicle in timestep.findall('vehicle'):
            vid = vehicle.get("id")
            cs_id = vehicle.get("chargingStationId", "NULL")
            energy = float(vehicle.get("energyCharged", 0))

            if cs_id != "NULL" and energy > 0:
                if vid not in active_sessions:
                    active_sessions[vid] = (cs_id, time)
            else:
                if vid in active_sessions:
                    prev_cs, start = active_sessions.pop(vid)
                    sessions[prev_cs].append((start, time))

    # Close any remaining active sessions
    max_time = float(root.findall('timestep')[-1].get("time"))
    for vid, (cs_id, start) in active_sessions.items():
        sessions[cs_id].append((start, max_time))

    return sessions

def aggregate_sessions_by_timeslot(sessions, slot_length_sec):
    aggregated = defaultdict(lambda: defaultdict(int))  # cs_id -> slot -> count

    for cs_id, cs_sessions in sessions.items():
        for start, end in cs_sessions:
            slot_start = int(start // slot_length_sec)
            slot_end = int(end // slot_length_sec)
            for slot in range(slot_start, slot_end + 1):
                aggregated[cs_id][slot] += 1

    return aggregated

def plot_congestion(aggregated_data, slot_length_sec):
    for cs_id, slots in aggregated_data.items():
        timeslots = sorted(slots.keys())
        values = [slots[t] for t in timeslots]

        # --- Print as list ---
        print(f"\nCharging Station: {cs_id}")
        print(f"Timeslot indices: {[f'TS{t}' for t in timeslots]}")
        print(f"Session counts  : {values}")

        # --- Plot ---
        plt.figure(figsize=(8, 4))
        plt.bar(timeslots, values)
        plt.title(f"Charging Sessions per Timeslot\nStation: {cs_id}")
        plt.xlabel(f"Timeslot (each = {slot_length_sec//60} min)")
        plt.ylabel("Charging Sessions")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.show()

# === USER CONFIGURATION ===
xml_file = "battery_outputZ.xml"   # Path to your XML
slot_length_minutes = 60          # Timeslot size in minutes
# ===========================

slot_length_sec = slot_length_minutes * 60
sessions = parse_charging_sessions(xml_file)
aggregated = aggregate_sessions_by_timeslot(sessions, slot_length_sec)
plot_congestion(aggregated, slot_length_sec)
