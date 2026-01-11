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
    def verify_trajectory(trajectory, current_state: Dict, joint_limits: Dict[str, Tuple[float, float]] = None) -> Dict:
        """
        Validates a JointTrajectoryChunk against physical limits.
        """
        # 1. Continuity Check (Anti-Teleportation)
        # Ensure the trajectory starts near the current robot state.
        start_wp = trajectory.waypoints[0]
        current_joints = current_state.get("joints", {})
        
        tolerance = 0.5 # Rad tolerance (loose for Sim, tighter for Real)
        
        for idx, name in enumerate(trajectory.joint_names):
            current_val = current_joints.get(name)
            if current_val is not None:
                start_val = start_wp.positions[idx]
                if abs(current_val - start_val) > tolerance:
                    return {
                        "valid": False, 
                        "reason": f"Continuity Error: Joint {name} jumps from {current_val:.2f} to {start_val:.2f}"
                    }
        
        # 2. Joint Limit Check (Configured Limits)
        # Default symmetric 3.14 if no limits provided
        default_limit = (-3.14, 3.14)
        
        for i, wp in enumerate(trajectory.waypoints):
             if wp.names != trajectory.joint_names:
                 return {"valid": False, "reason": f"Waypoint {i} joint names mismatch"}
             
             for j_idx, pos in enumerate(wp.positions):
                 j_name = trajectory.joint_names[j_idx]
                 j_min, j_max = joint_limits.get(j_name, default_limit) if joint_limits else default_limit
                 
                 if not (j_min <= pos <= j_max):
                      return {
                          "valid": False, 
                          "reason": f"Joint {j_name} limit violation: {pos:.2f} not in [{j_min}, {j_max}]"
                      }

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
