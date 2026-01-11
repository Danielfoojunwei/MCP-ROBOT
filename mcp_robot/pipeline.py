
import asyncio
import json
from typing import Dict
import numpy as np

from mcp_robot.planning.task_decomposer import ALOHATaskDecomposer
from mcp_robot.planning.long_horizon_planner import ACTLongHorizonPlanner
from mcp_robot.action_encoder.visio_tactile_action_encoder import VisioTactileActionEncoder
from mcp_robot.action_encoder.universal_action_encoder import UniversalActionEncoder
from mcp_robot.verification.verification_engine import VerificationEngine
from mcp_robot.execution.ros_interface import ROS2ExecutionBridge
from mcp_robot.contracts.schemas import JointTrajectoryChunk
from mcp_robot.simulation.kinematic_sim import KinematicSimulator
from mcp_robot.verification.physics_engine import PhysicsEngine
from mcp_robot.learning.learning_loop import LearningLoop

class MRCPUnifiedPipeline:
    """
    Complete pipeline: Task → Execution → Learning
    Orchestrates all 7 tiers with Strict Contracts & Kinematic State.
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
        
        # Initialize Simulator (Digital Twin)
        self.kinematic_sim = KinematicSimulator()
        
        # Initialize all tiers
        self.tier1_decomposer = ALOHATaskDecomposer()
        self.tier2_planner = ACTLongHorizonPlanner()
        self.tier3_encoder = VisioTactileActionEncoder(robot_profiles[robot_id], tactile_db)
        self.tier4_mapper = UniversalActionEncoder(robot_profiles)
        self.tier5_verifier = VerificationEngine(robot_profiles[robot_id], self.kinematic_sim)
        
        # TIER 6: Real ROS2 Bridge
        self.tier6_bridge = ROS2ExecutionBridge(robot_id)
        
        self.tier7_learner = LearningLoop(tactile_db)
        
        # Learning Logs Storage (exposed to MCP)
        self.logs = []
        # Plan storage
        self.active_plans = {}
    
    async def process_task(self, task_instruction: str) -> Dict:
        """
        Executes Tier 1 & 2 (Planning Phase).
        Returns a Plan ID.
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
        
        # Pre-process Tier 3 & 4
        chunks = plan_result["chunks"]
        chunks = await self.tier3_encoder.augment_chunks_with_tactile(
             chunks, camera_frames["overhead"], [], {}
        )
        
        # TIER 4: Returns List[JointTrajectoryChunk] Objects
        traj_objects = await self.tier4_mapper.map_chunks_to_robot(
             chunks, self.robot_id, camera_frames["wrist"], camera_frames["overhead"]
        )

        plan_id = f"plan_{int(asyncio.get_event_loop().time())}"
        
        # We store the *Objects* in memory. 
        # For JSON debug we might serialize them, but execution uses Objects.
        plan_data = {
            "plan_id": plan_id,
            "instruction": task_instruction,
            "subtasks": subtasks,
            "chunks": [t.dict() for t in traj_objects], # Serialize for API/Viz
            "chunk_objects": traj_objects, # Keep Objects for Execution
            "total_chunks": len(traj_objects)
        }
        self.active_plans[plan_id] = plan_data
        return plan_data

    async def execute_specific_chunk(self, plan_id: str, chunk_id: str) -> Dict:
        """
        Orchestrates Tier 5 (Verify) -> Tier 6 (ROS2 Action).
        """
        # Strict Plan Ownership
        if not plan_id or plan_id not in self.active_plans:
             return {"status": "ERROR", "reason": f"Plan {plan_id} not found/expired."}

        plan = self.active_plans[plan_id]
        target_chunk_obj = None
        
        # Find the Object
        for obj in plan["chunk_objects"]:
             if str(obj.id) == str(chunk_id):
                 target_chunk_obj = obj
                 break
            
        if not target_chunk_obj:
             return {"status": "ERROR", "reason": f"Chunk {chunk_id} not found in plan {plan_id}."}

        camera_frame = np.zeros((224,224,3))
        
        # Tier 5: Verification (Safety Chip) - Uses Object & Physics Engine
        # We call the static method on PhysicsEngine directly here for efficiency, 
        # or use the wrapper. Let's use the wrapper if updated, but for now direct Physics call is cleanest integration.
        sim_state = self.kinematic_sim.get_state_vector()
        
        # VERIFY TRAJECTORY OBJECT
        safety_report = PhysicsEngine.verify_trajectory(target_chunk_obj, sim_state)
        
        if not safety_report["valid"]:
            print(f"[Tier 5] CRITICAL: Safety Chip Rejected Trajectory: {safety_report['reason']}")
            return {"status": "rejected", "reason": safety_report['reason']}
        
        print(f"[Tier 5] Trajectory Certified Safe. Handing off to ROS2 Bridge.")
            
        # Tier 6: Execution (ROS2 Bridge)
        # Passes the Validated Object
        result = await self.tier6_bridge.execute_trajectory(target_chunk_obj)
        
        # UPDATE SIMULATOR STATE
        self.kinematic_sim.step() 
        
        # Tier 7: Learning (Mock log)
        self.logs.append(result)
        
        return result
