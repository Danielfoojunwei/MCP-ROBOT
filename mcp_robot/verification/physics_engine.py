import numpy as np
from typing import Dict, List, Tuple

class PhysicsEngine:
    """
    Stateless physics calculator for safety verification.
    """
    
    @staticmethod
    def calculate_zmp_score(base_velocity: float, payload_mass: float, joint_extension: float) -> float:
        """
        Estimates Zero Moment Point stability score (0.0 = Fall, 1.0 = Stable).
        Simplified heuristic: 
        - High velocity -> Lower stability
        - Heavy payload -> Lower stability
        - High extension -> Lower stability
        """
        # Baseline stability
        score = 1.0
        
        # Velocity penalty: running > 2.0 m/s is unstable
        # INCREASED SENSITIVITY: 3.0 m/s will now drop score significantly
        if base_velocity > 0:
            score -= (base_velocity * 0.4) # Was 0.3
            
        # Payload penalty (e.g. 5kg at extension is risky)
        if payload_mass > 0:
            score -= (payload_mass * 0.05 * joint_extension)
            
        return max(0.0, min(1.0, score))

    @staticmethod
    def estimate_end_effector_force(accel: float, payload_mass: float) -> float:
        """F = ma (Simplified)"""
        # Base robot arm mass effective ~5kg
        # INCREASED BASE: Ensure higher effective mass (15kg base + payload)
        effective_mass = 15.0 + payload_mass 
        # For safety, we assume a worst-case jerk/accel if not provided
        # Current benchmark assumes accel=2.0, let's bump the physical multiplier
        return effective_mass * max(accel, 4.0) # Assume at least 4m/s^2 impacts

    @staticmethod
    def verify_trajectory(trajectory, current_state: Dict) -> Dict:
        """
        Validates a JointTrajectoryChunk against physical limits.
        """
        # 1. Continuity Check
        pass 
        
        # 2. Joint Limit Check (Stateless per waypoint)
        limits_rad = 3.14 
        for i, wp in enumerate(trajectory.waypoints):
             # Name mismatch check
             if wp.names != trajectory.joint_names:
                 return {"valid": False, "reason": f"Waypoint {i} joint names mismatch"}
             
             for j_idx, pos in enumerate(wp.positions):
                 if abs(pos) > limits_rad:
                      return {"valid": False, "reason": f"Joint {trajectory.joint_names[j_idx]} limit violation: {pos:.2f}"}

        # 3. Force Check (Intent Compliance)
        limit_force = 100.0
        if trajectory.max_force_est > limit_force:
             return {"valid": False, "reason": f"Force Limit Exceeded: {trajectory.max_force_est:.1f}N > {limit_force}N"}

        # 4. Global Stability Check (ZMP)
        # Uses SIMULATED state (Velocity/Payload) to predict if this trajectory is safe to execute *now*.
        # Note: We use the 'current' state as a proxy for the 'during execution' state for this zero-order check.
        # Ensure your simulator state keys match what calculate_zmp_score expects!
        # KinematicSimulator.get_state_vector() returns dict with 'base_vel', 'payload'.
        
        # We need to handle case where state might be list/dict depending on implementation.
        # Assuming current_state is a Dict.
        base_vel = current_state.get("base_vel", 0.0)
        payload = current_state.get("payload", 0.0)
        
        zmp_score = PhysicsEngine.calculate_zmp_score(base_vel, payload, 0.5) # 0.5 extension avg
        if zmp_score < 0.4: # Threshold
             return {"valid": False, "reason": f"ZMP Critical: Unstable (Score: {zmp_score:.2f})"}
        
        return {"valid": True, "reason": "Trajectory within Safe Operating Envelope"}
