import hashlib
import json
import numpy as np
import time
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field

class DeterminismConfig(BaseModel):
    """Global configuration for deterministic execution."""
    seed: int = 42
    float_round: int = 6
    stable_json: bool = True
    deterministic_mode: bool = True

class StableHasher:
    """Provides stable hashing for JSON-serializable objects."""
    
    @staticmethod
    def sha256_json(obj: Any, float_round: int = 6) -> str:
        """
        Canonicalizes and hashes a JSON-serializable object.
        """
        def canonicalize(data):
            if hasattr(data, "model_dump"): # Handle Pydantic
                data = data.model_dump()
            
            if isinstance(data, dict):
                return {k: canonicalize(v) for k, v in sorted(data.items())}
            elif isinstance(data, list):
                return [canonicalize(i) for i in data]
            elif isinstance(data, float):
                return round(data, float_round)
            return data

        canonical_obj = canonicalize(obj)
        json_str = json.dumps(
            canonical_obj, 
            separators=(',', ':'), 
            sort_keys=True
        )
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

class Clock:
    """Robust clock that can be frozen globally."""
    def __init__(self):
        self._frozen_time: Optional[float] = None
    
    def now(self) -> float:
        if self._frozen_time is not None:
            return self._frozen_time
        return time.time()
    
    def freeze(self, value: float):
        self._frozen_time = value
    
    def unfreeze(self):
        self._frozen_time = None

class DeterministicRNG:
    """Seeded random number generator."""
    def __init__(self, seed: int):
        self.rng = np.random.default_rng(seed)
    
    def random(self, size: Optional[Union[int, tuple]] = None):
        return self.rng.random(size)

# Single global instance that persists
global_clock = Clock()
global_rng = DeterministicRNG(42)

def set_global_seed(seed: int):
    global global_rng
    global_rng = DeterministicRNG(seed)
