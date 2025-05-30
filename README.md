# MaSVeT: Macroscopic Synthetic Vehicular Traffic Generator

MaSVeT is a modular and GUI-based synthetic vehicle trajectory generator tailored for large-scale macroscopic traffic modeling. It supports urban mobility simulation over multiple days and across heterogeneous vehicle types with charging and emission modeling.

---

##  Features

- Interactive GUI for region annotation (Residential, Commercial)
- Statistical trip generation using population, density, ownership, and inter-region flow distributions
- Support for Electric Vehicles (EV) and Internal Combustion Engine Vehicles (ICEV)
- SUMO integration: trip generation, routing, simulation, and data collection
- Vehicle-level output for charge, emission, and spatial movement
- Post-processing tools for speed, heatmap, emissions, and charging metrics

---

##  Supported Vehicle Types

### Electric Vehicles (EVs)

| Type     | Max Speed | Notes                                                             |
|----------|-----------|-------------------------------------------------------------------|
| ev_car   | 80 km/h   | Includes battery, air/roll resistance, efficiency, charging curve |
| ev_truck | 60 km/h   | Modeled for energy-heavy transport                               |
| ev_bus   | 50 km/h   | Public mobility scenarios, includes regenerative braking         |

### Internal Combustion Engine Vehicles (ICEVs)

| Type       | Max Speed | Notes                                                      |
|------------|-----------|------------------------------------------------------------|
| icev_car   | 80 km/h   | Includes emissions: CO, NOx, PM                            |
| icev_truck | 60 km/h   | Heavy-duty emissions model                                |
| icev_bus   | 50 km/h   | High mass, realistic acceleration and braking             |

> Note: You can modify vehicle parameters (e.g., battery capacity, efficiency) in the code for custom calibration.

---

##  Repository Structure

| File                                | Description                                                              |
|-------------------------------------|--------------------------------------------------------------------------|
| preprocessing_masvet.py            | Downloads OSM, converts to SUMO `.net.xml`, extracts charging stations   |
| tripgenerator.py                   | GUI-based synthetic trip generator with user-defined regions             |
| route_generator.py                 | Generates SUMO-compatible route files from generated trips               |
| sumo_traci_run.py                  | Runs SUMO using TraCI, collects emission and charging data               |
| trace_stat.py                      | Summarizes trip traces, trip count, average duration                     |
| vehicle_trace_density.py           | Creates heatmaps of vehicle presence across the city                     |
| vehicle_count_avg_speed_per_edge.py| Calculates average speed and flow per road segment                       |
| charge_session_count.py            | Counts EV charging sessions per station                                  |
| cs_charge_drawn.py                 | Computes total energy drawn per station                                  |
| emission_track.py                  | Tracks pollutants: CO2, NOx, PM from SUMO output                         |

---

## What Are PRC and PCR?

- **PRC (Residential → Commercial Rate):**  
  Describes the percentage of vehicles moving **from residential to commercial zones** in each time slot. Modeled using a Normal distribution:  
  `PRC_t ~ N(mu_PRC_t, sigma_PRC_t)`

- **PCR (Commercial → Residential Rate):**  
  Describes the return percentage **from commercial to residential zones**, also sampled from a Normal distribution:  
  `PCR_t ~ N(mu_PCR_t, sigma_PCR_t)`

> These rates control **city-wide mobility directionality** and are key parameters in MaSVeT's stochastic traffic modeling.

---
## Tested Operating System

Ubuntu **22.04.5 LTS** or higher is recommended for full compatibility with SUMO, GUI-based inputs, and all Python dependencies.

##  Setup Instructions

### 1. Install SUMO (Linux)
```
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-doc
```

### 2. Install Python Dependencies
```
pip install pyproj sumolib matplotlib numpy pillow lxml
```

---

## How to Use MaSVeT

### Step 1: Run Preprocessing
```
python preprocessing_masvet.py
```

### Step 2: Generate Trips
```
python tripgenerator.py
```

### Step 3: Route and Simulate
```
python route_generator.py
python sumo_traci_run.py
```

> **Charging Logic**: When an EV’s battery falls below a threshold, it detours to the nearest station and charges to full.  
> MaSVeT allows easy customization of charging strategies.

### Step 4: Analyze Output
```
python trace_stat.py
python vehicle_trace_density.py
python charge_session_count.py
python cs_charge_drawn.py
python emission_track.py
```

---


