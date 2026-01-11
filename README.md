
# MCP-Robot: Agentic Humanoid Control

**MCP-Robot** (formerly MRCP-H) is an agentic control framework that enables Large Language Models (LLMs) to safely control humanoid robots. It bridges the gap between high-level semantic reasoning and low-level whole-body control using the **Model Context Protocol (MCP)**.

![Architecture Status](https://img.shields.io/badge/Architecture-7--Tier-blue)
![Agent](https://img.shields.io/badge/Agent-Local_Qwen_0.5B-green)
![Safety](https://img.shields.io/badge/Safety-ZMP_Verification-red)

## 🚀 Key Features

*   **7-Tier Architecture**: A robust pipeline from Task Decomposition (ALOHA) to Hardware Execution (ROS2).
*   **MCP Integration**: Exposes robot capabilities as standard **MCP Tools** (`submit_task`, `execute_chunk`) and **Resources** (`humanoid://balance`).
*   **Safety-First**: Includes a **Tier 5 Verification Engine** that checks ZMP (Zero Moment Point) stability and tactile slip risks *before* execution.
*   **Local Agent**: Includes a fully autonomous local agent using **Qwen2.5-0.5B** that runs on your CPU, ensuring privacy and zero latency.
*   **Live Visualization**: Generates dashboards correlating execution timeline with stability metrics.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/mcp-robot.git
    cd mcp-robot
    ```

2.  **Install Dependencies**:
    ```bash
    pip install mcp transformers torch matplotlib numpy
    ```

## 🏃 Usage

### 1. Run the MCP Server (Standalone)
```bash
python mcp_robot/server.py
```

### 2. Run the Autonomous Local Agent
```bash
python scripts/local_agent.py
```
*   **Input**: "Pick up the red cube from the table."
*   **Behavior**: The agent will autonomously download the model, connect to the pipeline, plan the task, and execute safe chunks.

### 3. Generate Visualization Dashboard
```bash
python scripts/generate_dashboard.py
```

## 📊 Directory Structure

```
mcp-robot/
├── mcp_robot/              # Core Package (formerly mrcp)
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
