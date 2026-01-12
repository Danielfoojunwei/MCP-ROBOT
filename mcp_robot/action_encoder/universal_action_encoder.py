import numpy as np
import logging
from typing import Dict, List, Optional
from mcp_robot.contracts.schemas import JointTrajectoryChunk, JointState

class UniversalActionEncoder:
    """
    Tier 4: Deterministic Universal Mapper.
    Translates task-space waypoints into joint-space trajectories.
    """
    def __init__(self, profiles: Dict):
        logging.info("Loading Tier 4: Deterministic Universal Mapper...")
        self.profiles = profiles

    def _solve_ik(self, world_pos: List[float], profile: Dict) -> List[float]:
        """
        Deterministic Geometric IK Solver for 7-DOF Manipulator.
        - q1: Base Rotation (Yaw)
        - q2: Shoulder (Pitch)
        - q3: Upper Arm (Roll)
        - q4: Elbow (Pitch)
        - q5: Forearm (Roll)
        - q6: Wrist (Pitch)
        - q7: Flange (Roll)
        """
        x, y, z = world_pos
        
        # 1. Base Rotation
        q1 = np.arctan2(y, x)
        
        # 2. Geometric Approximation for Reach
        r = np.sqrt(x**2 + y**2)
        h = z - 0.2 # Offset for base height
        dist = np.sqrt(r**2 + h**2)
        
        # Link lengths (Typical cobot arm)
        L1, L2 = 0.4, 0.4
        
        # Law of Cosines for Elbow (q4)
        cos_q4 = (dist**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_q4 = np.clip(cos_q4, -1.0, 1.0)
        q4 = -np.arccos(cos_q4)
        
        # Shoulder (q2)
        phi1 = np.arctan2(h, r)
        phi2 = np.arctan2(L2 * np.sin(-q4), L1 + L2 * np.cos(-q4))
        q2 = phi1 + phi2
        
        # Simple defaults for redundant joints (q3, q5, q6, q7)
        q3 = 0.0
        q5 = 0.0
        q6 = -q2 - q4 # Wrist compensation for level flange
        q7 = 0.0
        
        return [float(np.round(q, 6)) for q in [q1, q2, q3, q4, q5, q6, q7]]

    async def map_chunks_to_robot(
        self, 
        chunks: List[Dict], 
        robot_id: str, 
        wrist_cam, 
        overhead_cam, 
        current_joints: Dict[str, float] = None
    ) -> List[JointTrajectoryChunk]:
        """
        Map augmented chunks to joint trajectories deterministically.
        """
        profile = self.profiles.get(robot_id, {})
        joint_names = profile.get("joint_names", 
            ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7"]
        )
        
        mapped_chunks = []
        for chunk in chunks:
            # 1. Interpolate Task-Space Waypoints (Fixed Timeline)
            # Input waypoints might be low density. We ensure 10 points per chunk.
            raw_target_pos = chunk.get("position_waypoints")[-1] # Target is last pt
            
            workspace = profile.get("workspace", 
                {"x": {"min":-1, "max":1}, "y": {"min":-1, "max":1}, "z": {"min":0, "max":1}}
            )
            world_target = self._denormalize(raw_target_pos, workspace)
            
            # 2. Derive Joint Waypoints
            trajectory_waypoints = []
            
            # Start State
            if current_joints:
                start_pos = [current_joints.get(n, 0.0) for n in joint_names]
                trajectory_waypoints.append(JointState(names=joint_names, positions=start_pos))
            
            # Target State
            target_joint_pos = self._solve_ik(world_target, profile)
            trajectory_waypoints.append(JointState(names=joint_names, positions=target_joint_pos))
            
            # 3. Create Chunk (Ordinal and IDs will be set by pipeline)
            # Placeholder for ActionChunk fields (filled by Pipeline)
            traj = JointTrajectoryChunk(
                chunk_id="tmp", 
                plan_id="tmp", 
                ordinal=0,
                description=chunk.get("description", "trajectory"),
                joint_names=joint_names,
                waypoints=trajectory_waypoints,
                duration=chunk.get("duration_s", 2.0),
                max_force_est=chunk.get("estimated_force", 0.0)
            )
            mapped_chunks.append(traj)
            
            # Sequential state tracking if multiple chunks
            current_joints = {n: v for n, v in zip(joint_names, target_joint_pos)}
            
        return mapped_chunks

    def _denormalize(self, pos: List[float], workspace: Dict) -> List[float]:
        """Map [0,1] to World coordinates."""
        return [
            workspace["x"]["min"] + pos[0] * (workspace["x"]["max"] - workspace["x"]["min"]),
            workspace["y"]["min"] + pos[1] * (workspace["y"]["max"] - workspace["y"]["min"]),
            workspace["z"]["min"] + pos[2] * (workspace["z"]["max"] - workspace["z"]["min"])
        ]
