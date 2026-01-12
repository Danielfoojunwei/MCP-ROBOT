from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Optional, Any
import time

SCHEMA_VERSION = "2.0.0"

class RobotStateSnapshot(BaseModel):
    """
    A deterministic snapshot of the robot's physical state.
    Joints must be ordered consistently with the robot's joint_names.
    """
    joint_names: List[str]
    joint_positions: List[float]
    joint_velocities: Optional[List[float]] = None
    base_vel: float = 0.0
    payload: float = 0.0
    timestamp: Optional[float] = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode='after')
    def check_joint_alignment(self) -> 'RobotStateSnapshot':
        names = self.joint_names
        pos = self.joint_positions
        vel = self.joint_velocities
        
        if len(names) != len(pos):
            raise ValueError(f"Joint names count ({len(names)}) != positions count ({len(pos)})")
        if vel is not None and len(names) != len(vel):
            raise ValueError(f"Joint names count ({len(names)}) != velocities count ({len(vel)})")
        return self

    def to_ordered_dict(self) -> Dict[str, float]:
        """Returns joint positions as a name-mapped dictionary."""
        return {n: p for n, p in zip(self.joint_names, self.joint_positions)}

class PerceptionSnapshot(BaseModel):
    """
    A deterministic summary of the robot's sensory inputs.
    """
    camera_frame_digest: str
    detected_objects: List[Dict[str, Any]] = []
    tactile_summary: Dict[str, Any] = {}
    timestamp: Optional[float] = None
    schema_version: str = SCHEMA_VERSION

class JointState(BaseModel):
    """Represents a single waypoint in a joint trajectory."""
    names: List[str]
    positions: List[float] # Radians
    velocities: Optional[List[float]] = None
    effort: Optional[List[float]] = None
    
    @field_validator('names')
    @classmethod
    def check_names(cls, v: List[str]) -> List[str]:
        if not v: raise ValueError("Joint names cannot be empty")
        return v

    @model_validator(mode='after')
    def check_alignment(self) -> 'JointState':
        if self.names and self.positions and len(self.names) != len(self.positions):
             raise ValueError(f"Names count ({len(self.names)}) != Positions count ({len(self.positions)})")
        return self

class ActionChunk(BaseModel):
    """Base class for all deterministic execution units."""
    chunk_id: str
    plan_id: str
    ordinal: int
    type: str # 'trajectory', 'servo', 'gripper'
    timestamp: Optional[float] = None
    description: str
    schema_version: str = SCHEMA_VERSION

class JointTrajectoryChunk(ActionChunk):
    """Standard ROS-style Joint Trajectory."""
    type: str = "trajectory"
    joint_names: List[str]
    waypoints: List[JointState]
    duration: float # Expected seconds to complete
    max_force_est: float = 0.0
    stability_score: float = 1.0

class CartesianServoChunk(ActionChunk):
    """End-effector servo command."""
    type: str = "servo"
    frame_id: str
    target_pose: Dict[str, float] # {x,y,z, qx,qy,qz,qw}
    speed_scale: float = 1.0

class GripperCommandChunk(ActionChunk):
    """Binary or Scalar gripper command."""
    type: str = "gripper"
    width: float # 0.0 (closed) to 1.0 (open)
    max_force: float = 10.0 # Newtons

class TaskPlan(BaseModel):
    """A full sequence of actions derived from an instruction."""
    plan_id: str
    instruction: str
    input_digest: str
    config_digest: str
    chunks: List[JointTrajectoryChunk] # Using direct model for simplicity in this stage
    created_at: Optional[float] = None
    schema_version: str = SCHEMA_VERSION
