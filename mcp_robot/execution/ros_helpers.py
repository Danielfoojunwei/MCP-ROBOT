import logging
import time
from typing import Optional, Any, Dict

# Try importing ROS2 libraries
try:
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
    from control_msgs.action import FollowJointTrajectory
    from trajectory_msgs.msg import JointTrajectoryPoint
    from builtin_interfaces.msg import Duration
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False
    # Mock classes for Type Hinting / Sim Mode
    class Node: pass
    class QoSProfile: 
        def __init__(self, **kwargs): pass
    class QoSReliabilityPolicy:
        RELIABLE = 1
        BEST_EFFORT = 2
    class QoSHistoryPolicy:
        KEEP_LAST = 1
    class QoSDurabilityPolicy:
        VOLATILE = 1
        TRANSIENT_LOCAL = 2
    
    # Mock Message Types
    class JointTrajectoryPoint:
        def __init__(self):
            self.positions = []
            self.velocities = []
            self.time_from_start = None

    class Duration:
        def __init__(self, sec=0, nanosec=0):
            pass

    class FollowJointTrajectory:
        class Goal:
            def __init__(self):
                self.trajectory = type('Trajectory', (), {})()
                self.trajectory.joint_names = []
                self.trajectory.points = []

def get_production_qos(reliability: str = "RELIABLE") -> QoSProfile:
    """
    Returns a production-hardened QoS Profile.
    Matches settings used in Nav2 and standard drivers.
    """
    if reliability == "BEST_EFFORT":
        return QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
    else:
        # Default: Reliable (TCP-like)
        return QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=10
        )

def to_ros_duration(seconds: float) -> Any:
    """Converts float seconds to builtin_interfaces.msg.Duration"""
    if not ROS_AVAILABLE: return None
    
    sec = int(seconds)
    nanosec = int((seconds - sec) * 1e9)
    return Duration(sec=sec, nanosec=nanosec)

class ROSActionWrapper:
    """
    Wraps a ROS2 Action Client with connection watchdog and type safety.
    """
    def __init__(self, node: Node, action_type: Any, action_name: str):
        self.node = node
        self.action_name = action_name
        self.client = None
        
        if ROS_AVAILABLE:
            self.client = ActionClient(node, action_type, action_name)
    
    def wait_for_server(self, timeout_sec: float = 5.0) -> bool:
        if not self.client: return False
        return self.client.wait_for_server(timeout_sec=timeout_sec)
    
    def destroy(self):
        if self.client:
            self.client.destroy()
