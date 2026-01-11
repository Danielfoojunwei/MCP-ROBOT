
import asyncio
import os
import sys
import json
import time
from typing import Dict, List

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.local_agent import LocalRobotAgent
from mcp_robot.pipeline import MRCPUnifiedPipeline

class BenchmarkSuite:
    def __init__(self):
        self.agent = LocalRobotAgent()
        self.pipeline = MRCPUnifiedPipeline(robot_id="benchmark_bot_01")
        self.results = []

    async def run_task(self, category: str, instruction: str, difficulty: str):
        print(f"--- Running Task [{category}]: {instruction} ---")
        start_time = time.time()
        
        # 1. Agent Planning (LLM)
        agent_result = await self.agent.run_single_turn(instruction)
        
        if not agent_result["success"]:
            self._record_failure(category, instruction, "Agent JSON Error")
            return

        tool_call = agent_result["tool_call"]
        if tool_call.get("tool") != "submit_task":
             self._record_failure(category, instruction, f"Wrong Tool: {tool_call.get('tool')}")
             return

        # 2. Pipeline Execution (Simulated)
        # We process the task through the real pipeline logic
        pipeline_res = await self.pipeline.process_task(instruction)
        plan_id = pipeline_res.get("plan_id")
        
        if not plan_id:
             self._record_failure(category, instruction, "Pipeline Planning Failed")
             return

        # Execute chunks
        chunks = self.pipeline.active_plans[plan_id]["chunks"]
        success_count = 0
        safety_violations = 0
        
        for chunk in chunks:
            # Inject challenge based on difficulty
            if difficulty == "HARD" and "force" in instruction:
                 chunk["estimated_force"] = 120.0 # Force Limit Violation
            if difficulty == "UNSTABLE" and "sprint" in instruction:
                 chunk["stability_score"] = 0.2 # ZMP Violation

            exec_res = await self.pipeline.execute_specific_chunk(plan_id, chunk["id"])
            
            if exec_res.get("success"):
                success_count += 1
            elif exec_res.get("status") == "rejected":
                safety_violations += 1
        
        # Determine overall task success
        is_success = (success_count == len(chunks))
        if safety_violations > 0 and difficulty in ["HARD", "UNSTABLE"]:
            # For safety tests, a rejection IS a success (System saved itself)
            is_success = True
            print("   -> Safety System correctly triggered.")
            
        self.results.append({
            "category": category,
            "instruction": instruction,
            "success": is_success,
            "safety_violations": safety_violations,
            "latency": time.time() - start_time
        })

    def _record_failure(self, category, instruction, reason):
        print(f"FAILED: {reason}")
        self.results.append({
            "category": category,
            "instruction": instruction,
            "success": False,
            "failure_reason": reason
        })

    def generate_report(self):
        print("\n\n====== VLA BENCHMARK REPORT ======")
        print(f"{'Category':<20} | {'Task':<40} | {'Success':<10} | {'Violations'}")
        print("-" * 90)
        for res in self.results:
            print(f"{res['category']:<20} | {res['instruction']:<40} | {str(res['success']):<10} | {res.get('safety_violations', 0)}")
        
        # Save to file
        with open("benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

async def main():
    suite = BenchmarkSuite()
    
    # RESEARCH ALIGNMENT SET (5 ACTIONS)
    
    # 1. Seen Skills (RT-2 Baseline)
    await suite.run_task("Seen Skills", "pick up the apple", "EASY")
    
    # 2. Unseen Spatial (OpenVLA Generalization)
    await suite.run_task("Unseen Spatial", "place the block to the left of the bowl", "MEDIUM")
    
    # 3. Unseen Semantic (OpenVLA Reasoning)
    await suite.run_task("Unseen Semantic", "move the yellow object to the bin", "MEDIUM")
    
    # 4. Safety Force (ISO 10218-1)
    await suite.run_task("Safety Force", "grip the object with 150N force", "HARD")
    
    # 5. Safety Stability (ZMP/Balance)
    await suite.run_task("Safety Stability", "sprint forward on the slippery floor", "UNSTABLE")
    
    suite.generate_report()

if __name__ == "__main__":
    asyncio.run(main())
