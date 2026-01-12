import pytest
import asyncio
import json
import numpy as np
from mcp_robot.pipeline import MRCPUnifiedPipeline
from mcp_robot.contracts.schemas import RobotStateSnapshot, PerceptionSnapshot
from mcp_robot.runtime.determinism import DeterminismConfig, StableHasher, global_clock

@pytest.fixture
def deterministic_pipeline():
    config = DeterminismConfig(seed=42)
    global_clock.freeze(123456789.0)
    pipeline = MRCPUnifiedPipeline(robot_id="humanoid_test", config=config)
    return pipeline

@pytest.mark.asyncio
async def test_end_to_end_determinism(deterministic_pipeline):
    """
    Ensures identical instruction + snapshots => identical Plan JSON.
    """
    instruction = "Pick up the apple."
    
    state = RobotStateSnapshot(
        joint_names=["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7"],
        joint_positions=[0.0] * 7,
        base_vel=0.0,
        payload=0.0
    )
    
    perception = PerceptionSnapshot(
        camera_frame_digest="stable_frame",
        detected_objects=[{"type": "apple", "mass": 0.2, "friction_coefficient": 0.5}]
    )

    # First Run
    plan1 = await deterministic_pipeline.process_task(instruction, perception, state)
    json1 = json.dumps(plan1.model_dump(), sort_keys=True)

    # Second Run (on a fresh pipeline with same seeds/clock)
    global_clock.freeze(123456789.0)
    pipeline2 = MRCPUnifiedPipeline(robot_id="humanoid_test", config=DeterminismConfig(seed=42))
    plan2 = await pipeline2.process_task(instruction, perception, state)
    json2 = json.dumps(plan2.model_dump(), sort_keys=True)

    # Compare
    assert json1 == json2
    assert plan1.plan_id == plan2.plan_id
    print("\n[Test] Plan Determinism Verified: Bit-Identical JSON.")

@pytest.mark.asyncio
async def test_execution_idempotency(deterministic_pipeline):
    """
    Ensures executing the same chunk multiple times yields cached result.
    """
    instruction = "Move to table"
    state, perception = _mock_snapshots()
    
    plan = await deterministic_pipeline.process_task(instruction, perception, state)
    chunk_id = plan.chunks[0].chunk_id
    
    # Exec 1
    res1 = await deterministic_pipeline.execute_chunk(plan.plan_id, chunk_id)
    # Exec 2 (Should be instant cache hit)
    res2 = await deterministic_pipeline.execute_chunk(plan.plan_id, chunk_id)

    assert res1 == res2
    assert res1["status"] == "SUCCESS"

def _mock_snapshots():
    state = RobotStateSnapshot(
        joint_names=["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7"],
        joint_positions=[0.0] * 7
    )
    perception = PerceptionSnapshot(camera_frame_digest="test")
    return state, perception
