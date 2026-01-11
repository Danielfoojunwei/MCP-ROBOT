
import json
import torch
import sys
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DEVICE = "cpu"

class PromptEvaluator:
    def __init__(self):
        print(f"Loading Model: {MODEL_NAME}...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(DEVICE)
    
    def evaluate_prompt(self, system_prompt: str, test_cases: List[str]) -> Dict:
        """
        Runs the model with the given `system_prompt` against all `test_cases`.
        Returns statistics.
        """
        results = []
        parsed_tools = []
        
        print("\n--- Starting Evaluation ---")
        for i, user_input in enumerate(test_cases):
            print(f"Test {i+1}: '{user_input}'", end=" -> ")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            input_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer.encode(input_text, return_tensors="pt").to(DEVICE)
            
            outputs = self.model.generate(
                inputs, 
                max_new_tokens=100, 
                temperature=0.1, 
                do_sample=True, # Low temp for consistency
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True).strip()
            
            # Analyze Result
            tool_name = "unknown"
            valid_plan = False
            
            try:
                # Naive JSON extraction
                if "{" in response:
                    json_str = response[response.find("{"):response.rfind("}")+1]
                    data = json.loads(json_str)
                    tool_name = data.get("tool", "unknown")
                    
                    # PASS CONDITION: Must use 'submit_task'. 
                    # 'execute_chunk' is a FAIL for a new user request.
                    if tool_name == "submit_task":
                        valid_plan = True
            except:
                pass
            
            print(f"Tool: {tool_name} | Pass: {valid_plan}")
            results.append({"input": user_input, "response": response, "tool": tool_name, "pass": valid_plan})
            
        score = sum([1 for r in results if r["pass"]]) / len(results)
        print(f"--- Eval Complete. Score: {score*100:.1f}% ---")
        return {"score": score, "results": results}

if __name__ == "__main__":
    # 1. Define the Research Alignment Set
    research_baseline_inputs = [
        "Pick up the apple",
        "Place the block to the left of the bowl",
        "Move the yellow object to the bin",
        "Grip the object with 150N force",
        "Sprint forward on the slippery floor"
    ]
    
    evaluator = PromptEvaluator()
    
    # 2. Define the PROMPTS to test
    
    # A. The Baseline Prompt (Weak constraints)
    baseline_prompt = """You are a robot controller. You DO NOT chat. You ONLY output JSON.
AVAILABLE TOOLS:
1. submit_task(instruction: str)
2. execute_chunk(plan_id: str, chunk_id: str)

User: "Pick up the red cube."
Assistant: {"tool": "submit_task", "args": {"instruction": "pick up red cube"}}
"""

    # B. The Optimized Prompt (Thought-Action & Strict Protocol)
    # This matches the latest logic in local_agent.py
    optimized_prompt = """You are a robot controller. You DO NOT chat.
    
    CRITICAL PROTOCOL:
    1. First, think about the request. Is it a new command?
    2. If it is a NEW command (even if it seems simple like "move", "run", "push", "stop"), you MUST call `submit_task` FIRST to generate a plan.
    3. You can ONLY use `execute_chunk` if a plan is ALREADY ready (e.g., User says "Plan ready" or "Chunk executed").
    
    RESPONSE FORMAT:
    Thought: [Your reasoning here]
    JSON: {"tool": "...", "args": {...}}

    EXAMPLES:
    User: "Pick up the red cube."
    Assistant:
    Thought: This is a new command. I need to submit a task plan.
    JSON: {"tool": "submit_task", "args": {"instruction": "pick up red cube"}}
    """

    print("\n\n>>> TESTING BASELINE PROMPT <<<")
    evaluator.evaluate_prompt(baseline_prompt, research_baseline_inputs)
    
    print("\n\n>>> TESTING OPTIMIZED RESEARCH PROMPT <<<")
    evaluator.evaluate_prompt(optimized_prompt, research_baseline_inputs)
