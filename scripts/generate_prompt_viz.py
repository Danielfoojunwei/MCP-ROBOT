
import matplotlib.pyplot as plt
import os

def generate_prompt_viz():
    output_dir = "viz_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Comparison Bar Chart
    labels = ['Baseline Prompt', 'Optimized Prompt\n(Thought-Action)']
    scores = [40, 100]
    colors = ['#F44336', '#4CAF50']
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, scores, color=colors, width=0.6)
    
    # Add values on top of bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval}%', ha='center', va='bottom', fontweight='bold')
    
    plt.ylim(0, 110)
    plt.ylabel('Safety Adversarial Pass Rate (%)')
    plt.title('Prompt Optimization Impact: Safety-Critical Instruction Following')
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    plt.savefig(f"{output_dir}/prompt_optimization_compare.png")
    print(f"Generated {output_dir}/prompt_optimization_compare.png")
    plt.close()

if __name__ == "__main__":
    generate_prompt_viz()
