import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import math

def parse_emission_file(file_path):
    emission_data = []

    tree = ET.parse(file_path)
    root = tree.getroot()

    for timestep in root.findall("timestep"):
        time = float(timestep.get("time"))
        sum_co2 = sum_nox = sum_pmx = sum_fuel = sum_elec = 0.0

        for vehicle in timestep.findall("vehicle"):
            sum_co2 += float(vehicle.get("CO2", 0.0))
            sum_nox += float(vehicle.get("NOx", 0.0))
            sum_pmx += float(vehicle.get("PMx", 0.0))
            sum_fuel += float(vehicle.get("fuel", 0.0))
            sum_elec += float(vehicle.get("electricity", 0.0))

        emission_data.append((time, sum_co2, sum_nox, sum_pmx, sum_fuel, sum_elec))

    return emission_data

def aggregate_by_timeslot(emission_data, slot_minutes=10):
    slot_seconds = slot_minutes * 60
    slots = {}

    for entry in emission_data:
        time, co2, nox, pmx, fuel, elec = entry
        slot_index = int(time // slot_seconds)

        if slot_index not in slots:
            slots[slot_index] = [0.0, 0.0, 0.0, 0.0, 0.0]
        slots[slot_index][0] += co2
        slots[slot_index][1] += nox
        slots[slot_index][2] += pmx
        slots[slot_index][3] += fuel
        slots[slot_index][4] += elec

    sorted_slots = sorted(slots.items())
    timeslot_labels = [f"TS{i+1}" for i, _ in sorted_slots]
    aggregated = list(zip(*[values for _, values in sorted_slots]))

    return timeslot_labels, aggregated  # (list of str), ([co2 list], [nox list], ...)

def plot_aggregated_metric(timeslot_labels, values, ylabel, title, color):
    print(f"\n{title} (per timeslot):")
    print(values)

    plt.figure(figsize=(10, 5))
    plt.plot(timeslot_labels, values, marker='o', color=color)
    plt.xlabel("Timeslot")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- MAIN RUN ---
if __name__ == "__main__":
    emission_file = "emission.xml"  # Replace with your file path
    slot_minutes = 60               # Define your timeslot size

    data = parse_emission_file(emission_file)
    labels, (co2, nox, pmx, fuel, elec) = aggregate_by_timeslot(data, slot_minutes)

    plot_aggregated_metric(labels, co2, "CO₂ (g)", f"CO₂ Emissions per {slot_minutes}-min Slot", "green")
    plot_aggregated_metric(labels, nox, "NOₓ (g)", f"NOₓ Emissions per {slot_minutes}-min Slot", "blue")
    plot_aggregated_metric(labels, pmx, "PMₓ (g)", f"PMₓ Emissions per {slot_minutes}-min Slot", "red")
    plot_aggregated_metric(labels, fuel, "Fuel Used (ml)", f"Fuel Use per {slot_minutes}-min Slot", "orange")
    plot_aggregated_metric(labels, elec, "Electricity (Wh)", f"Electricity Usage per {slot_minutes}-min Slot", "purple")
