import numpy as np
import logging
from typing import List, Dict, Optional
from mcp_robot.runtime.determinism import StableHasher

class VisioTactileActionEncoder:
    """
    Tier 3: Deterministic Action Encoding.
    Augments chunks with tactile guidance and stability metadata.
    """
    
    def __init__(self, robot_profile: Dict, tactile_db: Dict):
        logging.info("Loading Tier 3: Deterministic Visio-Tactile Encoder...")
        self.robot_profile = robot_profile
        self.tactile_db = tactile_db
    
    async def augment_chunks_with_tactile(
        self,
        chunks: List[Dict],
        camera_frame: Optional[np.ndarray],
        detected_objects: List[Dict],
        current_tactile: Dict
    ) -> List[Dict]:
        """
        Augment action chunks with tactile guidance based on PerceptionSnapshot.
        """
        augmented_chunks = []
        
        for chunk in chunks:
            # 1. Resolve Target Object Deterministically
            target_obj = self._resolve_target(chunk, detected_objects)
            
            # 2. Derive Tactile Profile
            # Note: Friction/Slip parameters are derived from targeted object metadata
            friction = target_obj.get("friction_coefficient", 0.5)
            mass = target_obj.get("mass", 0.2)
            
            waypoints = chunk["position_waypoints"]
            tactile_waypoints = []
            
            for wp in waypoints:
                # 3. Compute Safe Grip Force (Deterministic Formula)
                grip_force = self._calculate_grip_force(mass, friction)
                
                # 4. Predict ZMP Shift (Deterministic Kinematic Approximation)
                # Waypoint [x, y, z] normalized. Support polygon center at 0.5, 0.5
                zmp = {
                    "x": round((wp[0] - 0.5) * 0.1, 4),
                    "y": round((wp[1] - 0.5) * 0.1, 4)
                }

                tactile_waypoints.append({
                    "position": wp,
                    "grip_force_n": grip_force,
                    "predicted_friction": friction,
                    "slip_threshold": round(grip_force * 0.2, 4),
                    "slip_recovery": "automatic_force_increase",
                    "monitor_tactile": chunk["criticality"] == "high",
                    "predicted_zmp": zmp
                })
            
            augmented_chunk = chunk.copy()
            augmented_chunk["tactile_waypoints"] = tactile_waypoints
            augmented_chunk["is_tactile_critical"] = chunk["criticality"] in ["high", "medium"]
            augmented_chunks.append(augmented_chunk)
        
        return augmented_chunks
    
    def _resolve_target(self, chunk: Dict, detected_objects: List[Dict]) -> Dict:
        """Find the targeted object in the perception snapshot."""
        target_name = chunk.get("target_object", "unknown")
        for obj in detected_objects:
            if obj.get("type") == target_name:
                return obj
        return {"type": "default", "mass": 0.2, "friction_coefficient": 0.5}

    def _calculate_grip_force(self, mass_kg: float, friction: float) -> float:
        """Safe grip force formula: F = (m*g / mu * n_fingers) * safety_factor"""
        G = 9.81
        NUM_FINGERS = 2
        SAFETY_FACTOR = 1.5
        
        min_force = (mass_kg * G) / (friction * NUM_FINGERS)
        safe_force = min_force * SAFETY_FACTOR
        
        max_robot_force = self.robot_profile.get("gripper", {}).get("max_force_n", 100.0)
        return round(min(safe_force, max_robot_force * 0.8), 4)
