import asyncio
import logging
import json
from typing import Dict, List, Optional

from mcp.server.fastmcp import FastMCP
import mcp.types as types

from mcp_robot.pipeline import MRCPUnifiedPipeline
from mcp_robot.contracts.schemas import RobotStateSnapshot, PerceptionSnapshot, JointTrajectoryChunk, JointState
from mcp_robot.runtime.determinism import StableHasher, global_clock

# Initialize FastMCP
mcp = FastMCP("MCP-Robot Deterministic Control")

# Initialize Deterministic Pipeline
pipeline = MRCPUnifiedPipeline(robot_id="humanoid_01")

def _get_current_snapshots():
    """Helper to fetch synchronized snapshots for planning."""
    state = pipeline.kinematic_sim.get_state_vector()
    
    perception = PerceptionSnapshot(
        camera_frame_digest=StableHasher.sha256_json("mock_frame"),
        detected_objects=[
            {"type": "cube", "mass": 0.5, "friction_coefficient": 0.6},
            {"type": "bin", "mass": 5.0, "friction_coefficient": 0.3}
        ],
        timestamp=global_clock.now()
    )
    return state, perception

@mcp.tool()
async def submit_task(instruction: str) -> str:
    """
    Submits a task instruction. 
    Deterministically generates a sequence of action chunks.
    """
    state, perception = _get_current_snapshots()
    
    plan = await pipeline.process_task(instruction, perception, state)
    
    # Return canonicalized JSON
    return json.dumps({
        "plan_id": plan.plan_id,
        "instruction": plan.instruction,
        "total_chunks": len(plan.chunks),
        "status": "PLAN_GENERATED",
        "digest": plan.input_digest
    }, sort_keys=True, indent=2)

@mcp.tool()
async def execute_chunk(plan_id: str, chunk_id: str) -> str:
    """Executes a specific chunk from a generated plan."""
    result = await pipeline.execute_chunk(plan_id, chunk_id)
    return json.dumps(result, sort_keys=True, indent=2)

@mcp.tool()
async def stabilize() -> str:
    """
    Triggers a deterministic stabilization trajectory (Home Pose).
    """
    # Create a synthetic Home Chunk
    joint_names = pipeline.robot_profile["joint_names"]
    home_pos = [0.0] * len(joint_names)
    
    state, _ = _get_current_snapshots()
    
    home_chunk = JointTrajectoryChunk(
        chunk_id="stabilize_cmd",
        plan_id="system",
        ordinal=0,
        description="Stabilizing to home pose",
        joint_names=joint_names,
        waypoints=[
            JointState(names=joint_names, positions=state.joint_positions),
            JointState(names=joint_names, positions=home_pos)
        ],
        duration=2.0
    )
    
    result = await pipeline.tier6_bridge.execute_trajectory(home_chunk)
    if result.get("success"):
        pipeline.kinematic_sim.set_joint_state(home_pos)
        
    return json.dumps({
        "status": "STABILIZED" if result.get("success") else "FAILED",
        "final_state": home_pos
    }, sort_keys=True, indent=2)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run()
