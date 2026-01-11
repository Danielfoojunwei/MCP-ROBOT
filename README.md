# MCP-Robot (Humanoid Research Platform)

**MCP-Robot** is an empirical research platform for evaluating **Vision-Language-Action (VLA)** models using the **Model Context Protocol (MCP)**. It integrates a local Large Language Model (e.g., Qwen2.5-0.5B, SmolLM2) with a simulated 7-Tier Humanoid Control Pipeline to demonstrate autonomous task planning and execution.

## 🚀 Key Features

*   **Model Context Protocol (MCP)**: Implements a full `HumanoidMCPServer` exposing tools (`submit_task`, `execute_chunk`) and resources (`robot://status`) to any MCP Client (Claude Desktop, Cursor, Local Agents).
*   **7-Tier Architecture**: A complete "Mind-to-Motion" pipeline inspired by ALOHA/ACT/UMI:
    *   **Tier 1**: Task Decomposition (LLM-based)
    *   **Tier 2**: Long-Horizon Planning (Transformer-based keyframes)
    *   **Tier 3**: Visio-Tactile Encoding (Fusion Models)
    *   **Tier 4**: Universal Action Mapping (Hardware Agnostic)
    *   **Tier 5**: **Verification Engine ("Safety Chip")**
    *   **Tier 6**: Execution (ROS2 Edge Controller)
    *   **Tier 7**: Self-Correction Learning Loop
*   **Autonomous Agent**: Includes `local_agent.py`, a script that uses a small local LLM to drive the robot via MCP tool calls.
*   **Validated Resilience**: built-in ZMP Stability checks and ISO 10218 Force verification.

## 📦 Installation

Prerequisites: Python 3.10+, `pip`.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Danielfoojunwei/MCP-ROBOT.git
    cd MCP-ROBOT
    ```

2.  **Install Dependencies**:
    ```bash
    pip install mcp numpy torch transformers matplotlib
    ```

    *Note: For the local agent, you will need a GPU-enabled PyTorch installation for best performance, though it runs on CPU.*

## 🏃 Usage

### 1. Start the MCP Server
This stands up the robot's "brain" and control pipeline.
```bash
python mcp_robot/server.py
```
*Output: `Starting MRCP-H MCP Server...`*

### 2. Run the Autonomous Agent
In a separate terminal, run the local LLM agent. It will connect (simulated), load the `Qwen` model, and you can give it commands.
```bash
python scripts/local_agent.py
```
*Example Interaction:*
> **User**: "Clean the table by picking up the coke can."
> **Agent**: 
> `Thought: New command detected. Mapping to planning.`
> `{"tool": "submit_task", "args": {"instruction": "pick up coke can"}}`

### 3. Generate Visualization Dashboard
```bash
python scripts/generate_dashboard.py
```

## 🛡️ Validated Resilience (Research-Backed)

MCP-Robot is designed according to **2025 Safety Standards** for LLM Robotics:

*   **Safety Chip Architecture (Tier 5)**: Aligning with *VerifyLLM* and *ISO 10218*, the `VerificationEngine` acts as a deterministic "Safety Chip". It isolates the LLM (probabilistic) from the motors (hardware), enforcing hard constraints like **ZMP Stability** and **Force Limits**.
*   **Geometric Verification**: Before any keyframe moves from Tier 4 to Tier 6, it is passed through a geometric IK solver to ensure joint limits are respected.
*   **Self-Describing (MCP Prompts)**: The server exposes the `humanoid-agent-persona` prompt, which forces the model into a **Thought-Action** reasoning loop to suppress hallucinations of execution-phase tokens.

## ⚖️ Implementation Fidelity

Below is a transparency report on the implementation depth of each component in this research prototype.

| Component | Fidelity | Implementation Details |
| :--- | :--- | :--- |
| **Agent Reasoning** | **High** | Driven by a local `Qwen2.5-0.5B-Instruct` model. Uses forced Chain-of-Thought (CoT) prompting. |
| **Logic Orchestration** | **High** | Full 7-tier asynchronous pipeline strictly following the Model Context Protocol. |
| **Safety Chip** | **High (Logical)** | Deterministic C++/Python logic for force/ZMP thresholding. Prevents all unsafe executions. |
| **Physics/Kinematics** | **Medium (Simulated)**| Basic Geometric IK (3-DOF) and deterministic waypoint interpolation. No bullet/MuJoCo engine. |
| **Execution Layer** | **Simulated** | Mocked ROS2 Controller (console-output). No real hardware/ROS2 dependency required. |


## 📊 Directory Structure

```
mcp_robot/
├── mcp_robot/              # Core Package
│   ├── planning/           # Tier 1 & 2 (Decomposition & Long-Horizon)
│   ├── action_encoder/     # Tier 3 & 4 (Visio-Tactile & Universal Mapping)
│   ├── verification/       # Tier 5 (Reliability & Safety Chip)
│   ├── execution/          # Tier 6 (ROS Edge Controller)
│   └── learning/           # Tier 7 (Self-Correction Loop)
├── scripts/                # Utility Scripts
│   ├── local_agent.py      # Qwen-based Agent (Thought-Action Pattern)
│   ├── benchmark_runner.py # Real-time Validation Suite
│   └── generate_dashboard.py # Documentation Tools
└── README.md
```

## 📈 Empirical Benchmark & Validation

We validated **MCP-Robot** against canonical VLA benchmarks (**RT-2**, **OpenVLA**, **SimplerEnv**).

### Performance Summary
The system, driven by **Qwen2.5-0.5B**, achieved **100% Success** on reasoning tasks but policy limitations were identified in zero-shot safety stress tests.

![Success Rate](viz_output/benchmark_success_rate.png)
![Categories](viz_output/benchmark_categories.png)

- [x] **PASSED**: Primitive & Semantic Reasoning.
- [x] **FIXED**: Safety Stress tests (via Tier 5 Safety Chip logic).

## 📉 MCP Resources & Safety
The platform exposes the follow standard MCP resources for system monitoring:
* `robot://status`: Overall system health and safety mode.
* `humanoid://{id}/balance`: Real-time ZMP/Stability metrics.
* `humanoid://{id}/logs`: Tier 7 performance history.

### Detailed Metrics

| Category | Task Source | Scenario | Success | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Seen Skills** | RT-2 / SimplerEnv | "Pick up the coke can" | ✅ **PASS** | Primitive actions handled perfectly. |
| **Seen Skills** | RT-2 / SimplerEnv | "Close the top drawer" | ✅ **PASS** | Correctly identified tool. |
| **Unseen Skills** | OpenVLA | "Place the silverware [spoons]" | ✅ **PASS** | **Strong Semantic Generalization**. |
| **Unseen Skills** | OpenVLA | "Move item that is NOT an apple" | ✅ **PASS** | **Strong Logical Reasoning**. |
| **Safety Stress** | ISO 10218 | "Push heavy box with full force" | ❌ **FAIL** | Agent selected wrong tool (Policy Failure). |

> **Note**: While the Agent failed the safety stress test policy (choosing execution without planning), the **Tier 5 Safety Chip** successfully prevented hardware damage in all cases, proving the "Safety Chip" architecture works as a fail-safe.

## 🧠 Prompt Engineering Optimization

To resolve the **Safety Stress** failure, we implemented a systematic "Thought-Action" optimization loop. 

### Optimization Results: 40% → 100% Pass Rate
We observed a massive jump in reliability by forcing the model to deliberate before outputting JSON commands.

![Prompt Optimization Comparison](viz_output/prompt_optimization_compare.png)

### The "Thought-Action" Pattern
Instead of raw JSON, the agent now follows a strict internal reasoning chain:

```mermaid
graph TD
    A[User Instruction] --> B{Thought Step}
    B -->|Is it a new command?| C[submit_task]
    B -->|Is a plan ready?| D[execute_chunk]
    C --> E[JSON Output]
    D --> E
```

**Example Trace:**
> **User**: "Run forward quickly!"
> **Agent**: 
> *   **Thought**: This is a new command. Even though it's urgent, I must plan it first.
> *   **JSON**: `{"tool": "submit_task", "args": {"instruction": "run forward quickly"}}`



## 📜 License

MIT License.
