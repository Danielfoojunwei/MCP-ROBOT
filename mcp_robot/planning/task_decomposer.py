import numpy as np
import logging
from typing import List, Dict, Any, Optional
from mcp_robot.runtime.determinism import global_rng, StableHasher

class ALOHATaskDecomposer:
    """
    Tier 1: High-Level Planning (Deterministic ALOHA).
    Decomposes instructions into semantic subtasks using stable heuristics.
    """
    
    def __init__(self):
        logging.info("Loading Tier 1: Deterministic Task Decomposer...")
    
    async def decompose_task(
        self,
        task_instruction: str,
        vision_frame: Optional[np.ndarray] = None,
        detected_objects: List[Dict] = None
    ) -> List[Dict]:
        """
        Decompose task into semantic subtasks.
        - Uses StableHasher for pseudo-embeddings.
        - Rule-based parser for determinism.
        """
        if detected_objects is None:
            detected_objects = []

        # Generate a stable "embedding" digest for the instruction
        task_digest = StableHasher.sha256_json(task_instruction)
        
        logging.info(f"[Tier 1] Processing task: '{task_instruction}' (Digest: {task_digest[:8]})")
        
        # 1. Deterministic Semantic Parsing
        subtasks = []
        instruction_lower = task_instruction.lower()
        
        # Action Map: (Keyword -> Sequence of subtask types)
        action_map = {
            "pick": ["walk_to", "scan_workspace", "grasp_approach", "grasp_close", "lift"],
            "place": ["walk_to", "release"],
            "move": ["grasp_approach", "grasp_close", "lift", "move_to", "release"]
        }
        
        # Identify actions from instruction
        planned_actions = []
        for keyword, sequence in action_map.items():
            if keyword in instruction_lower:
                planned_actions.extend(sequence)
        
        if not planned_actions:
            planned_actions = ["idle"]

        # 2. Build Subtask Specs
        for i, action_type in enumerate(planned_actions):
            # Resolve target object from detected_objects or instruction
            target = self._resolve_target(action_type, instruction_lower, detected_objects)
            
            subtask = {
                "type": action_type,
                "target_object": target,
                "estimated_duration": self._get_duration(action_type),
                "criticality": self._assess_criticality(action_type),
                "force_requirements": "gentle" if "grasp_close" in action_type else "normal"
            }
            subtasks.append(subtask)
        
        return subtasks
    
    def _resolve_target(self, action_type: str, instruction: str, objects: List[Dict]) -> str:
        """Deterministically resolve the target object."""
        # Check if any detected object's type is in the instruction
        for obj in objects:
            if obj.get("type", "").lower() in instruction:
                return obj["type"]
        
        # Fallback to instruction keywords
        if "cube" in instruction: return "cube"
        if "apple" in instruction: return "apple"
        if "bin" in instruction: return "bin"
        
        return "object"

    def _get_duration(self, action_type: str) -> float:
        """Stable duration constants."""
        durations = {
            "walk_to": 4.0,
            "grasp_approach": 2.0,
            "grasp_close": 0.5,
            "lift": 1.0,
            "release": 0.5,
            "scan_workspace": 1.0,
            "idle": 0.0
        }
        return durations.get(action_type, 1.0)

    def _assess_criticality(self, action_type: str) -> str:
        """Deterministic criticality mapping."""
        if action_type in ["grasp_close", "lift", "release"]:
            return "high"
        elif action_type in ["grasp_approach", "move_to", "walk_to"]:
            return "medium"
        return "low"
