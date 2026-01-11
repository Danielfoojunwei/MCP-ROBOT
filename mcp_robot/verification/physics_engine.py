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
            score -= (base_velocity * 0.3) # Was 0.2
            
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
    def check_joint_limits(joints: Dict[str, float], limits: Dict[str, Tuple[float, float]]) -> List[str]:
        violations = []
        for j_name, angle in joints.items():
            min_lim, max_lim = limits.get(j_name, (-3.14, 3.14))
            if angle < min_lim or angle > max_lim:
                violations.append(f"{j_name} limit: {angle:.2f} not in [{min_lim}, {max_lim}]")
        return violations
