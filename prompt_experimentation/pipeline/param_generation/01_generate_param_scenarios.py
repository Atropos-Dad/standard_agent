import json
import os
from tqdm import tqdm
from prompt_experimentation._test_scenarios import PARAMETER_TEST_SCENARIOS

def generate_param_scenarios():
    """Generate parameter generation test scenarios"""
    
    print(f"Generating {len(PARAMETER_TEST_SCENARIOS)} parameter generation test scenarios...")
    
    # Add pair_id to each scenario
    for idx, scenario in enumerate(PARAMETER_TEST_SCENARIOS, 1):
        scenario["pair_id"] = str(idx)
    
    # Save to file
    output_file = "prompt_experimentation/data/param_generation/param_generation_scenarios.json"
    with open(output_file, "w") as f:
        json.dump(PARAMETER_TEST_SCENARIOS, f, indent=2)
    
    print(f"✅ Generated {len(PARAMETER_TEST_SCENARIOS)} scenarios")
    print(f"📁 Saved to {output_file}")
    
    # Print scenario summary
    print("\n📊 Scenario Summary:")
    for scenario in PARAMETER_TEST_SCENARIOS:
        memory_keys = list(scenario['step_inputs'].keys()) if scenario['step_inputs'] else []
        memory_info = f" (memory: {', '.join(memory_keys)})" if memory_keys else " (no memory)"
        print(f"  • {scenario['id']}: {scenario['step'][:50]}...{memory_info}")

if __name__ == "__main__":
    generate_param_scenarios()