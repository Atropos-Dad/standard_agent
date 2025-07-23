#!/usr/bin/env python3
"""
Simple script to run the pipeline in sequence: 1 -> 3 -> 4
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
    # Pipeline 3: LLM tool selection and evaluation  
    run_command(
<<<<<<< HEAD:prompt_experimentation/run_pipeline.py
        "python -m prompt_experimentation.pipeline.tool_selection.03_llm_tool_selection_and_eval",
=======
        "python -m prompt_experimentation.pipeline.search_and_tool_selection.03_llm_tool_selection_and_eval",
>>>>>>> 1fcd93952ee58559f0715bd6c1d237dbcc74eddc:prompt_experimentation/pipeline/search_and_tool_selection/run_selection_pipeline.py
        "Pipeline 3 - LLM tool selection and evaluation"
    )
    
    # Pipeline 4: Comparison
    run_command(
<<<<<<< HEAD:prompt_experimentation/run_pipeline.py
        "python -m prompt_experimentation.pipeline.tool_selection.04_comparison",
=======
        "python -m prompt_experimentation.pipeline.search_and_tool_selection.04_comparison",
>>>>>>> 1fcd93952ee58559f0715bd6c1d237dbcc74eddc:prompt_experimentation/pipeline/search_and_tool_selection/run_selection_pipeline.py
        "Pipeline 4 - Comparison"
    )
    
    print(f"\n{'='*60}")
    print("🎉 All pipelines completed successfully!")
    print('='*60)