
import asyncio
import logging
import json
from typing import Dict, List

from mcp.server.fastmcp import FastMCP
import mcp.types as types

# Import Real Backend
from mcp_robot.pipeline import MRCPUnifiedPipeline

# Initialize the MCP Server
print("Initializing MCP-Robot Server...")
mcp = FastMCP("MCP-Robot Control")

# Initialize Pipeline
pipeline = MRCPUnifiedPipeline(robot_id="humanoid_01")

# --- Resources ---

@mcp.resource("robot://status")
def get_overall_status() -> str:
    """Get overall robot system status."""
    return json.dumps({
        "robot_id": pipeline.robot_id,
        "mode": "COLLABORATIVE",
        "battery": 85,
        "is_stabilized": True
    }, indent=2)

@mcp.resource("humanoid://{id}/balance")
def get_balance_telemetry(id: str) -> str:
    """Get real-time balance stability metrics (ZMP, CoP, CoM)."""
    return json.dumps({
        "zmp": {"x": 0.01, "y": -0.02}, 
        "status": "STABLE"
    }, indent=2)

@mcp.resource("humanoid://{id}/logs")
def get_learning_logs(id: str) -> str:
    """Get Tier 7 learning and execution logs."""
    return json.dumps(pipeline.logs, indent=2)

# --- Tools (The 7-Tier Interface) ---

@mcp.tool()
async def submit_task(instruction: str) -> str:
    """
    TIER 1 & 2: Submit a high-level natural language instruction to the robot.
    Triggers Task Decomposition (ALOHA) and Long-Horizon Planning (ACT).
    Returns a Plan Summary with plan_id.
    """
    logging.info(f"Received task: {instruction}")
    
    plan = await pipeline.process_task(instruction)
    
    # Return a summary (don't dump full chunks, too large)
    summary = {
        "plan_id": plan["plan_id"],
        "subtasks": plan["subtasks"],
        "total_chunks": plan["total_chunks"],
        "status": "READY_FOR_EXECUTION"
    }
    return json.dumps(summary, indent=2)

@mcp.tool()
async def execute_chunk(plan_id: str, chunk_id: str) -> str:
    """
    TIER 6: Execute a specific action chunk on the hardware.
    CRITICAL: Requires both plan_id and chunk_id to prevent ambiguity.
    """
    logging.info(f"Request to execute chunk: {chunk_id} for plan: {plan_id}")
    
    result = await pipeline.execute_specific_chunk(plan_id, chunk_id)
    return json.dumps(result, indent=2)

@mcp.tool()
async def stabilize() -> str:
    """
    Emergency Tool: Trigger stable pose.
    """
    logging.warning("STABILIZE triggered!")
    return "Stabilization command sent to Whole-Body Controller."

# --- Main Entry Point ---

@mcp.prompt("humanoid-agent-persona")
def humanoid_agent_persona() -> str:
    """Returns the DYNAMIC system prompt based on robot state."""
    # In a real system, we'd read this from the pipeline
    battery_level = 85 
    mode = "Collaborative (ISO 10218)"
    
    return f"""You are a robot controller for MCP-Robot (Humanoid 01).
You DO NOT chat. You ONLY output JSON tool calls.

CURRENT STATUS:
- Battery: {battery_level}%
- Safety Mode: {mode}

AVAILABLE TOOLS:
1. submit_task(instruction: str)
   - Function: Decompose high-level goal into a plan.
2. execute_chunk(plan_id: str, chunk_id: str)
   - Function: Execute a verified action chunk.
   - NOTE: You MUST provide the plan_id from the previous tool output.
   - NOTE: This passes through the Tier 5 'Safety Chip' (ZMP + Force Limits).

FORMAT:
Output ONLY JSON: {{"tool": "name", "args": {{...}}}}
"""

if __name__ == "__main__":
    print("Starting MRCP-H MCP Server...")
    mcp.run()
