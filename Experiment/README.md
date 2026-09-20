# ATOM Experimental Programs and Data

This directory contains the final experimental programs, measurements, and analysis scripts used in the ATOM paper. Earlier trials and superseded program variants were intentionally excluded.

## Directory overview

| Directory | Paper experiment | Included material |
|---|---|---|
| `01_Trajectory_Tracking` | Single-robot circular and square tracking | MicroBlocks program, UDP acquisition and analysis scripts, final raw/processed trajectories, metrics, and summary |
| `02_ESP_NOW_Communication` | Broadcast reliability and bidirectional round-trip tests | MicroBlocks programs, raw trial counts, paper summaries, and plotting script |
| `03_Distributed_Collision_Avoidance` | Five-robot collision avoidance | Robot and remote-control programs, layout plotting script, and final results |
| `04_Dynamic_Voronoi_Coverage` | Dynamic area coverage | Unified MicroBlocks program and Voronoi visualization script |
| `05_Cooperative_Transport` | Five-robot cooperative transport | Robot and remote-control programs and final success-rate data |
| `06_Platform_Speed` | Maximum translational and angular speed | Test program and reported measurements |

MicroBlocks project files use the `.ubp` extension. Python dependencies for trajectory processing are listed in the corresponding `requirements.txt` files.

## 1. Trajectory tracking

The final datasets are:

- Circle: `omnistamp_circle_20260914_192932`, centered at `(300, 300)` with a radius of 150 units.
- Square: `omnistamp_circle_20260914_193513`, with vertices `(150,150)`, `(450,150)`, `(450,450)`, and `(150,450)`.

Raw UDP captures, processed coordinates, metrics, and plots are stored under `data/circle` and `data/square`. The consolidated paper values, including the separately recorded heading RMSE, are in `data/trajectory_results.csv`. One map unit is approximately 1.36 mm.

From this directory, the publication-style combined plot can be regenerated with:

```bash
python 01_Trajectory_Tracking/scripts/plot_combined_trajectories.py
```

The output is written to `01_Trajectory_Tracking/figures`.

## 2. ESP-NOW communication

The broadcast test uses two to five robots. Each robot transmits 1000 fixed-length 10-byte packets at a nominal rate of 25 Hz in each of four trials. `broadcast_raw.csv` stores every directed sender-receiver count, and `broadcast_summary.csv` contains the values reported in the paper.

The round-trip test uses two robots and five trials of 100 attempts at each retained message length. `rtt_raw.csv` records the number of successful replies and their total elapsed time. `mean_rtt_ms` is the total time divided by the number of successful replies; unanswered requests are counted as failures. `rtt_summary.csv` contains the six message lengths reported in the paper.

The communication CSV files were transcribed from the final experiment records because the MicroBlocks test programs displayed and accumulated counts directly rather than writing a host-side packet log.

## 3. Distributed collision avoidance

The final program stores the pentagram-crossing, central-crossing, and multi-path-convergence start-goal layouts. Each layout was tested 20 times with five robots. All robots reached their goals in all 60 trials; `collision_avoidance_results.csv` reports collision-free completion counts and mean completion times over collision-free trials.

## 4. Dynamic Voronoi coverage

`Voronoi_Coverage.ubp` is the common program used by all robots. Robots exchange their IDs and positions, recompute the active set as robots are added or removed, and move toward locally evaluated Voronoi centroids. `overlay_voronoi.py` overlays Voronoi cells on experimental images for visualization.

## 5. Cooperative transport

Five robots transport a 50 g, 3-D-printed regular pentagonal prism along the route defined by `(120,120)`, `(480,120)`, `(480,480)`, and `(120,480)`. All 20 final trials succeeded. The program files and the corresponding summary are provided in this directory.

## 6. Platform speed

The speed test used five unloaded prototypes with a regulated 5 V motor-driver supply. The reported peak translational and angular speeds are stored in `speed_results.csv`.

## Data provenance

Files copied from the development directory retain their original names except for spaces removed from the two RTT program filenames. Newly created summary CSV files reproduce the final values used in the manuscript. No superseded run data, Python caches, or unrelated experiments are included.

