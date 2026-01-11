
import numpy as np
import asyncio
from typing import List, Dict

# Mock Loaders
# Deterministic Encoders for Research Reproducibility
def load_vision_encoder():
    class DeterministicVis:
         def encode(self, frame): 
             # Use mean of frame to create a semi-semantic but stable embedding
             return np.full(256, np.mean(frame) if frame is not None else 0.5)
    return DeterministicVis()

def load_task_embedder():
    class DeterministicEmb:
        def encode(self, text): 
            # Simple hash-based embedding
            val = sum(ord(c) for c in text) % 256 / 256.0
            return np.full(256, val)
    return DeterministicEmb()

class TransformerDecoderForPlanning:
    def predict(self, vision, task, subtask_spec, num_chunks):
        # Return deterministic latents derived from vision + task + spec
        # This replaces the purely random simulation and ensures consistency across runs.
        seed_val = np.mean(vision) + np.mean(task) + np.mean(subtask_spec)
        return [np.full(64, (seed_val + i*0.1) % 1.0) for i in range(num_chunks)]

class ACTLongHorizonPlanner:
    """
    Tier 2: Long-Horizon Planning (ACT Transformer)
    From ACT paper: Predict long action sequences (100+ chunks) from task + perception.
    """
    
    def __init__(self):
        print("Loading Tier 2: ACT Planner...")
        self.vision_encoder = load_vision_encoder()
        self.transformer = TransformerDecoderForPlanning()
        self.task_embedder = load_task_embedder()
    
    async def plan_action_chunks(
        self,
        subtasks: List[Dict],
        current_frame: np.ndarray,
        robot_state: Dict,
        task_instruction: str
    ) -> Dict:
        """
        Plan full action sequence across all subtasks.
        Returns action chunks with latent representations.
        """
        
        # Encode current observation
        if current_frame is None:
             current_frame = np.zeros((224, 224, 3))
        vision_emb = self.vision_encoder.encode(current_frame)
        
        # Encode task
        task_emb = self.task_embedder.encode(task_instruction)
        
        # For each subtask, generate chunks
        all_chunks = []
        chunk_id = 0
        
        for subtask in subtasks:
            # Predict action chunks for this subtask
            subtask_chunks = await self._plan_subtask_chunks(
                subtask=subtask,
                vision_context=vision_emb,
                task_context=task_emb,
                robot_state=robot_state,
                start_chunk_id=chunk_id
            )
            
            all_chunks.extend(subtask_chunks)
            chunk_id += len(subtask_chunks)
        
        return {
            "chunks": all_chunks,
            "total_chunks": len(all_chunks),
            "total_duration_s": len(all_chunks) * (50 / 30),  # 50 timesteps per chunk
            "subtasks": subtasks
        }
    
    async def _plan_subtask_chunks(
        self,
        subtask: Dict,
        vision_context: np.ndarray,
        task_context: np.ndarray,
        robot_state: Dict,
        start_chunk_id: int
    ) -> List[Dict]:
        """
        Plan action chunks for single subtask using transformer.
        """
        
        # Estimate number of chunks needed for this subtask
        est_duration = subtask.get("estimated_duration", 2.0)
        num_chunks = max(1, int(est_duration / (50/30)))  # chunks = seconds / chunk_duration
        
        # Use transformer to predict latent chunk representations
        latent_chunks = self.transformer.predict(
            vision=vision_context,
            task=task_context,
            subtask_spec=self._encode_subtask(subtask),
            num_chunks=num_chunks
        )
        
        # Decode latents to action chunks
        chunks = []
        for i, latent in enumerate(latent_chunks):
            chunk = {
                "id": start_chunk_id + i,
                "subtask_id": subtask["type"],
                "latent": latent.tolist(), # Serialize for JSON
                "position_waypoints": self._decode_positions(latent),
                "force_profile": self._decode_forces(latent),
                "duration_s": 50 / 30,
                "criticality": subtask["criticality"]
            }
            chunks.append(chunk)
        
        return chunks
    
    def _encode_subtask(self, subtask: Dict) -> np.ndarray:
        """Encode subtask specification as vector."""
        # Map task type to a unique float for the transformer seed
        type_map = {"walk_to": 0.1, "pick": 0.2, "place": 0.3, "scan": 0.4}
        val = type_map.get(subtask.get("type", "unknown"), 0.5)
        return np.full(32, val)
    
    def _decode_positions(self, latent: np.ndarray) -> List[List[float]]:
        # Deterministic: 50 waypoints per chunk
        # Creates a smooth movement trajectory starting from 'latent' seed
        base_x, base_y, base_z = latent[0]*0.5, latent[1]*0.5, latent[2]*0.5
        return [[base_x + i*0.005, base_y, base_z] for i in range(50)]

    def _decode_forces(self, latent: np.ndarray) -> List[float]:
        # Deterministic force profile
        return [latent[3] * 20.0 for _ in range(50)]
