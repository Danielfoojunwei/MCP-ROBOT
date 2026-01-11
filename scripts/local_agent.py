
import asyncio
import json
import sys
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_robot.server import mcp

# --- Configuration ---
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DEVICE = "cpu" # or "cuda" if available

class LocalRobotAgent:
    def __init__(self):
        print(f"Loading Local Agent: {MODEL_NAME}...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE)
        self.history = []
        
        # Define available tools text for the System Prompt
        self.tools_prompt = """You are a robot controller. You DO NOT chat. You ONLY output JSON.

AVAILABLE TOOLS:
1. submit_task(instruction: str)
   - Start a task.
2. execute_chunk(chunk_id: str)
   - Execute a plan chunk.

EXAMPLES:
User: "Pick up the red cube."
Assistant: {"tool": "submit_task", "args": {"instruction": "pick up red cube"}}

User: "Plan plan_123 is ready."
Assistant: {"tool": "execute_chunk", "args": {"chunk_id": "0"}}

User: "Chunk 0 executed."
Assistant: {"tool": "execute_chunk", "args": {"chunk_id": "1"}}

INSTRUCTIONS:
- Monitor the user input.
- Decide which tool to call.
- OUTPUT ONLY JSON.
"""

    def generate_response(self, user_input: str):
        # Construct messages
        messages = [
            {"role": "system", "content": self.tools_prompt},
        ]
        # Only keep last few turns to avoid context overflow
        messages.extend(self.history[-4:])
        messages.append({"role": "user", "content": user_input})
        
        # Apply chat template
        input_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer.encode(input_text, return_tensors="pt").to(DEVICE)
        
        # Generate with lower temp for deterministic JSON
        outputs = self.model.generate(inputs, max_new_tokens=100, temperature=0.01, do_sample=True, pad_token_id=self.tokenizer.eos_token_id)
        
        # Extract new tokens
        new_tokens = outputs[0][inputs.shape[1]:]
        response_content = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        
        return response_content.strip()

    async def run_loop(self):
        print("\n[Local Agent] Online. Waiting for commands...")
        
        # Initial Goal
        initial_goal = "Pick up the red cube from the table."
        print(f"User: {initial_goal}")
        self.history.append({"role": "user", "content": initial_goal})
        
        # 1. Agent Logic (Step 1: Planning)
        print("Thinking...")
        response = self.generate_response(initial_goal)
        print(f"Agent: {response}")
        self.history.append({"role": "assistant", "content": response})
        
        # Parse Tool Call
        tool_call = self._parse_json(response)
        if tool_call:
            result = await self._execute_tool(tool_call)
            print(f"Tool Result: {result}")
            
            # 2. Agent Logic (Step 2: Execution)
            # Feed result back to agent
            feedback_prompt = f"Tool output: {result}. What is the next step?"
            self.history.append({"role": "user", "content": feedback_prompt})
            
            print("Thinking...")
            response_2 = self.generate_response(feedback_prompt)
            print(f"Agent: {response_2}")
            self.history.append({"role": "assistant", "content": response_2})
            
            # Execute step 2 if valid
            tool_call_2 = self._parse_json(response_2)
            if tool_call_2:
                result_2 = await self._execute_tool(tool_call_2)
                print(f"Tool Result: {result_2}")

    def _parse_json(self, text):
        try:
            # Find closest JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                return json.loads(json_str)
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
        return "Unknown tool"

if __name__ == "__main__":
    agent = LocalRobotAgent()
    asyncio.run(agent.run_loop())
