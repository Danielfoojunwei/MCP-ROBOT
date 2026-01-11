from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import time

class JointState(BaseModel):
    """Represents a single snapshot of joint configurations."""
    names: List[str]
    positions: List[float] # Radians
    velocities: Optional[List[float]] = None
    effort: Optional[List[float]] = None
    
    @validator('names')
    def check_names(cls, v):
        if not v: raise ValueError("Joint names cannot be empty")
        return v

    @validator('positions')
    def check_len(cls, v, values):
        if 'names' in values and len(v) != len(values['names']):
            raise ValueError(f"Position count {len(v)} must match name count {len(values['names'])}")
        return v

class ActionChunk(BaseModel):
    """Base class for all discrete execution units."""
    id: str
    type: str # 'trajectory', 'servo', 'gripper'
    timestamp: float = Field(default_factory=time.time)
    description: str

class JointTrajectoryChunk(ActionChunk):
    """
    Standard ROS-style Joint Trajectory.
    Tier 6 will execute this via FollowJointTrajectory.
    """
    type: str = "trajectory"
    joint_names: List[str]
    waypoints: List[JointState]
    duration: float # Expected seconds to complete
    
    # Safety Metadata (Populated by Physics Engine)
    max_force_est: float = 0.0
    stability_score: float = 1.0

class CartesianServoChunk(ActionChunk):
    """
    End-effector servo command (e.g. MoveIt Servo / Teleop).
    """
    type: str = "servo"
    frame_id: str
    target_pose: Dict[str, float] # {x,y,z, qx,qy,qz,qw}
    speed_scale: float = 1.0

class GripperCommandChunk(ActionChunk):
    """
    Binary or Scalar gripper command.
    """
    type: str = "gripper"
    width: float # 0.0 (closed) to 1.0 (open)
    max_force: float = 10.0 # Newtons
