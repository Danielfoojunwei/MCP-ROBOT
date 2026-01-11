
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import random

# Create viz directory
os.makedirs("viz_output", exist_ok=True)

def load_logs():
    try:
        if not os.path.exists("pipeline_logs.json"):
            return []
        with open("pipeline_logs.json", "r") as f:
            data = json.load(f)
            return data if data else []
    except Exception as e:
        print(f"Error loading logs: {e}")
        return []

def plot_execution_timeline(logs):
    """Plot execution duration of chunks."""
    chunk_ids = [log["chunk_id"] for log in logs]
    durations = [log["duration_actual"] for log in logs]
    
    plt.figure(figsize=(10, 5))
    plt.bar(chunk_ids, durations, color='skyblue')
    plt.xlabel('Chunk ID')
    plt.ylabel('Duration (s)')
    plt.title('Execution Time per Chunk (Tier 6 Performance)')
    plt.savefig("viz_output/timeline.png")
    plt.close()

def plot_tactile_stability(logs):
    """Plot mock tactile/stability events."""
    timestamps = []
    stability_scores = []
    
    for i, log in enumerate(logs):
        timestamps.append(i)
        slips = len([e for e in log.get("tactile_events", []) if e.get("event") == "slip_detected"])
        score = max(0, 1.0 - (slips * 0.4)) # Exaggerate for viz
        stability_scores.append(score)
        
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, stability_scores, marker='o', linestyle='-', color='green')
    plt.ylim(0, 1.1)
    plt.xlabel('Execution Step')
    plt.ylabel('Stability Confidence (1.0 = Stable)')
    plt.title('Tier 5b: Stability Verification Score')
    plt.grid(True)
    plt.savefig("viz_output/stability.png")
    plt.close()

def generate_html_report(logs):
    html = """
    <html>
    <head>
        <title>MRCP-H Pipeline Dashboard</title>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            h1 { color: #333; }
            .card { background: #f4f4f4; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .img-container { text-align: center; }
            img { max-width: 100%; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <h1>MRCP-H Pipeline Execution Dashboard</h1>
        
        <div class="card">
            <h2>Architecture Flow</h2>
             <img src="https://mermaid.ink/img/pako:eNqVkE1rwzAMhv9K0GkL20t7GwyG3cYO2mF0h54sR4utYyPLKYX89ylNUMje7McnPT8SrbQ1E9KiuPsq-6M-F58m-y_q1r5_hF-vG0hW640qYHFdK9i_Q7tC_wd9gRbcwR7aYAtPsIfHcJceh_s00d5C_wI9dGEPz3AAJ7d6Y7-uF_ALtOAD7KELD_AET_AY7nFwj5P7fC_0t9C_QA9d2MMzHMDJrd7Yr-sV_Pq5gJPlsqw1W-m0M2q1Ma0x1sBKB6O9cWas1dIqY4zWyij9Xwbj_wFr7J02" />
        </div>

        <div class="card">
            <h2>Real-Time Performance</h2>
            <div class="img-container">
                <img src="timeline.png" alt="Timeline Graph">
            </div>
            <p><b>Total Chunks Executed:</b> {count}</p>
        </div>

        <div class="card">
            <h2>Stability & Tactile Analysis</h2>
            <div class="img-container">
                <img src="stability.png" alt="Stability Graph">
            </div>
            <p>Monitors ZMP deviations and Slip Events across the run.</p>
        </div>
    </body>
    </html>
    """
    
    count = len(logs)
    html = html.replace("{count}", str(count))
    
    with open("viz_output/dashboard.html", "w") as f:
        f.write(html)
    print(f"Dashboard generated at {os.path.abspath('viz_output/dashboard.html')}")

if __name__ == "__main__":
    print("Generating visualizations...")
    logs = load_logs()
    if logs:
        plot_execution_timeline(logs)
        plot_tactile_stability(logs)
        generate_html_report(logs)
