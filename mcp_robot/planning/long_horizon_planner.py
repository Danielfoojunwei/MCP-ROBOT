import numpy as np
import logging
from typing import List, Dict, Optional
from mcp_robot.runtime.determinism import global_rng, StableHasher

class ACTLongHorizonPlanner:
    """
    Tier 2: Long-Horizon Planning (Deterministic ACT).
    Predicts action sequences from task context and subtasks.
    """
    
    def __init__(self):
        logging.info("Loading Tier 2: Deterministic ACT Planner...")
    
    async def plan_action_chunks(
        self,
        subtasks: List[Dict],
        current_frame: Optional[np.ndarray],
        robot_state: Dict,
        task_instruction: str
    ) -> Dict:
        """
        Deterministic planning of action chunks.
        """
        # 1. State/Task Digits
        task_digest = StableHasher.sha256_json(task_instruction)
        
        all_chunks = []
        global_chunk_idx = 0
        
        for subtask in subtasks:
            # Generate chunks for this subtask
            chunks = self._plan_subtask(subtask, task_digest, global_chunk_idx)
            all_chunks.extend(chunks)
            global_chunk_idx += len(chunks)
            
        return {
            "chunks": all_chunks,
            "total_chunks": len(all_chunks),
            "total_duration_s": sum(c["duration_s"] for c in all_chunks),
            "subtasks": subtasks
        }
    
    def _plan_subtask(self, subtask: Dict, task_digest: str, start_idx: int) -> List[Dict]:
        """Predict action chunks for a subtask using deterministic seeds."""
        
        # Timestep Constants (from Scope)
        TIMESTEPS_PER_CHUNK = 50
        HZ = 30
        CHUNK_DURATION = TIMESTEPS_PER_CHUNK / HZ # ~1.67s
        
        est_duration = subtask.get("estimated_duration", 2.0)
        num_chunks = max(1, int(est_duration / CHUNK_DURATION))
        
        chunks = []
        for i in range(num_chunks):
            # Create a unique latent seed for this specific chunk
            chunk_seed = StableHasher.sha256_json({
                "task_digest": task_digest,
                "subtask_type": subtask["type"],
                "ordinal": start_idx + i
            })
            
            # Use seed to generate deterministic "latents" (0.0 to 1.0)
            # We take first 8 chars of hex as int for seed
            chunk_rng = np.random.default_rng(int(chunk_seed[:8], 16))
            latent = chunk_rng.random(64)
            
            chunk = {
                "id": start_idx + i, # Temporary ID, pipeline will overwrite with hash
                "subtask_id": subtask["type"],
                "latent": latent.tolist(),
                "position_waypoints": self._generate_waypoints(latent, subtask["type"]),
                "force_profile": [float(latent[3] * 20.0)] * TIMESTEPS_PER_CHUNK,
                "duration_s": CHUNK_DURATION,
                "criticality": subtask["criticality"],
                "estimated_force": float(latent[4] * 100.0)
            }
            chunks.append(chunk)
            
        return chunks

    def _generate_waypoints(self, latent: np.ndarray, action_type: str) -> List[List[float]]:
        """Deterministic waypoint generation (Mock Forward Dynamics)."""
        # Map latent to a start/end delta
        # Typical workspace is around 0.5
        start_x, start_y, start_z = latent[0]*0.5, latent[1]*0.5, latent[2]*0.5
        
        # Define movement based on action type
        dx, dy, dz = 0.0, 0.0, 0.0
        if action_type == "lift": dz = 0.2
        elif action_type == "walk_to": dx = 0.3
        elif action_type == "grasp_approach": dz = -0.1
        
        waypoints = []
        for i in range(50):
            alpha = i / 49.0
            waypoints.append([
                float(start_x + alpha * dx),
                float(start_y + alpha * dy),
                float(start_z + alpha * dz)
            ])
        return waypoints
