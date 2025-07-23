import json
import os
import re
from tqdm import tqdm
import concurrent.futures
from prompt_experimentation._prompts import LLM_BULLET_PROMPT
from prompt_experimentation._test_scenarios import SEARCH_QUERIES
import toml
from jentic_agents.utils.llm import LiteLLMChatLLM

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
config = toml.load(config_path)
gen_cfg = config["generate_keyword_search"]
paths_cfg = config["paths"]

model_name = gen_cfg["llm_model"]
MAX_WORKERS = gen_cfg["max_workers"]

llm = LiteLLMChatLLM(model=model_name, temperature=gen_cfg["llm_temperature"])

KEYWORD_QUERIES_FILE = os.path.join(
    os.path.dirname(paths_cfg["keyword_search_ranking_report"]),
    "01_keyword_search_ranking_eval_queries.json"
)
os.makedirs(os.path.dirname(KEYWORD_QUERIES_FILE), exist_ok=True)

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
    return {"provider": entry.get("provider", ""), "goal": goal, "plan": plan}

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
                    "provider": plan_entry.get("provider", ""),
                    "goal": goal,
                    "step": last_step,
                    "keyword_search_query": m.group(1)
                })
    return results

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        plans = list(tqdm(
            executor.map(generate_plan, SEARCH_QUERIES),
            total=len(SEARCH_QUERIES),
            desc="Generating LLM plans",
            unit="goal"
        ))
    # Save all plans (optional, for debugging)
    # with open(os.path.join(os.path.dirname(KEYWORD_QUERIES_FILE), "01_keyword_search_ranking_eval_plans.json"), "w") as f:
    #     json.dump(plans, f, indent=2)

    all_step_keyword_entries = []
    for plan_entry in plans:
        all_step_keyword_entries.extend(extract_steps_and_keywords(plan_entry))

    with open(KEYWORD_QUERIES_FILE, "w") as f:
        json.dump(all_step_keyword_entries, f, indent=2)

    print(f"Keyword search queries written to {KEYWORD_QUERIES_FILE}") 