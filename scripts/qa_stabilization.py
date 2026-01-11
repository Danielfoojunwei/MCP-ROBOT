
import asyncio
import os
import sys
import json
import time

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_robot.server import mcp
from mcp_robot.pipeline import MRCPUnifiedPipeline
from mcp.types import CallToolRequest

class Color:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"

async def run_stress_test():
    print("--- Starting QA Stabilization Suite ---")
    pipeline = MRCPUnifiedPipeline(robot_id="humanoid_qa_01")
    
    # CASE 1: Nominal Flow
    print(f"\n{Color.GREEN}[TEST 1] Nominal Execution (OPTIMAL){Color.RESET}")
    task_res = await pipeline.process_task("clean table")
    plan_id = task_res.get("plan_id")
    chunk_0 = pipeline.active_plans[plan_id]["chunks"][0]
    
    # Inject OPTIMAL mock data
    chunk_0["stability_score"] = 0.9 # High stability
    chunk_0["estimated_force"] = 50.0
    
    res = await pipeline.execute_specific_chunk(chunk_0["id"])
    if res.get("success"):
        print("PASS: Nominal Execution succeeded.")
    else:
        print(f"FAIL: {res}")

    # CASE 2: Graceful Degradation
    print(f"\n{Color.YELLOW}[TEST 2] Degraded Execution (Safety Chip: MARGINAL){Color.RESET}")
    chunks = pipeline.active_plans[plan_id]["chunks"]
    chunk_1 = chunks[1] if len(chunks) > 1 else chunks[0]
    
    # Inject MARGINAL mock data
    chunk_1["stability_score"] = 0.45 # Marginal (should trigger DEGRADED)
    chunk_1["estimated_force"] = 80.0
    
    res = await pipeline.execute_specific_chunk(chunk_1["id"])
    # We can't easily capture stdout here without redirecting, but the logs will show "Reducing Low Force Limit"
    if res.get("success"):
        print("PASS: Degraded execution completed (Pipeline didn't crash).")
    else:
        print(f"FAIL: {res}")

    # CASE 3: Critical Failure (Safety Reject)
    print(f"\n{Color.RED}[TEST 3] Critical Safety Rejection (Safety Chip: UNSAFE){Color.RESET}")
    chunk_0 = pipeline.active_plans[plan_id]["chunks"][0] # Reuse chunk 0
    
    # Inject CRITICAL mock data
    chunk_0["stability_score"] = 0.1 # Very unstable
    
    res = await pipeline.execute_specific_chunk(chunk_0["id"])
    if res.get("status") == "rejected":
        print(f"PASS: Safety Chip correctly rejected action. Reason: {res.get('reason')}")
    else:
        print(f"FAIL: Action was NOT rejected! Result: {res}")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
