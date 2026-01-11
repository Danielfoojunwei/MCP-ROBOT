
import matplotlib.pyplot as plt
import json
import os
import sys

# Data from the report (Hardcoding for consistent styling matching the report text)
# We could read json, but the report artifact is the source of truth for the README text.
data = [
    {"category": "Seen Skills (RT-2)", "success": 2, "total": 2},
    {"category": "Unseen Skills (OpenVLA)", "success": 2, "total": 2},
    {"category": "Safety Stress (ISO)", "success": 0, "total": 2}
]

def generate_graphs():
    output_dir = "viz_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Overall Success Rate Pie Chart
    plt.figure(figsize=(6, 6))
    total_success = sum([d["success"] for d in data])
    total_tasks = sum([d["total"] for d in data])
    total_fail = total_tasks - total_success
    
    plt.pie([total_success, total_fail], labels=[f"Success ({total_success})", f"Fail ({total_fail})"], 
            colors=['#4CAF50', '#F44336'], autopct='%1.1f%%', startangle=140)
    plt.title(f"Overall Task Success Rate (n={total_tasks})")
    plt.savefig(f"{output_dir}/benchmark_success_rate.png")
    print(f"Generated {output_dir}/benchmark_success_rate.png")
    plt.close()

    # 2. Category Performance Bar Chart
    categories = [d["category"] for d in data]
    success_counts = [d["success"] for d in data]
    fail_counts = [d["total"] - d["success"] for d in data]
    
    plt.figure(figsize=(10, 6))
    plt.bar(categories, success_counts, label='Success', color='#4CAF50')
    plt.bar(categories, fail_counts, bottom=success_counts, label='Failure', color='#F44336')
    
    plt.xlabel('Task Category')
    plt.ylabel('Number of Tasks')
    plt.title('Performance by Category')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(f"{output_dir}/benchmark_categories.png")
    print(f"Generated {output_dir}/benchmark_categories.png")
    plt.close()

if __name__ == "__main__":
    generate_graphs()
