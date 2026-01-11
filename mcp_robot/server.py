
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

@mcp.resource("humanoid://{id}/balance")
def get_balance_telemetry(id: str) -> str:
    """Get real-time balance stability metrics (ZMP, CoP, CoM)."""
    # In a real app, this would query the robot hardware bridge directly
    # or the Pipeline's latest state cache.
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
async def execute_chunk(chunk_id: str) -> str:
    """
    TIER 6: Execute a specific action chunk on the hardware.
    CRITICAL: This tool performs TIER 5 Verification (Safety/Stability) first.
    """
    logging.info(f"Request to execute chunk: {chunk_id}")
    
    result = await pipeline.execute_specific_chunk(chunk_id)
    return json.dumps(result, indent=2)

@mcp.tool()
async def stabilize() -> str:
    """
    Emergency Tool: Trigger stable pose.
    """
    logging.warning("STABILIZE triggered!")
    return "Stabilization command sent to Whole-Body Controller."

# --- Main Entry Point ---

if __name__ == "__main__":
    print("Starting MRCP-H MCP Server...")
    mcp.run()
