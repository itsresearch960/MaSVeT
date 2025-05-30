import xml.etree.ElementTree as ET
from collections import defaultdict
import math
import matplotlib.pyplot as plt

def parse_battery_energy_per_timeslot(xml_file, minutes_per_slot=10):
    SECONDS_PER_SLOT = minutes_per_slot * 60
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # cs_id → timeslot → total energy drawn
    cs_timeslot_energy = defaultdict(lambda: defaultdict(float))

    for timestep in root.findall('timestep'):
        time = float(timestep.get("time"))
        timeslot = int(time // SECONDS_PER_SLOT)

        for vehicle in timestep.findall('vehicle'):
            cs_id = vehicle.get("chargingStationId", "NULL")
            energy_charged = float(vehicle.get("energyCharged", 0.0))
            if cs_id != "NULL":
                cs_timeslot_energy[cs_id][timeslot] += energy_charged

    return cs_timeslot_energy, SECONDS_PER_SLOT

def plot_energy_drawn_per_timeslot(cs_timeslot_energy, seconds_per_slot):
    max_slot = max(max(ts_data.keys()) for ts_data in cs_timeslot_energy.values())

    for cs_id, ts_data in sorted(cs_timeslot_energy.items()):
        slot_indices = list(range(max_slot + 1))
        energy_values = [round(ts_data.get(slot, 0.0), 2) for slot in slot_indices]
        slot_labels = [f"TS{slot + 1}" for slot in slot_indices]

        print(f"\nCharging Station: {cs_id}")
        print(f"Energy per Timeslot (Wh): {energy_values}")

        plt.figure(figsize=(9, 5))
        plt.plot(slot_labels, energy_values, marker='o')
        plt.xlabel(f"Timeslot (every {seconds_per_slot // 60} minutes)")
        plt.ylabel("Total Energy Charged (Wh)")
        plt.title(f"Charging Pattern - {cs_id}")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

# --- RUN ---

xml_file = "battery_outputZ.xml"  # Replace as needed
slot_duration_mins = 60          # You can change this value

cs_ts_energy, sec_per_slot = parse_battery_energy_per_timeslot(xml_file, slot_duration_mins)
plot_energy_drawn_per_timeslot(cs_ts_energy, sec_per_slot)
