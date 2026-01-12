import logging
import numpy as np
from typing import Dict, List, Optional
from mcp_robot.runtime.determinism import global_clock
from mcp_robot.contracts.schemas import RobotStateSnapshot

class KinematicSimulator:
    """
    Deterministic Digital Twin.
    Maintains persistent joint state and physical parameters.
    """
    def __init__(self):
        self.joint_angles = {
            "joint_1": 0.0, "joint_2": 0.0, "joint_3": 0.0,
            "joint_4": 0.0, "joint_5": 0.0, "joint_6": 0.0, "joint_7": 0.0
        }
        self.payload_mass = 0.0
        self.base_velocity = 0.0
        self.last_update = global_clock.now()

    def update_payload(self, mass: float):
        self.payload_mass = mass

    def update_base_velocity(self, velocity: float):
        self.base_velocity = velocity

    def set_joint_state(self, new_angles: List[float]):
        keys = list(self.joint_angles.keys())
        for i, angle in enumerate(new_angles):
            if i < len(keys):
                self.joint_angles[keys[i]] = float(np.round(angle, 6))

    def step(self):
        self.last_update = global_clock.now()

    def get_state_vector(self) -> RobotStateSnapshot:
        """Returns typed snapshot for verification."""
        return RobotStateSnapshot(
            joint_names=list(self.joint_angles.keys()),
            joint_positions=list(self.joint_angles.values()),
            base_vel=self.base_velocity,
            payload=self.payload_mass,
            timestamp=self.last_update
        )
