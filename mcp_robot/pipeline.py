import asyncio
import logging
from typing import Dict, List, Optional
import numpy as np

from mcp_robot.runtime.determinism import StableHasher, DeterminismConfig, global_clock
from mcp_robot.contracts.schemas import (
    RobotStateSnapshot, PerceptionSnapshot, ActionChunk, JointTrajectoryChunk, TaskPlan
)
from mcp_robot.planning.task_decomposer import ALOHATaskDecomposer
from mcp_robot.planning.long_horizon_planner import ACTLongHorizonPlanner
from mcp_robot.action_encoder.visio_tactile_action_encoder import VisioTactileActionEncoder
from mcp_robot.action_encoder.universal_action_encoder import UniversalActionEncoder
from mcp_robot.verification.verification_engine import VerificationEngine
from mcp_robot.execution.ros_interface import ROS2Adapter
from mcp_robot.learning.learning_loop import LearningLoop
from mcp_robot.simulation.kinematic_sim import KinematicSimulator
from mcp_robot.verification.physics_engine import PhysicsEngine

class MRCPUnifiedPipeline:
    """
    Tier 0: Pure Orchestration Pipeline.
    Strictly deterministic: Input Snapshots -> Verified Action Chunks.
    """
    
    def __init__(self, robot_id: str, config: Optional[DeterminismConfig] = None):
        self.robot_id = robot_id
        self.config = config or DeterminismConfig()
        self.lock = asyncio.Lock()
        
        # Robot Specific Profile (Stable)
        self.robot_profile = {
            "workspace": {"x": {"min":-1.0, "max":1.0}, "y": {"min":-1.0, "max":1.0}, "z": {"min":0.0, "max":1.0}},
            "gripper": {"max_force_n": 100.0},
            "joint_names": ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7"],
            "joint_limits": {
                "joint_1": (-3.14, 3.14), "joint_2": (-2.0, 2.0), "joint_3": (-3.14, 3.14),
                "joint_4": (-3.14, 3.14), "joint_5": (-3.14, 3.14), "joint_6": (-3.14, 3.14),
                "joint_7": (-6.28, 6.28)
            }
        }
        
        # Initialize Tiers
        self.kinematic_sim = KinematicSimulator()
        self.tier1_decomposer = ALOHATaskDecomposer()
        self.tier2_planner = ACTLongHorizonPlanner()
        self.tier3_encoder = VisioTactileActionEncoder(self.robot_profile, {})
        self.tier4_mapper = UniversalActionEncoder({robot_id: self.robot_profile})
        self.tier5_verifier = VerificationEngine(self.robot_profile, self.kinematic_sim)
        self.tier6_bridge = ROS2Adapter(robot_id, execution_mode="SIM")
        self.tier7_learner = LearningLoop({})
        
        self.active_plans: Dict[str, TaskPlan] = {}
        self.execution_results: Dict[str, Dict] = {} # Idempotency cache

    async def process_task(
        self, 
        instruction: str, 
        perception: PerceptionSnapshot, 
        state: RobotStateSnapshot
    ) -> TaskPlan:
        """
        Deterministic Planning Entrypoint.
        Input: Instruction + environment snapshots.
        Output: Fully formed, hashed TaskPlan.
        """
        async with self.lock:
            # 1. Deterministic ID Generation
            input_dict = {
                "instruction": instruction,
                "perception": perception.model_dump(),
                "state": state.model_dump()
            }
            input_digest = StableHasher.sha256_json(input_dict)
            config_digest = StableHasher.sha256_json(self.config.model_dump())
            
            plan_id = StableHasher.sha256_json({
                "input_digest": input_digest,
                "config_digest": config_digest,
                "schema_version": state.schema_version
            })

            if plan_id in self.active_plans:
                return self.active_plans[plan_id]

            logging.info(f"[Pipeline] Planning {plan_id} for '{instruction}'")

            # TIER 1: Decompose
            subtasks = await self.tier1_decomposer.decompose_task(
                task_instruction=instruction,
                vision_frame=None, 
                detected_objects=perception.detected_objects
            )

            # TIER 2: Long-Horizon Plan
            plan_result = await self.tier2_planner.plan_action_chunks(
                subtasks=subtasks,
                current_frame=None, 
                robot_state=state.model_dump(),
                task_instruction=instruction
            )

            # TIER 3/4: Encode & Map
            raw_chunks = plan_result["chunks"]
            vision_context = perception.camera_frame_digest
            
            augmented_chunks = await self.tier3_encoder.augment_chunks_with_tactile(
                raw_chunks, None, perception.detected_objects, perception.tactile_summary
            )
            
            traj_objects = await self.tier4_mapper.map_chunks_to_robot(
                augmented_chunks, self.robot_id, None, None, current_joints=state.to_ordered_dict()
            )

            # 2. Finalize Chunk IDs deterministically
            final_chunks = []
            for i, traj in enumerate(traj_objects):
                chunk_id = StableHasher.sha256_json({
                    "plan_id": plan_id,
                    "ordinal": i,
                    "payload_digest": StableHasher.sha256_json(traj.model_dump())
                })
                traj.chunk_id = chunk_id
                traj.plan_id = plan_id
                traj.ordinal = i
                traj.timestamp = global_clock.now()
                final_chunks.append(traj)

            plan = TaskPlan(
                plan_id=plan_id,
                instruction=instruction,
                input_digest=input_digest,
                config_digest=config_digest,
                chunks=final_chunks,
                created_at=global_clock.now()
            )
            
            self.active_plans[plan_id] = plan
            return plan

    async def execute_chunk(self, plan_id: str, chunk_id: str) -> Dict:
        """
        Deterministic Execution Entrypoint.
        """
        async with self.lock:
            # 1. Idempotency Check
            exec_id = f"{plan_id}:{chunk_id}"
            if exec_id in self.execution_results:
                return self.execution_results[exec_id]

            if plan_id not in self.active_plans:
                return {"status": "ERROR", "reason": f"Plan {plan_id} not found."}

            plan = self.active_plans[plan_id]
            target_chunk = next((c for c in plan.chunks if c.chunk_id == chunk_id), None)
            
            if not target_chunk:
                return {"status": "ERROR", "reason": f"Chunk {chunk_id} not found."}

            # 2. Tier 5: Verification (Auth Safety Gate)
            sim_state = self.kinematic_sim.get_state_vector()
            # Physics verifier now takes Snapshot-derived dicts
            safety_report = PhysicsEngine.verify_trajectory(
                target_chunk, sim_state, self.robot_profile["joint_limits"]
            )

            if not safety_report["valid"]:
                result = {"status": "REJECTED", "reason": safety_report["reason"]}
                self.execution_results[exec_id] = result
                return result

            # 3. Tier 6: Execution
            logging.info(f"[Pipeline] Executing {chunk_id}")
            result = await self.tier6_bridge.execute_trajectory(target_chunk)
            
            # 4. Deterministic SIM Update
            if result.get("success") and self.tier6_bridge.mode == "SIM":
                # In SIM, we update based on planned target, NOT wall-clock feedback
                if isinstance(target_chunk, JointTrajectoryChunk):
                    last_wp = target_chunk.waypoints[-1]
                    self.kinematic_sim.set_joint_state(last_wp.positions)
            
            self.kinematic_sim.step()
            
            final_result = {
                "status": "SUCCESS" if result.get("success") else "FAILED",
                "ros_result": result,
                "executed_at": global_clock.now()
            }
            
            self.execution_results[exec_id] = final_result
            return final_result
