
import numpy as np
from typing import List, Dict

# Mock IK Solver
class IKSolver:
    def solve(self, world_pos):
        """
        Simple Pseudo-IK for a humanoid leg/arm chain.
        Varies joints based on XYZ to provide functional feedback to Tiers 5/6.
        """
        x, y, z = world_pos
        # This provides a deterministic mapping so Tiers 5/6 can observe movement
        return [
            np.clip(x * 1.5, -0.5, 0.5),      # hip_yaw
            np.clip(y * 1.5, -0.3, 0.3),      # hip_roll
            np.clip((z - 0.5) * 2.0, -1.0, 1.0), # hip_pitch
            np.clip(-z * 2.5, -2.0, 0.0),     # knee_pitch
            np.clip(z * 1.2, -0.5, 0.5),      # ankle_pitch
            np.clip(y * 0.8, -0.3, 0.3),      # ankle_roll
            0.0                               # extra/gripper
        ]

class UniversalActionEncoder:
    """
    Tier 4: Universal Mapping (UMI Encoder)
    Maps normalized 0-1 actions to Target Robot Hardware Coordinates.
    """
    
    def __init__(self, robot_profiles: Dict):
        print("Loading Tier 4: Universal Mapper...")
        self.robot_profiles = robot_profiles
        self.ik_solver = dict()
        
        for robot_id, profile in robot_profiles.items():
            self.ik_solver[robot_id] = IKSolver() # In real impl, load per profile
    
    async def map_chunks_to_robot(
        self,
        chunks: List[Dict],
        target_robot_id: str,
        wrist_frame: np.ndarray,
        overhead_frame: np.ndarray
    ) -> List[Dict]:
        """
        Map universal action chunks to target robot's joint space.
        """
        if target_robot_id not in self.robot_profiles:
             print(f"Warning: Robot {target_robot_id} not found in profiles.")
             return chunks

        target_profile = self.robot_profiles[target_robot_id]
        mapped_chunks = []
        
        for chunk in chunks:
            # Decode waypoints to normalized positions (0-1)
            waypoints = chunk.get("tactile_waypoints", chunk.get("position_waypoints", []))
            
            # For each waypoint, convert to robot's hardware coordinates
            hardware_waypoints = []
            hardware_forces = []
            
            for waypoint in waypoints:
                 # Logic to handle both simple waypoints [x,y,z] and tactile dicts
                if isinstance(waypoint, dict):
                     pos = waypoint["position"]
                     grip_force = waypoint.get("grip_force_n", 50)
                else:
                     pos = waypoint
                     grip_force = 50
                
                # Denormalize to world coordinates (XYZ)
                world_pos = self._denormalize_to_world(
                    pos,
                    target_profile["workspace"]
                )
                
                # Solve inverse kinematics -> Joint Angles
                joint_angles = self.ik_solver[target_robot_id].solve(world_pos)
                
                hardware_waypoints.append(joint_angles)
                
                # Adapt grip force
                adapted_force = self._adapt_grip_force_to_robot(
                    grip_force,
                    target_profile.get("gripper", {})
                )
                hardware_forces.append(adapted_force)
            
            # Create mapped chunk
            mapped_chunk = chunk.copy()
            mapped_chunk["hardware_waypoints"] = hardware_waypoints
            mapped_chunk["hardware_forces"] = hardware_forces
            mapped_chunk["target_robot"] = target_robot_id
            mapped_chunk["joint_names"] = target_profile.get("joint_names", [])
            
            mapped_chunks.append(mapped_chunk)
        
        return mapped_chunks
    
    def _denormalize_to_world(
        self,
        normalized_pos: List[float],
        workspace: Dict
    ) -> List[float]:
        """Convert 0-1 normalized position to world coordinates."""
        return [
            workspace["x"]["min"] + normalized_pos[0] * (workspace["x"]["max"] - workspace["x"]["min"]),
            workspace["y"]["min"] + normalized_pos[1] * (workspace["y"]["max"] - workspace["y"]["min"]),
            workspace["z"]["min"] + normalized_pos[2] * (workspace["z"]["max"] - workspace["z"]["min"])
        ]
        
    def _adapt_grip_force_to_robot(self, force, gripper_profile):
        return min(force, gripper_profile.get("max_force_n", 60))
