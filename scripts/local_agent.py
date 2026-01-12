import torch
import json
import asyncio
import sys
import os
import random
import numpy as np
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_robot.server import mcp
from mcp_robot.runtime.determinism import set_global_seed

# --- Configuration ---
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DEVICE = "cpu"
DETERMINISTIC_SEED = 42

def enforce_determinism(seed: int):
    """Set all possible seeds for reproducible inference."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    set_global_seed(seed)
    # Transformers/PyTorch deterministic flags
    torch.use_deterministic_algorithms(True, warn_only=True)

class LocalRobotAgent:
    def __init__(self):
        logging.info(f"Loading Local Agent: {MODEL_NAME} (Deterministic)...")
        enforce_determinism(DETERMINISTIC_SEED)
        
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE)
        self.model.eval() # Set to evaluation mode
        
        self.history = []
        self.tools_prompt = """You are a robot controller. You DO NOT chat. 
        
CRITICAL PROTOCOL:
1. First, think about the request. Is it a new command?
2. If it is a NEW command, you MUST call `submit_task` FIRST.
3. You can ONLY use `execute_chunk` if a plan is ALREADY ready.

RESPONSE FORMAT:
Thought: [Your reasoning here]
JSON: {"tool": "...", "args": {...}}
"""

    def generate_response(self, user_input: str):
        # Construct messages
        messages = [{"role": "system", "content": self.tools_prompt}]
        messages.extend(self.history[-4:])
        messages.append({"role": "user", "content": user_input})
        
        input_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer.encode(input_text, return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs, 
                max_new_tokens=150, 
                temperature=0.0,   # Zero Temp for Determinism
                do_sample=False,   # Greedy Decoding
                pad_token_id=self.tokenizer.eos_token_id
            )
            
        new_tokens = outputs[0][inputs.shape[1]:]
        response_content = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        return response_content

    async def run_single_turn(self, instruction: str) -> str:
        """Process turn and return the tool result."""
        logging.info(f"[Agent] Input: '{instruction}'")
        response = self.generate_response(instruction)
        logging.info(f"[Agent] Response: {response}")
        
        tool_call = self._parse_json(response)
        if tool_call:
            result = await self._execute_tool(tool_call)
            return result
        return "ERROR: No tool call generated."

    def _parse_json(self, text):
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
        except Exception:
            pass
        return None

    async def _execute_tool(self, tool_call):
        name = tool_call.get("tool")
        args = tool_call.get("args", {})
        
        if name == "submit_task":
            return await mcp.call_tool("submit_task", arguments=args)
        elif name == "execute_chunk":
            return await mcp.call_tool("execute_chunk", arguments=args)
        elif name == "stabilize":
            return await mcp.call_tool("stabilize", arguments={})
        return f"Unknown tool: {name}"

    async def run_loop(self):
        print("\n[Local Agent] Online (Deterministic Mode).")
        # Example interaction
        instruction = "Pick up the apple."
        res1 = await self.run_single_turn(instruction)
        print(f"Result 1: {res1}")
        
        try:
             plan_id = json.loads(res1).get("plan_id")
             if plan_id:
                  chunk_exec = await self.run_single_turn(f"Plan {plan_id} generated. Execute first chunk.")
                  print(f"Result 2: {chunk_exec}")
        except:
             pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = LocalRobotAgent()
    asyncio.run(agent.run_loop())
