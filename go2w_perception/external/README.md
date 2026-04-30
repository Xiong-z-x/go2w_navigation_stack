# FAST-LIO External Dependency Policy

The repository does not vendor FAST-LIO source.

`tools/prepare_phase2d_fastlio_external.sh` prepares a patched external workspace
from the pinned refs in `fast_lio_ros2.lock.env`. By default, generated source
and build products are kept under the ignored repository-local cache:

```text
.go2w_external/src/FAST_LIO_ROS2
.go2w_external/workspaces/fast_lio_ros2
```

Override paths only through environment variables:

```bash
GO2W_FASTLIO_SRC=/path/to/FAST_LIO_ROS2
GO2W_FASTLIO_WS=/path/to/fast_lio_ws
```

Do not commit downloaded external source or build output.
