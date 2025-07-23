import json
import os
import re
from tqdm import tqdm
import concurrent.futures
from jentic_agents.platform.jentic_client import JenticClient
from jentic_agents.utils.llm import LiteLLMChatLLM
from prompt_experimentation._prompts import LLM_BULLET_PROMPT
from prompt_experimentation._test_scenarios import SEARCH_QUERIES
import toml

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
config = toml.load(config_path)
gen_cfg = config["generate_keyword_search"]
paths_cfg = config["paths"]

API_KEY = os.getenv("JENTIC_API_KEY")
model_name = gen_cfg["llm_model"]
TOP_K = gen_cfg["top_k"]
MAX_WORKERS = gen_cfg["max_workers"]
TOOL_SEARCH_WORKERS = gen_cfg["tool_search_workers"]
PLAN_RESULTS_FILE = paths_cfg["plan_results"]
KEYWORD_TOOL_SEARCH_RESULTS_FILE = paths_cfg["keyword_tool_search_results"]

client = JenticClient(api_key=API_KEY)
llm = LiteLLMChatLLM(model=model_name, temperature=gen_cfg["llm_temperature"])

def generate_plan(entry):
    goal = entry["goal"]
    prompt = LLM_BULLET_PROMPT.format(goal=goal)
    llm_messages = [
        {"role": "system", "content": "You are a world-class planning assistant operating within the Jentic platform."},
        {"role": "user", "content": prompt}
    ]
    try:
        plan = llm.chat(llm_messages).strip()
    except Exception as e:
        plan = f"llm_error: {e}"
    return {"provider": entry["provider"], "goal": goal, "plan": plan}

def extract_steps_and_keywords(plan_entry):
    goal = plan_entry["goal"]
    plan = plan_entry["plan"]
    last_step = None
    results = []
    if plan.startswith("```"):
        plan_body = plan.strip('`\n')
    else:
        plan_body = plan
    for line in plan_body.splitlines():
        line = line.strip()
        if line.startswith("- "):
            last_step = line[2:]
        elif line.startswith("→ keyword search query:"):
            m = re.match(r'→ keyword search query: "([^"]+)"', line)
            if m and last_step:
                results.append({
                    "provider": plan_entry["provider"],
                    "goal": goal,
                    "step": last_step,
                    "keyword_search_query": m.group(1)
                })
    return results

def tool_search(entry):
    keyword_query = entry["keyword_search_query"]
    try:
        search_results = client.search(keyword_query, top_k=TOP_K)
    except Exception as e:
        search_results = f"search_error: {e}"
    enriched = dict(entry)
    enriched["tool_search_results"] = search_results
    return enriched

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        plans = list(tqdm(
            executor.map(generate_plan, SEARCH_QUERIES),
            total=len(SEARCH_QUERIES),
            desc="Generating LLM plans",
            unit="goal"
        ))
    with open(PLAN_RESULTS_FILE, "w") as f:
        json.dump(plans, f, indent=2)

    all_step_keyword_entries = []
    for plan_entry in plans:
        all_step_keyword_entries.extend(extract_steps_and_keywords(plan_entry))

    with concurrent.futures.ThreadPoolExecutor(max_workers=TOOL_SEARCH_WORKERS) as executor:
        tool_search_results = list(tqdm(
            executor.map(tool_search, all_step_keyword_entries),
            total=len(all_step_keyword_entries),
            desc="Tool search",
            unit="query"
        ))
    with open(KEYWORD_TOOL_SEARCH_RESULTS_FILE, "w") as f:
        json.dump(tool_search_results, f, indent=2)

    # Assign pair_id as a simple string index
    for idx, entry in enumerate(tool_search_results, 1):
        entry["pair_id"] = str(idx)

    print(f"Plans written to {PLAN_RESULTS_FILE}")
    print(f"Tool search results written to {KEYWORD_TOOL_SEARCH_RESULTS_FILE}") 