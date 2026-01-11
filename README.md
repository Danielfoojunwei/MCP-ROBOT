
# MRCP-H: Multi-Robot Control Pipeline for Humanoids (via MCP)

**MRCP-H** is an agentic control framework that enables Large Language Models (LLMs) to safely control humanoid robots. It bridges the gap between high-level semantic reasoning and low-level whole-body control using the **Model Context Protocol (MCP)**.

![Architecture Status](https://img.shields.io/badge/Architecture-7--Tier-blue)
![Agent](https://img.shields.io/badge/Agent-Local_Qwen_0.5B-green)
![Safety](https://img.shields.io/badge/Safety-ZMP_Verification-red)

## 🚀 Key Features

*   **7-Tier Architecture**: A robust pipeline from Task Decomposition (ALOHA) to Hardware Execution (ROS2).
*   **MCP Integration**: Exposes robot capabilities as standard **MCP Tools** (`submit_task`, `execute_chunk`) and **Resources** (`humanoid://balance`).
*   **Safety-First**: Includes a **Tier 5 Verification Engine** that checks ZMP (Zero Moment Point) stability and tactile slip risks *before* execution.
*   **Local Agent**: Includes a fully autonomous local agent using **Qwen2.5-0.5B** that runs on your CPU, ensuring privacy and zero latency.
*   **Live Visualization**: Generates dashboards correlating execution timeline with stability metrics.

## 🏗️ Architecture

The system is composed of 7 tiers, exposed via `mrcp/server.py`:

| Tier | Component | Function | Status |
| :--- | :--- | :--- | :--- |
| **1** | **Task Decomposer** | NLU -> Subtasks (ALOHA-inspired) | ✅ Implemented |
| **2** | **Long-Horizon Planner** | Subtasks -> Action Chunks (ACT) | ✅ Implemented |
| **3** | **Visio-Tactile Encoder** | Fuses Vision + Tactile constraints | ✅ Implemented |
| **4** | **Universal Mapper** | Norm. Actions -> Robot Kinematics (UMI) | ✅ Implemented |
| **5** | **Verification Engine** | ZMP Stability & Safety Checks | ✅ Implemented |
| **6** | **Edge Controller** | ROS2 Real-time Servo Loop | ✅ Implemented |
| **7** | **Learning Loop** | Execution Telemetry -> Model Update | ✅ Implemented |

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/mrcp-h.git
    cd mrcp-h
    ```

2.  **Install Dependencies**:
    Requires Python 3.10+.
    ```bash
    pip install mcp transformers torch matplotlib numpy
    ```

## 🏃 Usage

### 1. Run the MCP Server (Standalone)
To run the server for connection to Claude Desktop or other MCP clients:
```bash
python mrcp/server.py
```

### 2. Run the Autonomous Local Agent
To verify the system with the local **Qwen-0.5B** agent:
```bash
python scripts/local_agent.py
```
*   **Input**: "Pick up the red cube from the table."
*   **Behavior**: The agent will autonomously download the model, connect to the pipeline, plan the task, and execute safe chunks.

### 3. Generate Visualization Dashboard
After running the agent, generate a performance report:
```bash
python scripts/generate_dashboard.py
```
This produces `viz_output/dashboard.html` with graphs of:
*   Execution Latency
*   Stability Confidence Scores

## 🧠 Local Agent Details

The project uses `scripts/local_agent.py` to demonstrate agentic capabilities without external APIs.
*   **Model**: `Qwen/Qwen2.5-0.5B-Instruct`
*   **method**: ReAct Loop (Think -> Act -> Observe)
*   **Prompting**: Few-Shot JSON constraints to ensure reliable tool usage.

## 📊 Directory Structure

```
mrcp-h/
├── mrcp/                   # Core Package
│   ├── action_encoder/     # Tiers 3 & 4
│   ├── execution/          # Tier 6 (ROS)
│   ├── learning/           # Tier 7
│   ├── planning/           # Tiers 1 & 2
│   ├── verification/       # Tier 5 (Internal Gatekeeper)
│   ├── pipeline.py         # 7-Tier Orchestrator
│   └── server.py           # MCP Server Entrypoint
├── scripts/
│   ├── local_agent.py      # Qwen-based Autonomous Client
│   ├── simulate_client.py  # Mock Client for testing
│   └── generate_dashboard.py # Viz Generator
└── README.md
```

## 📜 License

MIT License.
