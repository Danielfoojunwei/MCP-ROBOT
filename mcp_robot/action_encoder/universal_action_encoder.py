import numpy as np
from typing import Dict, List
from mcp_robot.contracts.schemas import JointTrajectoryChunk, JointState

class UniversalActionEncoder:
    """
    Tier 4: Maps abstract intentions to Rigorous JointTrajectoryChunk Schemas.
    """
    def __init__(self, profiles: Dict):
        print("Loading Tier 4: Universal Mapper...")
        self.profiles = profiles

    def _solve_ik(self, world_pos: List[float]) -> List[float]:
        """
        Deterministic 'Pseudo-IK' mapping World (x,y,z) -> 7 Joint Angles.
        In a real system, this wraps `dm_control` or `kdl_parser`.
        """
        x, y, z = world_pos
        # Mock geometric solution for 7-DOF arm
        q1 = np.arctan2(y, x) 
        q2 = np.clip(z * 2.0, -1.5, 1.5)
        q3 = np.clip(x * 0.5, -3.14, 3.14)
        q4 = -q2 # Elbow compensation
        q5 = 0.0 # Wrist 1
        q6 = np.clip(y * 0.5, -1.0, 1.0) # Wrist 2
        q7 = 0.0 # Flange
        return [float(q) for q in [q1, q2, q3, q4, q5, q6, q7]]

    async def map_chunks_to_robot(
        self, 
        chunks: List[Dict], 
        robot_id: str, 
        wrist_cam, 
        overhead_cam, 
        current_joints: Dict[str, float] = None
    ) -> List[JointTrajectoryChunk]:
        """
        Converts Planning Chunks -> Validated JointTrajectoryChunks.
        """
        profile = self.profiles.get(robot_id, {})
        # Standardize strict joint names for the contract
        joint_names = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7"]
        
        mapped_chunks = []
        for chunk in chunks:
            # Generate waypoints (interpolate for "trajectory" feel)
            # In real system: full PL/spline generation
            target_pos = chunk.get("position_waypoints", [0.5, 0, 0.5])
            
            # 1. Denormalize
            if isinstance(target_pos[0], list): target_pos = target_pos[0] # Take first point
            
            workspace = profile.get("workspace", {"x": {"min":-1, "max":1}, "y": {"min":-1, "max":1}, "z": {"min":0, "max":1}})
            world_pos = self._denormalize_to_world(target_pos, workspace)

            # 2. IK
            target_joints = self._solve_ik(world_pos)
            
            # Create Trajectory
            waypoints = []
            
            # 2a. Start Point (Current State) - Crucial for Continuity
            if current_joints:
                start_positions = [current_joints.get(name, 0.0) for name in joint_names]
                waypoints.append(JointState(names=joint_names, positions=start_positions))
            
            # 2b. Target Point
            waypoints.append(JointState(names=joint_names, positions=target_joints))
            
            # Construct the Strict Contract Object
            traj = JointTrajectoryChunk(
                id=str(chunk["id"]),
                description=chunk.get("description", "move"),
                joint_names=joint_names,
                waypoints=waypoints, # [Start, Target]
                duration=2.0, # seconds
                # Propagate intent for verification
                max_force_est=chunk.get("estimated_force", 0.0) 
            )
            mapped_chunks.append(traj)
            
            # Update "Current" for next chunk (Chain Chunks)
            if current_joints: 
                current_joints = {n: v for n, v in zip(joint_names, target_joints)}
            
        return mapped_chunks

    def _denormalize_to_world(self, normalized_pos: List[float], workspace: Dict) -> List[float]:
        """Convert 0-1 normalized position to world coordinates."""
        # Safety check for dimensions
        if len(normalized_pos) < 3: return [0.5, 0.5, 0.5]
        
        return [
            workspace["x"]["min"] + normalized_pos[0] * (workspace["x"]["max"] - workspace["x"]["min"]),
            workspace["y"]["min"] + normalized_pos[1] * (workspace["y"]["max"] - workspace["y"]["min"]),
            workspace["z"]["min"] + normalized_pos[2] * (workspace["z"]["max"] - workspace["z"]["min"])
        ]
