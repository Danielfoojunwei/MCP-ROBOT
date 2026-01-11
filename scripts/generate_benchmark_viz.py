
import matplotlib.pyplot as plt
import json
import os
import sys

# Load Data from benchmark_results.json (Transparency Check)
def load_data():
    results_path = "benchmark_results.json"
    if not os.path.exists(results_path):
        print(f"Warning: {results_path} not found. Using empty data.")
        return []
        
    with open(results_path, "r") as f:
        raw_results = json.load(f)
        
    # Aggregate by category
    categories = {}
    for res in raw_results:
        cat = res["category"]
        if cat not in categories:
            categories[cat] = {"success": 0, "total": 0}
        categories[cat]["total"] += 1
        if res.get("success", False):
            categories[cat]["success"] += 1
            
    # Convert to format expected by plotting logic
    data = []
    for cat, stats in categories.items():
        data.append({
            "category": cat,
            "success": stats["success"],
            "total": stats["total"]
        })
    return data

data = load_data()

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
