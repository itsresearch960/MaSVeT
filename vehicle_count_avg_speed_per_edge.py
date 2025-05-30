import pandas as pd
import matplotlib.pyplot as plt

# --- Parameters ---
csv_file = "edge_congestion_summary.csv"  # input CSV file
M = 60                         # timeslot size in minutes
seconds_per_slot = M * 60      # convert to seconds
TOP_X_EDGES = 150                # Number of top edges to analyze and plot

# --- Load data ---
df = pd.read_csv(csv_file)

# --- Create timeslot column ---
df['timeslot'] = df['time'] // seconds_per_slot

# --- Aggregate by edge and timeslot ---
agg_df = df.groupby(['edge_id', 'timeslot']).agg(
    total_vehicle_count=('vehicle_count', 'sum'),
    avg_speed=('avg_speed', 'mean')
).reset_index()

# --- Get top X edges with highest total vehicle count ---
total_counts = agg_df.groupby('edge_id')['total_vehicle_count'].sum().reset_index()
top_edges = total_counts.sort_values(by='total_vehicle_count', ascending=False)['edge_id'].head(TOP_X_EDGES).tolist()

# --- Filter only top X edges ---
agg_df = agg_df[agg_df['edge_id'].isin(top_edges)]
all_times = list(range(int(agg_df['timeslot'].min()), int(agg_df['timeslot'].max()) + 1))

# --- Prepare subplots ---
fig, axes = plt.subplots(TOP_X_EDGES, 2, figsize=(12, 4 * TOP_X_EDGES), sharex=True)

for i, edge in enumerate(top_edges):
    edge_data = agg_df[agg_df['edge_id'] == edge]

    # Fill missing timeslots with 0s
    edge_data = edge_data.set_index('timeslot').reindex(all_times, fill_value=0).reset_index()
    edge_data['edge_id'] = edge

    # Round values
    ts_list = edge_data['timeslot'].tolist()
    vehicle_counts = [int(v) for v in edge_data['total_vehicle_count']]
    avg_speeds = [round(v, 2) for v in edge_data['avg_speed']]

    # Print values
    print(f"\nEdge: {edge}")
    #print(f"Timeslots: {ts_list}")
    print(f"Vehicle Counts: {vehicle_counts}")
    print(f"Average Speeds: {avg_speeds}")

    # Plot vehicle count
    axes[i][0].plot(ts_list, vehicle_counts, marker='o')
    axes[i][0].set_title(f"Edge {edge} - Vehicle Count")
    axes[i][0].set_ylabel("Count")

    # Plot average speed
    axes[i][1].plot(ts_list, avg_speeds, marker='x', color='orange')
    axes[i][1].set_title(f"Edge {edge} - Average Speed")
    axes[i][1].set_ylabel("Speed (m/s)")

# Label X axis
for ax in axes[:, 0]:
    ax.set_xlabel("Timeslot")
for ax in axes[:, 1]:
    ax.set_xlabel("Timeslot")

plt.tight_layout()
plt.show()
