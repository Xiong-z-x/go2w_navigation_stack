# Gazebo GPU Re-baseline

## Purpose
Record the 2026-04-27 GPU re-baseline for the current WSL2 + ROS 2 Humble +
Gazebo Fortress environment.

This document does not change the accepted runtime baseline. The accepted
Gazebo path remains software rendering with `use_gpu:=false`.

## Scope

Allowed scope:

- confirm NVIDIA / CUDA visibility
- confirm WSLg GLX / D3D12 OpenGL capability
- test Gazebo Fortress server / headless rendering
- test `go2w_sim` Gazebo sensors/rendering with `use_gpu:=true`
- test Gazebo GUI with `use_gpu:=true`
- test RViz standalone OpenGL startup

Out of scope:

- changing `go2w_sim` default launch arguments
- changing Phase 2 FAST-LIO2 integration files
- adding Nav2, routing, mission, or staircase behavior
- changing the Fortress-only baseline to Garden / Harmonic

## Environment Evidence

### NVIDIA Device

Command:

```bash
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv,noheader
```

Observed result:

```text
NVIDIA GeForce RTX 3050 Laptop GPU, 595.97, 4096 MiB, 28 MiB
```

Interpretation:

- WSL can see the NVIDIA GPU.
- CUDA-capable device visibility is present.
- This does not prove Gazebo Fortress/Ogre2 rendering compatibility.

### GLX / D3D12

Command:

```bash
glxinfo -B
```

Observed result:

```text
direct rendering: Yes
Device: D3D12 (NVIDIA GeForce RTX 3050 Laptop GPU)
Accelerated: yes
OpenGL core profile version string: 4.2 (Core Profile) Mesa 23.2.1-1ubuntu3.1~22.04.3
OpenGL renderer string: D3D12 (NVIDIA GeForce RTX 3050 Laptop GPU)
```

Interpretation:

- WSLg GLX is using the D3D12 NVIDIA path.
- RViz can use this OpenGL path.
- Gazebo Fortress/Ogre2 still needs separate validation.

## Test Matrix

| Layer | Command | Result | Interpretation |
| --- | --- | --- | --- |
| Empty Gazebo server/headless rendering | `LIBGL_ALWAYS_SOFTWARE=0 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA MESA_GL_VERSION_OVERRIDE=4.2 MESA_GLSL_VERSION_OVERRIDE=420 timeout 20s ign gazebo -r -s --headless-rendering install/go2w_sim/share/go2w_sim/worlds/empty_world.sdf --force-version 6` | Ran until `timeout` with no observed Ogre2 crash | Empty world server startup is not the crash point |
| `go2w_sim` headless sensors/rendering | `LIBGL_ALWAYS_SOFTWARE=0 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA MESA_GL_VERSION_OVERRIDE=4.2 MESA_GLSL_VERSION_OVERRIDE=420 timeout 40s ros2 launch go2w_sim sim.launch.py use_gpu:=true headless:=true launch_rviz:=false` | `ign gazebo-6` aborted with `Ogre::UnimplementedException` in `GL3PlusTextureGpu::copyTo`; stack included `libignition-gazebo-sensors-system.so` `SensorsPrivate::RenderThread()` | Gazebo sensors/rendering GPU path is not stable |
| `go2w_sim` GUI + sensors/rendering | `LIBGL_ALWAYS_SOFTWARE=0 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA MESA_GL_VERSION_OVERRIDE=4.2 MESA_GLSL_VERSION_OVERRIDE=420 timeout 40s ros2 launch go2w_sim sim.launch.py use_gpu:=true headless:=false launch_rviz:=false` | Reproduced `Ogre::UnimplementedException` in `GL3PlusTextureGpu::copyTo`; GUI and sensors/rendering paths both emitted Ogre2 abort traces | Gazebo GUI GPU path is not stable |
| RViz standalone | `LIBGL_ALWAYS_SOFTWARE=0 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA timeout 20s rviz2 -d go2w_description/rviz/go2w_phase1.rviz` | RViz reported `OpenGl version: 4.2 (GLSL 4.2)` and ran until `timeout` | RViz may use the WSLg/NVIDIA OpenGL path independently of Gazebo |

## Decision

Do not introduce `use_gpu:=true` into the accepted Gazebo baseline.

The current accepted project baseline remains:

```bash
ros2 launch go2w_sim sim.launch.py use_gpu:=false
```

Rationale:

- GPU and GLX are visible from WSL.
- RViz can initialize OpenGL 4.2 on the D3D12 NVIDIA path.
- `go2w_sim use_gpu:=true` fails in Gazebo Fortress/Ogre2 rendering, including
  the headless sensors/rendering path.
- The failure is therefore narrower than "GPU unavailable" and broader than
  "GUI only".

## Allowed GPU Usage After This Re-baseline

Allowed:

- RViz may use the current WSLg/NVIDIA GLX path.
- Future CUDA workloads, FAST-LIO acceleration, or ML workloads may use the GPU
  if validated independently.
- Gazebo GPU rendering may be re-tested only as a separate environment task.

Not allowed as current default:

- enabling `use_gpu:=true` by default
- treating Gazebo Fortress GPU rendering as Phase 1 or Phase 2 acceptance
- replacing the Fortress-only baseline with Garden / Harmonic to chase GPU
  rendering without explicit re-baseline approval

## Required Regression

After GPU experiments, re-run the accepted software-rendering launch check:

```bash
./tools/cleanup_sim_runtime.sh
./tools/verify_go2w_sim_launch.sh
```

The GPU re-baseline is valid only if the accepted `use_gpu:=false` path still
passes after cleanup.
