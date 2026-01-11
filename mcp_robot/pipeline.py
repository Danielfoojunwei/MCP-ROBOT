
import asyncio
import json
from typing import Dict
import numpy as np

from mcp_robot.planning.task_decomposer import ALOHATaskDecomposer
from mcp_robot.planning.long_horizon_planner import ACTLongHorizonPlanner
from mcp_robot.action_encoder.visio_tactile_action_encoder import VisioTactileActionEncoder
from mcp_robot.action_encoder.universal_action_encoder import UniversalActionEncoder
from mcp_robot.verification.verification_engine import VerificationEngine
from mcp_robot.execution.ros_edge_controller import ROSEdgeController
from mcp_robot.learning.learning_loop import LearningLoop

class MRCPUnifiedPipeline:
    """
    Complete pipeline: Task → Execution → Learning
    Orchestrates all 7 tiers in sequence.
    """
    
    def __init__(self, robot_id: str):
        # Mock Configs
        robot_profiles = {robot_id: {
            "workspace": {"x": {"min":-1, "max":1}, "y": {"min":-1, "max":1}, "z": {"min":0, "max":1}},
            "gripper": {"max_force_n": 100},
            "joint_names": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
        }}
        tactile_db = {} 
        
        self.robot_id = robot_id
        
        # Initialize all tiers
        self.tier1_decomposer = ALOHATaskDecomposer()
        self.tier2_planner = ACTLongHorizonPlanner()
        self.tier3_encoder = VisioTactileActionEncoder(robot_profiles[robot_id], tactile_db)
        self.tier4_mapper = UniversalActionEncoder(robot_profiles)
        self.tier5_verifier = VerificationEngine(robot_profiles[robot_id])
        self.tier6_controller = ROSEdgeController(robot_id)
        self.tier7_learner = LearningLoop(tactile_db)
        
        # Learning Logs Storage (exposed to MCP)
        self.logs = []
        # Plan storage
        self.active_plans = {}
    
    async def process_task(self, task_instruction: str) -> Dict:
        """
        Executes Tier 1 & 2 (Planning Phase).
        Returns a Plan object.
        """
        print(f"\n[MRCP Pipeline]: {task_instruction}")
        
        # Mock vision data
        camera_frames = {"overhead": np.zeros((224,224,3)), "wrist": np.zeros((224,224,3))}
        robot_state = {}
        
        # TIER 1
        subtasks = await self.tier1_decomposer.decompose_task(
            task_instruction=task_instruction,
            vision_frame=camera_frames["overhead"]
        )
        
        # TIER 2
        plan_result = await self.tier2_planner.plan_action_chunks(
            subtasks=subtasks,
            current_frame=camera_frames["overhead"],
            robot_state=robot_state,
            task_instruction=task_instruction
        )
        
        # Pre-process Tier 3 & 4 for the plan preview
        chunks = plan_result["chunks"]
        chunks = await self.tier3_encoder.augment_chunks_with_tactile(
             chunks, camera_frames["overhead"], [], {}
        )
        chunks = await self.tier4_mapper.map_chunks_to_robot(
             chunks, self.robot_id, camera_frames["wrist"], camera_frames["overhead"]
        )

        plan_id = f"plan_{int(asyncio.get_event_loop().time())}"
        plan_data = {
            "plan_id": plan_id,
            "instruction": task_instruction,
            "subtasks": subtasks,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
        self.active_plans[plan_id] = plan_data
        return plan_data

    async def execute_specific_chunk(self, chunk_id: str, plan_id: str = None) -> Dict:
        """
        Orchestrates Tier 5, 6, 7 for a single chunk.
        """
        # Find chunk logic (simplified)
        chunk_data = None
        # Search in all active plans if plan_id not provided
        plans_to_search = [self.active_plans[plan_id]] if plan_id and plan_id in self.active_plans else self.active_plans.values()
        
        for plan in plans_to_search:
            for chk in plan["chunks"]:
                if str(chk["id"]) == str(chunk_id):
                    chunk_data = chk
                    break
            if chunk_data: break
            
        if not chunk_data:
             return {"status": "ERROR", "reason": f"Chunk {chunk_id} not found."}

        # Tier 5: Verification
        camera_frame = np.zeros((224,224,3))
        current_tactile = {"grip_force": 0, "slip_detected": False}
        
        verification = await self.tier5_verifier.verify_chunk(
            chunk=chunk_data,
            camera_frame=camera_frame,
            tactile_current=current_tactile
        )
        
        if verification["status"] != "CERTIFIED":
            return {"status": "REJECTED", "reason": verification}

        # Tier 6: Execution
        result = await self.tier6_controller.execute_verified_chunk(chunk_data, verification)
        
        # Tier 7: Learning
        await self.tier7_learner.process_execution_telemetry(chunk_data, result, camera_frame)
        self.logs.append(result)
        
        # PERSIST LOGS FOR VISUALIZATION
        with open("pipeline_logs.json", "w") as f:
            json.dump(self.logs, f, indent=2)
        
        return result
