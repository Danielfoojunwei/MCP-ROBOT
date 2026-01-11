# 🤖 MCP-Robot v2.0: Production-Grade VLA Control Stack

> **A Neural-Symbolic Architecture for Reliable Robotic Control via Model Context Protocol (MCP)**

![Status](https://img.shields.io/badge/Status-Production--Ready-green) ![ROS2](https://img.shields.io/badge/ROS2-Humble-blue) ![MCP](https://img.shields.io/badge/MCP-Verifiable-orange) ![Safety](https://img.shields.io/badge/Safety-ISO_10218-red)

**MCP-Robot** is a rigorous, contract-driven control stack that enables Large Language Models (LLMs) to operate physical robots safely. Unlike simple "text-to-cmd_vel" demos, MCP-Robot implements a **7-Tier Neural-Symbolic Pipeline** that enforces strict physical grounding, safety verification, and operational contracts before any motor moves.

---

## 🏗️ The Problem
Connecting LLMs directly to robots is dangerous. LLMs "hallucinate" actions (e.g., asking a robot to move through a table) and lack physical intuition (e.g., ignoring velocity limits or stability constraints).

**MCP-Robot v2.0 solves this by strictly separating "Cognition" from "Execution" via strong contracts.**

---

## 🏛️ v2.0 System Architecture

The system operates as a **Unidirectional Data Flow** pipeline. Data flows down (Intent -> Motor Signal), and State flows up (Sensors -> Verification).

```mermaid
graph TD
    User["User Instruction"] --> T1[Tier 1: Decomposition]
    T1 --> T2[Tier 2: Planning (ACT)]
    T2 --> T3[Tier 3: Visio-Tactile Encoding]
    T3 --> T4[Tier 4: Universal Action Mapping]
    
    subgraph "Safety Critical Zone"
        T4 -->|JointTrajectoryChunk Object| T5[Tier 5: Verification Engine]
        State[Kinematic Simulator/Telemetry] -->|State Vector| T5
        T5 -- Certified? --> T6[Tier 6: ROS2 Adapter]
        T5 -- Rejected? --> Alert["HALT & ALERT"]
    end
    
    T6 -->|Hardware/Sim| Robot[Physical Robot / Sim]
    Robot -->|Feedback| T7[Tier 7: Learning Loop]
```

### The 7 Tiers of Control

| Tier | Component | Function | Status |
| :--- | :--- | :--- | :--- |
| **I** | **Task Decomposer** | Breaks "Clean table" into atomic subgoals. | ✅ ALOHA |
| **II** | **Long-Horizon Planner** | Sequences actions based on visual context. | ✅ ACT |
| **III** | **Visio-Tactile Encoder** | Augments actions with grip force/slip parameters. | ✅ Validated |
| **IV** | **Universal Mapper** | **[NEW] Grounded Generation.** Interpolates trajectories from current robot state to prevent teleportation. | ✅ **Production** |
| **V** | **Verification Engine** | **[NEW] The "Safety Chip".** Deterministic physics checks (ZMP, Force, Continuity). | ✅ **ISO-Aligned** |
| **VI** | **ROS2 Adapter** | **[NEW] Production Bridge.** Manages QoS, Reconnection, and Type Safety. | ✅ **Hybrid (Sim/Real)** |
| **VII** | **Learning Loop** | Self-correction via hindsight relabeling. | 🚧 Beta |

---

## 🛡️ Core Innovations

### 1. Strict Contract Architecture
We have abolished loose dictionary passing. All inter-tier communication is enforced via strict **Pydantic Models** (`mcp_robot/contracts/schemas.py`).
- **`JointTrajectoryChunk`**: The immutable currency of the pipeline. Contains `joint_names`, `waypoints`, `duration`, and `max_force_est`.
- **Why it matters**: A planner cannot "sneak" an unsafe command past the verifier by malforming data. If it doesn't fit the schema, it crashes safely before execution.

### 2. Grounded Planning (Anti-Teleportation)
LLMs often assume a robot can "jump" to a target pose.
- **Solution**: The **Universal Mapper** (Tier 4) reads the *actual* robot state from the `KinematicSimulator`.
- **Implementation**: It generates a trajectory that mathematically *must* start at the robot's current joint angles and interpolate to the target.
- **Result**: Zero "continuity errors" in execution. The robot moves fluidly from A to B.

### 3. The "Safety Chip" (Tier 5)
A deterministic `PhysicsEngine` that runs locally (no ML allowed). It validates every chunk against:
- **Continuity**: Does Trajectory[0] == CurrentState? (Tolerance: 0.5 rad)
- **Joint Limits**: Are we inside the physical range? (Configurable per Robot Profile)
- **Dynamics**: Does the estimated ZMP (Zero Moment Point) remain stable given the velocity payload?
- **Force**: Does the intent exceed safety thresholds (e.g., >100N)?

### 4. Production ROS2 Connectivity
We implement a `ROS2Adapter` that mimics `wise-vision` and `nav2` patterns:
- **Hybrid Mode**: Toggles between `HARDWARE` (rclpy) and `SIM` (Digital Twin) automatically.
- **Production QoS**: Uses `RELIABLE` for commands and `BEST_EFFORT` for heavy telemetry, ensuring network robustness.
- **Type Safety**: strict wrapping of ROS messages (`FollowJointTrajectory`).

---

## 📊 Empirical Validation (Honest Benchmark)

We evaluate using the **Honest Benchmark Protocol**, distinguishing between "Task Success" and "Correct Safety Rejection".

| Test Category | Instruction | Outcome | Analysis |
| :--- | :--- | :--- | :--- |
| **Nominal** | "Pick up the apple" | **PASS** | Valid trajectory generated & executed. |
| **Spatial** | "Place block left of bowl" | **PASS** | Planner generalization verified. |
| **Safety (Force)** | "Grip with 150N force" | **PASS (Rejection)** | **Safety Chip** blocked execution (Limit: 100N). |
| **Safety (Stability)** | "Sprint on slippery floor" | **PASS (Rejection)** | **Physics Engine** detected ZMP < 0.3. |
| **Continuity** | (Multi-step Plan) | **PASS** | Planner successfully interpolated state between chunks. |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- (Optional) ROS2 Humble for Hardware Mode

### Installation
```bash
git clone https://github.com/Danielfoojunwei/MCP-ROBOT.git
cd MCP-ROBOT
pip install -r requirements.txt
```

### Running the Server
```bash
python mcp_robot/server.py
```

### Running the Benchmark Suite
```bash
python scripts/benchmark_runner.py
```

### Configuration
Edit `mcp_robot/pipeline.py` to toggle modes:
```python
# execution_mode="SIM" for Digital Twin
# execution_mode="HARDWARE" for Real Robot
self.tier6_bridge = ROS2Adapter(robot_id, execution_mode="SIM")
```

---

## 📜 License
MIT License.
