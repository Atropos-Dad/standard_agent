import json
import os
import toml
from tqdm import tqdm
import concurrent.futures
from prompt_experimentation._prompts import KEYWORD_SEARCH_PROMPT
from jentic_agents.utils.llm import LiteLLMChatLLM
from jentic_agents.platform.jentic_client import JenticClient

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
config = toml.load(config_path)
paths_cfg = config["paths"]
llm_cfg = config["llm_many_workers"]

GOAL_STEP_FILE = paths_cfg["keyword_search_ranking_queries"]
EXPECTED_FILE = paths_cfg["expected_tool_selections"]
SEARCH_RESULTS_FILE = paths_cfg["keyword_tool_search_results"]
REPORT_FILE = paths_cfg["keyword_search_ranking_report"]
LLM_WORKERS = llm_cfg["llm_workers"]

llm = LiteLLMChatLLM(model=llm_cfg["llm_model"], temperature=llm_cfg["llm_temperature"])

gen_cfg = config["generate_keyword_search"] if "generate_keyword_search" in config else {}
API_KEY = os.getenv("JENTIC_API_KEY")
TOP_K = gen_cfg.get("top_k", 10)

client = JenticClient(api_key=API_KEY)

def select_query(entry):
    goal = entry["goal"]
    step = entry["step"]
    prompt = f"""
{KEYWORD_SEARCH_PROMPT}
<goal>
Goal: {goal}
</goal>
<step>
- {step}
</step>
"""
    print("\n--- PROMPT PASSED TO LLM ---\n", prompt, "\n--- END PROMPT ---\n")
    try:
        llm_output = llm.chat([{"role": "user", "content": prompt}]).strip()
        import re
        m = re.search(r'→ keyword search query: "([^"]+)"', llm_output)
        generated_query = m.group(1) if m else llm_output
    except Exception as e:
        generated_query = f"llm_error: {e}"
    
    return {
        "pair_id": entry["pair_id"],
        "goal": goal,
        "step": step,
        "generated_query": generated_query
    }

def perform_search_with_query(query_entry):
    """
    Perform the actual keyword search using the generated query.
    """
    pair_id = query_entry["pair_id"]
    query = query_entry["generated_query"]
    # Skip if there was an LLM error
    if query.startswith("llm_error:"):
        return {
            "pair_id": pair_id,
            "query": query,
            "tool_search_results": []
        }
    try:
        search_results = client.search(query, top_k=TOP_K)
        return {
            "pair_id": pair_id,
            "query": query,
            "tool_search_results": search_results
        }
    except Exception as e:
        print(f"Search error for pair_id {pair_id}: {e}")
        return {
            "pair_id": pair_id,
            "query": query,
            "tool_search_results": []
        }

# Load data
with open(GOAL_STEP_FILE) as f:
    goal_step_data = json.load(f)

with open(EXPECTED_FILE) as f:
    expected_data = {e["pair_id"]: e for e in json.load(f)}

# Step 1: Generate queries using LLM
print("Step 1: Generating queries with LLM...")
with concurrent.futures.ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
    generated_queries = list(tqdm(
        executor.map(select_query, goal_step_data),
        total=len(goal_step_data),
        desc="LLM keyword search query generation",
        unit="query"
    ))

TOOL_SEARCH_WORKERS = gen_cfg.get("tool_search_workers", 8)

# Step 2: Perform tool search for each generated query
print("Step 2: Performing tool search for each generated query...")
with concurrent.futures.ThreadPoolExecutor(max_workers=TOOL_SEARCH_WORKERS) as executor:
    tool_search_results = list(tqdm(
        executor.map(perform_search_with_query, generated_queries),
        total=len(generated_queries),
        desc="Tool search",
        unit="query"
    ))

# Convert search results to lookup dictionary
search_results_data = {str(entry["pair_id"]): entry for entry in tool_search_results}

# Step 3: Evaluate the results
print("Step 3: Evaluating search results...")
results = []
total_score = 0
max_score = 0
skipped_none = 0

for entry in tqdm(generated_queries, desc="LLM keyword search ranking eval"):
    pair_id = str(entry["pair_id"])
    goal = entry["goal"]
    step = entry["step"]
    generated_query = entry["generated_query"]
    
    expected_entry = expected_data.get(pair_id)
    expected_tool_id = expected_entry["expected_tool_id"] if expected_entry else None
    
    if expected_tool_id is None or expected_tool_id == "none" or expected_tool_id == "":
        skipped_none += 1
        continue
    
    # Use the search results from our generated queries
    search_entry = search_results_data.get(pair_id)
    tool_search_results = search_entry["tool_search_results"] if search_entry else []
    tool_ids = [t.get("id") for t in tool_search_results]
    
    if isinstance(expected_tool_id, str):
        expected_ids = [x.strip() for x in expected_tool_id.split(",")]
    else:
        expected_ids = [str(expected_tool_id)]
    
    best_rank = None
    for eid in expected_ids:
        if eid in tool_ids:
            rank = tool_ids.index(eid)
            if best_rank is None or rank < best_rank:
                best_rank = rank
    
    if best_rank is not None:
        n = len(tool_ids)
        score = 10 if n == 1 else max(1, 10 - int(9 * best_rank / max(n-1,1)))
        rank_out = best_rank + 1
    else:
        score = 0
        rank_out = 0
    
    total_score += score
    max_score += 10
    
    results.append({
        "pair_id": pair_id,
        "goal": goal,
        "step": step,
        "generated_query": generated_query,
        "expected_tool_id": expected_tool_id,
        "tool_ids": tool_ids,
        "rank": rank_out,
        "score": score
    })

# Calculate final metrics
average_score = total_score / max_score * 10 if max_score else 0

report = {
    "average_score": average_score,
    "total_score": total_score,
    "max_score": max_score,
    "results": results,
    "search_results": tool_search_results  # Include the actual search results used
}

# Save the report
with open(REPORT_FILE, "w") as f:
    json.dump(report, f, indent=2)

YELLOW = '\033[1;33m'
CYAN = '\033[1;36m'
GREEN = '\033[1;32m'
RESET = '\033[0m'

print(f"\nLLM Keyword Search Ranking Evaluation Report")
print(f"{YELLOW}Average Score: {average_score:.2f} / 10.00{RESET} (10 = correct tool averaged first in search list, 1 = correct tool averaged last in search list)")
print(f"{CYAN}Total Score: {total_score} / {max_score}{RESET} (sum of all query scores; max score = number of queries × 10)")
print(f"{GREEN}Evaluated {len(results)} queries{RESET} (skipped {skipped_none} with expected_tool_id 'none' or empty)")
print(f"Detailed report saved to {REPORT_FILE}")