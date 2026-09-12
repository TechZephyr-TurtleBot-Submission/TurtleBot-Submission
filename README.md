# TurtleBot4 Pursuit & Evasion Challenge — Problem Statement

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

**`tz_nav.rviz` only has displays configured for `runner` — the hunter isn't in it.** Add these
manually in the same RViz window (once, per session) so you can actually see the second robot:

1. **Displays panel → Add → By display type → `RobotModel`**
   - `Description Topic` → `/hunter/robot_description`
   - This renders the hunter's mesh at its live TF pose.
2. **Displays panel → Add → By display type → `TF`**
   - Enable this if it isn't already on globally — it'll pick up `hunter/base_link`,
     `hunter/odom`, etc. automatically once the hunter is publishing. Optionally set
     **Filter (whitelist)** to `hunter/.*` if the tree gets too busy with both robots' frames.
   - Confirm `hunter/base_link` and `hunter/odom` appear under the TF tree in the Displays panel.
3. **(Optional) Displays panel → Add → By topic → `/hunter/scan` → `LaserScan`**
   - Useful once you start writing `hunter_script.py` against LiDAR data — lets you visually
     confirm the hunter is actually seeing the runner.
4. **(Optional) Displays panel → Add → By topic → `/hunter/oakd/rgb/image_raw` → `Image`**
   - Only if you're running `model:=standard` for the hunter and plan to use camera-based
     tracking; `lite` has no OAK-D camera.
5. Once set up, **File → Save Config As** and overwrite `tz_nav.rviz` (or save as your own copy)
   so you don't have to redo this every session.

You should now see both robots' meshes/frames side by side in the arena before moving on to
Terminal 4.

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

---

## 8. Submission requirements

This challenge is being run as **Round 1 of the Tech Zephyr 4.0 TurtleBot Pursuit & Evasion
Challenge**. This section summarizes what your submission needs to contain, on top of the
technical rulebook. If anything here conflicts with the official rulebook, the rulebook wins.

### Timeline
- **Release (12th):** the arena and a sample Runner node are released. Clone it and get it
  running on your own system exactly as this guide describes.
- **Testing window:** you get **2 weeks** to build and test your Catcher (`hunter_script.py`) —
  and, per the rulebook, your own Runner algorithm too — against the released arena.
- **Submission:** you submit your **modified workspace repo**. Once submitted, **no further
  changes are allowed** — any change made to the repo after submission may lead to
  disqualification. Make sure what you push is what you intend to be judged on.
  
### Team Information

| Field                     | Details                       |
| ------------------------- | ----------------------------- |
| **Team Name**             | `Your Team Name`              |
| **Team Leader**           | `Name`                        |
| **Team Members**          | `Name 1, Name 2, Name 3, ...` |
| **College / Institution** | `College Name`                |

### Repository
- Private GitHub repo, named `TechZephyr_TurtleBot<your_team_name>`.
- Must contain:
  - Complete Catcher (`hunter_script.py`) source.
  - Complete Runner algorithm source.
  - All launch/config/package files needed to actually run your solution — assume the evaluator
    starts from a clean `turtlebot4_ws` set up per this guide and only adds your repo's contents.
  - A structured `README.md` covering your approach, algorithm, dependencies, setup, and exact
    run instructions. Write it so someone who has only read *this* setup guide can get your
    solution running without asking you anything.
- **Only TurtleBot4 `lite` is accepted.** Don't submit a solution built or tuned against
  `standard` — namespaces stay `runner`/`hunter` as covered above, and the model stays `lite`.

### RViz / visual proof requirements
Your simulation run must be visually verifiable in RViz, not just claimed in the video's audio:
- **Runner:** must show the `visualize_centroid.py` marker set — centroid sphere **and** the
  0.5 m green ring — exactly as set up in §6 with `tz_nav.rviz`. Don't disable or replace this.
- **Hunter:** must have, at minimum, a visible centroid marker and its base_link axes/TF (per the
  RViz setup block in §6, Terminal 3) — so the evaluator can see it moving and where it thinks it
  is, not just watch the Gazebo viewport.
- **Capture check:** the hunter's centroid (or `hunter/base_link` origin) must visibly sit inside
  the runner's green 0.5 m ring, continuously, for at least 1 second, for the capture to count —
  this must be clearly visible in RViz in your recording, not just inferred from Gazebo.
- **If you use additional sensors** (camera, LIDAR-based detection, etc.) for the Catcher's
  perception, that sensor's output must also be visible in RViz during the recording — e.g. add
  the raw or an annotated image topic (`.../image_raw`, or your own `.../annotated_image` if
  you're overlaying detections) as an `Image` display, or the `LaserScan` display for LIDAR. If
  it's part of how your Catcher perceives the Runner, it needs to be shown, not just used
  internally.

### Demonstration video
Must show, with live timestamps visible throughout:
- Launch of the arena and spawning of both TurtleBots.
- Start of the match.
- The hunter's centroid entering and remaining within the runner's 0.5 m radius for at least
  1 second (the capture moment) — clearly visible in RViz per the requirements above.
- Any sensor visualizations you're relying on (per the point above), so the evaluator can see
  what your Catcher is actually perceiving, not just how it moves.
- Recommended structure and duration are in the rulebook (team intro, Catcher strategy, Runner
  strategy, brief architecture explanation, Gazebo demo, capture result). Make sure the video is
  accessible to organizers (correct sharing permissions) before you submit.

