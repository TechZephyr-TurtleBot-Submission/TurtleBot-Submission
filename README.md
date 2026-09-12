# TurtleBot4 Tag — Problem Statement

**Scenario:** Two TurtleBot4s (`lite` model) share a Gazebo arena. `runner` follows a fixed
patrol loop. Your job is to build `hunter_script.py` — an autonomous pursuit controller that
tracks and closes in on the runner in real time. This doc gets your environment from zero to a
running arena with the runner already patrolling; the hunter's brain is what gets judged.

Stack: **ROS 2 Jazzy + Gazebo Harmonic**, on top of the official
[TurtleBot4 Simulator](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html).

---

## 0. Prerequisites

Install per the official docs — don't deviate from these, version mismatches will bite you later:

- ROS 2 Jazzy: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
- TurtleBot4 Simulator (Gazebo Harmonic + sim packages): https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html

**Verify before going further:**

```bash
lsb_release -a                       # expect Ubuntu 24.04
ros2 --version                       # ROS 2 Jazzy
echo $ROS_DISTRO                     # jazzy
gz sim --version                     # Gazebo Harmonic

# confirm the simulator + nav stack packages actually landed
dpkg -l | grep -E "ros-jazzy-turtlebot4|ros-jazzy-irobot-create|ros-jazzy-nav2|ros-jazzy-slam-toolbox"
ros2 pkg list | grep -E "turtlebot4_navigation|turtlebot4_description|irobot_create_common_bringup"
```

If any of those come back empty, stop and fix the install before continuing — nothing below will
work on a partial install.

## 1. Build the workspace

```bash
mkdir -p ~/turtlebot4_ws/src
cd ~/turtlebot4_ws/src
git clone https://github.com/turtlebot/turtlebot4_simulator.git -b jazzy
cd ~/turtlebot4_ws
rosdep install --from-path src -yi
colcon build --symlink-install
```

## 2. Pull in our modified files — `turtlebot4_ws` stays the one workspace

Clone our repo somewhere temporary — it's a source of files to copy in, not a workspace you'll
work out of:

```bash
cd ~
git clone https://github.com/swarnav2-0/tz_turtlebot4_ws.git
```

`tz_turtlebot4_ws/turtlebot4_simulator` contains the **same four packages** as the stock repo
(`turtlebot4_gz_bringup`, `turtlebot4_gz_gui_plugins`, `turtlebot4_gz_toolbox`,
`turtlebot4_simulator` — identical `package.xml` names), just with the arena world and launch
tweaks added. Same package names in `src/` twice = colcon conflict, so **overwrite the copy
already sitting in `turtlebot4_ws`**:

```bash
rm -rf ~/turtlebot4_ws/src/turtlebot4_simulator
cp -r ~/tz_turtlebot4_ws/turtlebot4_simulator ~/turtlebot4_ws/src/turtlebot4_simulator
```

The repo's top-level assets (map, RViz config, scripts) aren't ROS packages — copy them straight
into `turtlebot4_ws` too, so everything you need lives in one workspace from here on:

```bash
cp ~/tz_turtlebot4_ws/arena_map.yaml        ~/turtlebot4_ws/
cp ~/tz_turtlebot4_ws/arena_map.pgm         ~/turtlebot4_ws/
cp ~/tz_turtlebot4_ws/tz_nav.rviz           ~/turtlebot4_ws/
cp ~/tz_turtlebot4_ws/runner_script.py      ~/turtlebot4_ws/
cp ~/tz_turtlebot4_ws/visualize_centroid.py ~/turtlebot4_ws/
chmod +x ~/turtlebot4_ws/*.py
```

Now rebuild:

```bash
cd ~/turtlebot4_ws
rosdep install --from-path src -yi
colcon build --symlink-install
```

`tz_turtlebot4_ws` has done its job at this point — everything you need going forward lives in
`~/turtlebot4_ws`. You can leave the clone around for future updates (re-copy after a `git pull`)
or delete it; either way, don't build or launch from inside it.

Everything else — Nav2, SLAM Toolbox, `turtlebot4_navigation`, `turtlebot4_description`,
`irobot_create_*` — comes from the apt install in §0 and lives in `/opt/ros/jazzy`. Leave it
alone; our repo never touches it.

Verify the swap built clean:

```bash
ros2 pkg list | grep turtlebot4_gz
```

## 3. `.bashrc`

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "source ~/turtlebot4_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### Discrete GPU — required in **every** terminal, before any Gazebo/RViz command

This does not persist across terminals unless you put it in `.bashrc`. Pick one:

- **Per-terminal (safe default, no side effects on other apps):** run these two lines first, in
  every new terminal, before your `ros2 launch` / `python3` command:
  ```bash
  export __NV_PRIME_RENDER_OFFLOAD=1
  export __GLX_VENDOR_LIBRARY_NAME=nvidia
  ```
- **Permanent (skip repeating it, but affects every terminal on the machine):**
  ```bash
  echo 'export __NV_PRIME_RENDER_OFFLOAD=1' >> ~/.bashrc
  echo 'export __GLX_VENDOR_LIBRARY_NAME=nvidia' >> ~/.bashrc
  source ~/.bashrc
  ```

Every command block below assumes the two exports have either been sourced via `.bashrc` or run
manually first in that terminal — they're written inline too, so copy-paste works either way.

## 4. Path handling — no hardcoded machine paths

Run everything from inside `turtlebot4_ws` and reference the map/RViz config with `$(pwd)`
instead of a hardcoded `/home/<user>/...` path:

```bash
cd ~/turtlebot4_ws
```

Stay in this directory for all the commands below — `$(pwd)/arena_map.yaml` and
`$(pwd)/tz_nav.rviz` resolve correctly from here on any machine, no editing required.

---

## 5. Launch file reference

The official manual covers the base args — here's what our repo adds/relies on:

**`turtlebot4_gz.launch.py`** (top-level: world + first robot)
| Arg | Default | Notes |
|---|---|---|
| `namespace` | `''` | e.g. `runner`, `hunter` |
| `rviz` | `false` | launches RViz2 |
| `world` | `warehouse` | our repo adds `arena` |
| `model` | `standard` | use `lite` — no OAK-D, lighter sim |
| `x y z yaw` | `0.0` | spawn pose |
| `localization` `slam` `nav2` `map` | — | wire these through if you need them at this level; see `turtlebot4_spawn.launch.py` for where they're actually consumed |

**`turtlebot4_spawn.launch.py`** (per-robot: description, spawn, bridge, TF, optional nav stack)
| Arg | Default | Notes |
|---|---|---|
| `use_sim_time` | `true` | keep `true` in sim |
| `localization` | `false` | AMCL against a map |
| `slam` | `false` | SLAM Toolbox instead |
| `nav2` | `false` | planner/controller/behavior servers |

**Worlds** (`turtlebot4_gz_bringup/worlds/`): `depot`, `maze`, `warehouse` are stock; **`arena`**
is ours — this is the tag arena.

**Top-level assets in the repo (not ROS packages, no build needed):**
- `arena_map.yaml` / `arena_map.pgm` — occupancy grid matching `arena.sdf`, for AMCL/Nav2.
- `tz_nav.rviz` — saved RViz config: `map` fixed frame, Nav2 panels, and a `MarkerArray` display
  already wired to `/rviz_visualizer_markers`.
- `runner_script.py` — Nav2 `BasicNavigator(namespace='runner')`, auto-sets initial pose to
  `(0,0,0)`, drives a fixed hexagonal patrol loop via `goToPose()`.
- `visualize_centroid.py` — subscribes to `/runner/odom`, republishes a `MarkerArray` on
  `/rviz_visualizer_markers`: runner centroid, live (x,y) label, 0.5 m ring.

---

## 6. Bring up the arena

### Terminal 1 — world + runner

```bash
cd ~/turtlebot4_ws
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia

ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py \
  model:=lite \
  localization:=true \
  nav2:=true \
  world:=arena \
  map:=$(pwd)/arena_map.yaml \
  namespace:=runner \
  rviz:=true
```

Once Gazebo + RViz are up:
1. In RViz: **File → Open Config** → load `$(pwd)/tz_nav.rviz` (i.e. the full path printed by
   `pwd` in that terminal, or just type it out — it's `~/turtlebot4_ws/tz_nav.rviz`).
2. Use **2D Pose Estimate** to confirm/set the runner's localized pose before trusting anything
   downstream.

### Terminal 2 — centroid visualizer

```bash
cd ~/turtlebot4_ws
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia

python3 visualize_centroid.py
```
In RViz, enable the **MarkerArray** display on `/rviz_visualizer_markers` (already there if you
loaded `tz_nav.rviz`).

### Terminal 3 — spawn the hunter

```bash
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia

ros2 launch turtlebot4_gz_bringup turtlebot4_spawn.launch.py \
  model:=lite \
  x:=3.0 \
  world:=arena \
  namespace:=hunter
```

Confirm it actually landed before moving on:

```bash
ros2 run tf2_ros tf2_echo hunter/odom hunter/base_link
```
And in RViz (same session as Terminal 1), make sure a **TF** or **RobotModel**
(`Description Topic: /hunter/robot_description`) display shows the hunter's frame/mesh next to
the runner's in the arena.

### Terminal 4 — start the runner patrol

```bash
cd ~/turtlebot4_ws
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia

python3 runner_script.py --ros-args -p use_sim_time:=true
```

Wait for the runner's Nav2 lifecycle to report `active` (Terminal 1 logs, or the RViz Nav2 panel
turning green) before starting the hunter.

---

## 7. Your task: `hunter_script.py`

This is what gets evaluated. Build a script that spawns/runs against the `hunter` namespace and
autonomously pursues the `runner` in real time.

**Hard requirements:**
- Namespaces are fixed: **`runner`** and **`hunter`**, exactly as-is — don't rename, alias, or
  add your own namespace. Your script must be written against these two names directly.
- Must run as `python3 hunter_script.py --ros-args -p use_sim_time:=true`, same pattern as
  `runner_script.py`.
- Must operate entirely under the `hunter` namespace — no bare `/cmd_vel`, `/odom`, `/scan`;
  everything goes through `hunter/...` (or a properly namespaced node/`BasicNavigator`).
- Must not touch or modify `runner_script.py`, the arena, or the map — pursuit logic only.
- Track the runner using **live sensor/topic data only** — `/runner/odom` (same source
  `visualize_centroid.py` reads), or the hunter's own `/hunter/scan` (LIDAR) and/or camera feed to
  detect the runner directly, or a fusion of these. Any legitimate topic already published by
  either robot's stack is fair game; reading ground-truth state straight from Gazebo is not.
- **No hardcoded waypoints.** `runner_script.py`'s patrol loop is visible to you in this repo, but
  that visibility is incidental, not a shortcut: `hunter_script.py` must not encode, replicate, or
  anticipate the runner's fixed coordinates in any form (no copy-pasting `waypoint_coords`, no
  precomputed path, no "drive to corner X because that's next on the loop"). The hunter has to
  infer where to go **only** from what it can observe at runtime — the runner's live
  position/odometry (or other sensor data) — exactly as it would have to if the runner's path
  were unknown or changed. If your algorithm would break the moment the runner's waypoints were
  edited, it doesn't satisfy this requirement.

**Open-ended, up to you:**
- Nav2 `BasicNavigator` re-issuing a moving goal vs. a direct `cmd_vel` pursuit controller
  (proportional heading control, pure pursuit, etc.) — either is valid, trade-offs are yours to
  own.
- Which sensing route you lean on: pure `/runner/odom` tracking, LIDAR/camera-based detection off
  the hunter's own sensors, or a mix — all valid as long as it's live data, not precomputed.
- How aggressively you replan/re-goal as the runner moves (goal-chasing lag vs. reactive control
  will be part of what's judged).
- Handling the runner passing through Nav2 recovery behaviors, obstacles, or corners of the arena.

**Sanity checks before you submit:**
```bash
ros2 topic list | grep -E "runner|hunter"     # both namespaces present and separate
ros2 topic hz /runner/odom                     # confirm runner state is actually flowing
ros2 topic echo /hunter/cmd_vel --once         # confirm hunter is actually publishing commands
```

Ping me when you're ready to start building it out — happy to review approach, debug TF/topic
issues, or sanity-check pursuit logic as you go.
