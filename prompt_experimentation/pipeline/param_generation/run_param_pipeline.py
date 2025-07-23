#!/usr/bin/env python3
"""
Parameter Generation Testing Pipeline Runner

Usage:
  python run_param_pipeline.py                    # Run the full pipeline
  python run_param_pipeline.py --generate-only    # Only generate scenarios
  python run_param_pipeline.py --test-only        # Skip manual step, only test
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running {description}...")
    print(f"Command: {cmd}")
    print('='*60)
    
    result = subprocess.run(cmd, shell=True, cwd=os.getcwd())
    if result.returncode != 0:
        print(f"ERROR: {description} failed with return code {result.returncode}")
        return False
    print(f"✅ {description} completed successfully")
    return True

def check_file_exists(filepath, description):
    """Check if a file exists and warn if not"""
    if not Path(filepath).exists():
        print(f"⚠️  Warning: {description} not found at {filepath}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Parameter Generation Testing Pipeline")
    parser.add_argument("--generate-only", action="store_true", 
                       help="Only generate scenarios, don't run tests")
    parser.add_argument("--test-only", action="store_true",
                       help="Skip manual expected parameter selection")
    parser.add_argument("--skip-comparison", action="store_true",
                       help="Skip final comparison report")
    
    args = parser.parse_args()
    
    print("🧪 Parameter Generation Testing Pipeline")
    print("========================================")
    
    # # Step 1: Generate scenarios
    # success = run_command(
    #     "python -m prompt_experimentation.pipeline.param_generation.01_generate_param_scenarios",
    #     "Step 1 - Generate parameter scenarios"
    # )
    # if not success:
    #     sys.exit(1)
    
    # if args.generate_only:
    #     print("\n🎉 Scenario generation completed!")
    #     return
    
    # # Step 2: Pick expected parameters (manual step)
    # if not args.test_only:
    #     print(f"\n{'='*60}")
    #     print("Step 2 - Pick Expected Parameters (Interactive)")
    #     print("='*60")
    #     print("This step requires manual input to set expected parameter values.")
    #     print("You'll be shown each scenario and asked to specify the expected JSON output.")
        
    #     continue_choice = input("\nDo you want to continue with the interactive step? (y/n): ")
    #     if continue_choice.lower() != 'y':
    #         print("⏭️  Skipping interactive step. You can run it later with:")
    #         print("   python -m prompt_experimentation.pipeline.param_generation.02_pick_expected_params")
    #         print("\nContinuing with existing expected results (if any)...")
    #     else:
    #         success = run_command(
    #             "python -m prompt_experimentation.pipeline.param_generation.02_pick_expected_params",
    #             "Step 2 - Pick expected parameters (interactive)"
    #         )
    #         if not success:
    #             print("⚠️  Interactive step failed, but continuing with existing data...")
    
    # Check if expected results exist
    expected_file = "prompt_experimentation/data/param_generation/expected_param_results.json"
    has_expected = check_file_exists(expected_file, "Expected parameter results")
    
    if not has_expected:
        print("\n⚠️  No expected results found. Evaluation will be limited.")
        print("   Run the following to set expected results:")
        print("   python -m prompt_experimentation.pipeline.param_generation.02_pick_expected_params")
    
    # Step 3: LLM parameter generation and evaluation
    success = run_command(
        "python -m prompt_experimentation.pipeline.param_generation.03_llm_param_generation_and_eval",
        "Step 3 - LLM parameter generation and evaluation"
    )
    if not success:
        sys.exit(1)
    
    # Step 4: Comparison and reporting
    if not args.skip_comparison:
        success = run_command(
            "python -m prompt_experimentation.pipeline.param_generation.04_param_comparison",
            "Step 4 - Comparison and reporting"
        )
        if not success:
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print("🎉 Parameter Generation Pipeline Completed!")
    print('='*60)
    
    # Show output files
    print("\n📁 Generated Files:")
    output_files = [
        ("Scenarios", "prompt_experimentation/data/param_generation/param_generation_scenarios.json"),
        ("Expected Results", "prompt_experimentation/data/param_generation/expected_param_results.json"),
        ("Test Results", "prompt_experimentation/data/param_generation/param_generation_results.json"),
        ("Comparison Report", "prompt_experimentation/data/param_generation/param_generation_comparison_report.json")
    ]
    
    for name, filepath in output_files:
        if Path(filepath).exists():
            print(f"  ✅ {name}: {filepath}")
        else:
            print(f"  ❌ {name}: {filepath} (not created)")
    
    print(f"\n🔍 Next Steps:")
    print("  • Review the comparison report for insights")
    print("  • Modify the PARAMETER_GENERATION_PROMPT and re-run to test improvements")
    print("  • Add more test scenarios in 01_generate_param_scenarios.py")

if __name__ == "__main__":
    main()