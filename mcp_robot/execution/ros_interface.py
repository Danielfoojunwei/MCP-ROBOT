import asyncio
import logging
from typing import Dict, Optional
from mcp_robot.contracts.schemas import JointTrajectoryChunk
from mcp_robot.execution.ros_helpers import (
    ROS_AVAILABLE, Node, ROSActionWrapper, to_ros_duration,
    FollowJointTrajectory, JointTrajectoryPoint
)
from mcp_robot.runtime.determinism import global_clock

class ROS2Adapter:
    """
    Tier 6: Deterministic Execution Bridge.
    Supports HARDWARE (rclpy) and SIM (Deterministic Tick) modes.
    """
    
    def __init__(self, robot_id: str, execution_mode: str = "SIM"):
        self.robot_id = robot_id
        self.mode = execution_mode
        self.node = None
        self.trajectory_client = None
        
        logging.info(f"[Tier 6] Initializing ROS2Adapter in {self.mode} mode.")
        
        if self.mode == "HARDWARE" and ROS_AVAILABLE:
            self._init_ros_node()
        elif self.mode == "HARDWARE":
            logging.warning("HARDWARE mode requested but ROS2 not available. Falling back to SIM.")
            self.mode = "SIM"

    def _init_ros_node(self):
        """Initialize real ROS2 infrastructure."""
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        
        if not rclpy.ok():
            rclpy.init()
            
        self.node = Node(f"mcp_robot_adapter_{self.robot_id}")
        self.trajectory_client = ROSActionWrapper(
            self.node, 
            FollowJointTrajectory, 
            "/joint_trajectory_controller/follow_joint_trajectory"
        )
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)

    async def execute_trajectory(self, trajectory: JointTrajectoryChunk) -> Dict:
        """
        Main execution entrypoint.
        """
        if self.mode == "SIM":
            return self._simulate_execution(trajectory)
        else:
            return await self._execute_hardware(trajectory)

    async def _execute_hardware(self, trajectory: JointTrajectoryChunk) -> Dict:
        """Real ROS2 Action Call with proper awaiting."""
        if not self.trajectory_client.wait_for_server(timeout_sec=5.0):
            return {"success": False, "error_code": -1, "reason": "Action Server Timeout"}
            
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory.joint_names = trajectory.joint_names
        
        # Mapping all waypoints to ROS points
        for wp in trajectory.waypoints:
            point = JointTrajectoryPoint()
            point.positions = wp.positions
            # Use chunk duration as total time for this simplified mapping
            point.time_from_start = to_ros_duration(trajectory.duration)
            goal_msg.trajectory.points.append(point)
        
        logging.info(f"[Tier 6] Sending goal to hardware...")
        
        # Actual rclpy-asyncio bridge
        # send_goal_async returns a future
        send_goal_future = self.trajectory_client.client.send_goal_async(goal_msg)
        goal_handle = await send_goal_future
        
        if not goal_handle.accepted:
            return {"success": False, "reason": "Goal Rejected by ROS Controller"}
            
        result_future = goal_handle.get_result_async()
        result = await result_future
        
        return {
            "success": result.status == 4, # 4 = SUCCEEDED in action_msgs
            "error_code": result.status,
            "reason": "Hardware Execution Complete"
        }

    def _simulate_execution(self, trajectory: JointTrajectoryChunk) -> Dict:
        """
        Deterministic SIM Execution.
        - NO asyncio.sleep (no wall-clock dependency).
        - State is updated instantaneously in the Digital Twin by the Pipeline.
        """
        logging.info(f"[Tier 6] [SIM] Deterministic Step: {trajectory.chunk_id}")
        
        return {
            "success": True, 
            "error_code": 0,
            "reason": "Simulated Step Complete (Deterministic)"
        }
