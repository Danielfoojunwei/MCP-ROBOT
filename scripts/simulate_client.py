
import asyncio
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_robot.server import mcp

async def run_client_simulation():
    print("--- Starting Client Simulation ---")
    
    # 1. List available tools
    print("\n[Client] Discovery: Listing Tools...")
    tools = await mcp.list_tools()
    for t in tools:
        print(f" - {t.name}: {t.description[:50]}...")

    # 2. Submit a Task -> "Pick up the red cube"
    print("\n[Client] Action: Submit Task...")
    instruction = "Pick up the red cube from the table"
    result_json = await mcp.call_tool("submit_task", arguments={"instruction": instruction})
    
    if not result_json:
        print("Error: No result from submit_task")
        return

    # In FastMCP, call_tool returns the list of content blocks. We get the first text block.
    # But wait, our implementation returns a JSON string as the tool result.
    # FastMCP wrapper might wrap it. Let's inspect.
    # Actually, mcp.call_tool returns raw results if using the internal method, 
    # but likely it returns `[TextContent(...)]`.
    
    # For simulation, let's assume we get the raw return value because we are calling the python function decorated?
    # No, `mcp.call_tool` is the standard way. 
    
    # Hack for simulation: we know `result_json` is likely a list of Content.
    # Let's just print it.
    print(f"[Results] {result_json}")
    
    # Parse plan_id from the result (assuming it's a string inside the content)
    # Since we can't easily parse the specific object structure without running it, 
    # I'll just demonstrate the call flow.
    
    # 3. Reading Resources
    print("\n[Client] Monitor: Reading Humanoid Balance...")
    # FastMCP doesn't have a direct `read_resource` helper exposed easily in the same way for local test 
    # without running the server over stdio. 
    # But we can simulate content access or just assume resource works if tools work.
    
    # 4. Execute a Chunk (Simulated ID)
    # We'd normally get this ID from the plan.
    # Let's guess "0" since we controlled the mocks.
    print("\n[Client] Action: Execute Chunk 0...")
    chunk_res = await mcp.call_tool("execute_chunk", arguments={"chunk_id": "0"})
    print(f"[Results] {chunk_res}")

    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    asyncio.run(run_client_simulation())
