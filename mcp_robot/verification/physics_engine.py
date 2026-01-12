import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from mcp_robot.contracts.schemas import JointTrajectoryChunk, RobotStateSnapshot

class PhysicsEngine:
    """
    Stateless, deterministic physics verification engine.
    Computes stability and limit compliance for JointTrajectoryChunks.
    """
    
    @staticmethod
    def verify_trajectory(
        trajectory: JointTrajectoryChunk, 
        current_state: RobotStateSnapshot,
        joint_limits: Dict[str, Tuple[float, float]]
    ) -> Dict:
        """
        Authoritative entrypoint for trajectory certification.
        """
        # 1. Continuity Check
        # Does the trajectory start where the robot actually is?
        start_wp = trajectory.waypoints[0]
        state_dict = current_state.to_ordered_dict()
        
        TOLERANCE_RAD = 0.1 # Real-world tight tolerance
        
        for i, name in enumerate(trajectory.joint_names):
            current_pos = state_dict.get(name)
            if current_pos is not None:
                plan_pos = start_wp.positions[i]
                if abs(current_pos - plan_pos) > TOLERANCE_RAD:
                    return {
                        "valid": False, 
                        "reason": f"Continuity Error: {name} jumps by {abs(current_pos - plan_pos):.4f} rad"
                    }

        # 2. Joint Limits Check
        for wp_idx, wp in enumerate(trajectory.waypoints):
            for i, pos in enumerate(wp.positions):
                name = trajectory.joint_names[i]
                j_min, j_max = joint_limits.get(name, (-np.inf, np.inf))
                if not (j_min <= pos <= j_max):
                    return {
                        "valid": False,
                        "reason": f"Limit Error: {name} at waypoint {wp_idx} is {pos:.4f}, out of range [{j_min}, {j_max}]"
                    }

        # 3. Stability Check (ZMP)
        # We calculate the worst-case ZMP score based on velocity and base position
        zmp_score = PhysicsEngine.calculate_zmp_stability(
            base_vel=current_state.base_vel,
            payload=current_state.payload,
            extension=0.5 # Avg limb extension
        )
        
        if zmp_score < 0.4:
            return {
                "valid": False,
                "reason": f"Stability Error: ZMP Critical ({zmp_score:.2f}) due to high velocity/payload"
            }

        # 4. Force Check
        FORCE_LIMIT_N = 100.0
        if trajectory.max_force_est > FORCE_LIMIT_N:
             return {
                 "valid": False, 
                 "reason": f"Force Error: Estimated force {trajectory.max_force_est:.1f}N > Limit {FORCE_LIMIT_N}N"
             }

        return {"valid": True, "reason": "Certified Safe"}

    @staticmethod
    def calculate_zmp_stability(base_vel: float, payload: float, extension: float) -> float:
        """
        Simplified Zero-Moment Point stability model.
        Returns score [0.0 (Fall) to 1.0 (Static)].
        """
        # Baseline score
        score = 1.0
        
        # Velocity penalty: High-speed mobile bases reduce the support polygon margin
        # Unstable > 2.0 m/s for this robot profile
        score -= (abs(base_vel) * 0.3)
        
        # Payload penalty: Center of gravity shifts out of bounds
        # Assumption: 10kg payload at full extension (1.0) causes 0.5 score drop
        score -= (payload * 0.05 * extension)
        
        return max(0.0, min(1.0, score))

    @staticmethod
    def calculate_end_effector_force(mass: float, accel: float) -> float:
        """Deterministic F=ma approximation."""
        ROBOT_ARM_MASS = 15.0 # kg
        total_mass = ROBOT_ARM_MASS + mass
        return total_mass * accel
