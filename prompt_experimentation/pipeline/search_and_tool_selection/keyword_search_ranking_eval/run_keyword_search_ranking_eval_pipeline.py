#!/usr/bin/env python3
"""
Pipeline runner for keyword search ranking evaluation:
  1. Generate keyword search queries
  2. Evaluate keyword search ranking
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    print(f"\n{'='*60}")
    print(f"Running {description}...")
    print(f"Command: {cmd}")
    print('='*60)
    result = subprocess.run(cmd, shell=True, cwd=os.getcwd())
    if result.returncode != 0:
        print(f"ERROR: {description} failed with return code {result.returncode}")
        sys.exit(1)
    print(f"✅ {description} completed successfully")

if __name__ == "__main__":
    run_command(
        "python -m prompt_experimentation.pipeline.search_and_tool_selection.keyword_search_ranking_eval.01_generate_keyword_search_ranking_eval",
        "Step 1 - Generate keyword search queries"
    )
    run_command(
        "python -m prompt_experimentation.pipeline.search_and_tool_selection.keyword_search_ranking_eval.02_eval_keyword_search_ranking",
        "Step 2 - Evaluate keyword search ranking"
    )
    print(f"\n{'='*60}")
    print("🎉 Keyword search ranking evaluation pipeline completed!")
    print('='*60) 