import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as colors

def extract_vehicle_positions(fcd_file):
    x_coords = []
    y_coords = []

    tree = ET.parse(fcd_file)
    root = tree.getroot()

    for timestep in root.findall('timestep'):
        for vehicle in timestep.findall('vehicle'):
            x = float(vehicle.get("x"))
            y = float(vehicle.get("y"))
            x_coords.append(x)
            y_coords.append(y)

    return x_coords, y_coords

def plot_dense_heatmap(x_coords, y_coords, bins=100, threshold_ratio=0.01):
    heatmap, xedges, yedges = np.histogram2d(x_coords, y_coords, bins=bins)

    # Apply threshold mask
    threshold = heatmap.max() * threshold_ratio
    heatmap[heatmap < threshold] = np.nan  # Mask sparse regions

    # Mask NaNs and assign custom color for them
    masked_heatmap = np.ma.masked_invalid(heatmap)
    cmap = cm.get_cmap('hot').copy()
    cmap.set_bad(color='lightgrey')  # Color for NaNs (below threshold)

    # Plot
    plt.figure(figsize=(10, 8))
    im = plt.imshow(
        masked_heatmap.T,
        origin='lower',
        cmap=cmap,
        extent=[min(x_coords), max(x_coords), min(y_coords), max(y_coords)],
        aspect='auto'
    )

    # Colorbar
    cbar = plt.colorbar(im)
    cbar.set_label('Vehicle Density', fontsize=20)
    cbar.ax.tick_params(labelsize=20)

    # Labels and title
    plt.title("Dense Areas of Vehicle Distribution", fontsize=20)
    plt.xlabel("X Position (m)", fontsize=20)
    plt.ylabel("Y Position (m)", fontsize=20)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.tight_layout()
    plt.show()

# --- Run ---
fcd_file = "fcdZ.xml"
x_coords, y_coords = extract_vehicle_positions(fcd_file)
plot_dense_heatmap(x_coords, y_coords, bins=20, threshold_ratio=0.0)
