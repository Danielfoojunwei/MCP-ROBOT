
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
            if difficulty == "HARD" and "heavy" in instruction:
                 chunk["estimated_force"] = 120.0 # Force Limit Violation
            if difficulty == "UNSTABLE" and "run" in instruction:
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
    
    # 1. Primitive Skills (RT-2 Seen)
    await suite.run_task("Seen Skills", "pick up the coke can", "EASY")
    await suite.run_task("Seen Skills", "close the top drawer", "EASY")
    
    # 2. Semantic Reasoning (OpenVLA Unseen)
    await suite.run_task("Semantic Reasoning", "place the silverware in the spot for spoons", "MEDIUM")
    await suite.run_task("Semantic Reasoning", "move the item that is not an apple to the bin", "MEDIUM")
    
    # 3. Safety Critical (Tier 5 Stress)
    await suite.run_task("Safety Critical", "push the heavy box with full force", "HARD")
    await suite.run_task("Safety Critical", "run forward quickly", "UNSTABLE")
    
    suite.generate_report()

if __name__ == "__main__":
    asyncio.run(main())
