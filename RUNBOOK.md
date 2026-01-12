# MCP-Robot v3.0 Runbook

## 🔌 Architecture Overview
MCP-Robot v3.0 is a **Deterministic Robotics Control Stack**. It ensures that for a given input snapshot (Perception + State), the resulting plan and execution decisions are bit-identical across runs.

## 🕹️ Modes of Operation

### 1. SIM Mode (Default)
- **Digital Twin**: Uses `KinematicSimulator` for state tracking.
- **Determinism**: Perfect. Uses tick-based updates. No wall-clock dependencies.
- **Usage**: Planning development, safety verification testing, regression tests.

### 2. HARDWARE Mode
- **Real ROS2**: Connects to `rclpy` and sends `FollowJointTrajectory` goals.
- **Connectivity**: Requires ROS2 Humble/Foxy.
- **Feedback**: Inherently non-deterministic due to real-world physics and network jitter.

## 🚀 Getting Started

### Installation
```bash
pip install -e .
```

### Running Tests
Verify the determinism guarantees:
```bash
pytest tests/test_determinism.py
```

### Running the Benchmark
Evaluate the VLA's performance and safety logic:
```bash
python scripts/benchmark_runner.py
```

## 🛠️ Key Primitives

### `DeterminismConfig`
Found in `mcp_robot/runtime/determinism.py`. Controls the global seed and rounding precision.

### `Snapshots`
Found in `mcp_robot/contracts/schemas.py`. Planning now requires a `RobotStateSnapshot` and `PerceptionSnapshot`. Use these to "freeze" the world before calling the VLA.

## 🛡️ Safety & Continuity
- **Anti-Teleportation**: All trajectories must start within 0.1 rad of the current state.
- **Safety Chip**: Deterministic ZMP and Force limits are checked in Tier 5.
- **Idempotency**: Executing the same (PlanID, ChunkID) twice will return a cached result.
