import json
import os
import re
from tqdm import tqdm
import concurrent.futures
import questionary
from jentic_agents.platform.jentic_client import JenticClient
from jentic_agents.utils.llm import LiteLLMChatLLM
from dylan_test._prompts import SEARCH_QUERIES, LLM_BULLET_PROMPT, TOOL_SELECTION_PROMPT

API_KEY = os.getenv("JENTIC_API_KEY")
model_name = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
TOP_K = 10
MAX_WORKERS = 60
TOOL_SEARCH_WORKERS = 8

PLAN_RESULTS_FILE = "dylan_test/data/llm_bullet_plans.json"
KEYWORD_TOOL_SEARCH_RESULTS_FILE = "dylan_test/data/keyword_tool_search_results.json"
EXPECTED_RESULTS_FILE = "dylan_test/data/expected_tool_selections.json"
SELECTION_RESULTS_FILE = "dylan_test/data/tool_selection_results.json"

client = JenticClient(api_key=API_KEY)
llm = LiteLLMChatLLM(model=model_name, temperature=0.2)

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

def prompt_user_for_selection(entry):
    print("\n" + "="*60)
    print(f"Goal: {entry['goal']}")
    print(f"Step: {entry.get('step', '')}")
    print(f"Keyword Search Query: {entry['keyword_search_query']}")
    print("\nTool Search Results:")
    tools = entry.get("tool_search_results", [])
    if not tools or isinstance(tools, str):
        print("  [No tools found or search error]")
        return "none"
    choices = [
        questionary.Choice(
            title=f"[{i+1}] {tool.get('name', '')} (id: {tool.get('id', '')})\n    Description: {tool.get('description', '')}\n    Type: {tool.get('type', '')}, API: {tool.get('api_name', '')}\n    Parameters: {tool.get('parameters', {})}",
            value=tool.get("id")
        )
        for i, tool in enumerate(tools[:10])
    ]
    choices.append(questionary.Choice(title="None of these", value="none"))
    answer = questionary.select(
        "Select the correct tool (arrow keys, then Enter):",
        choices=choices
    ).ask()
    return answer

def select_tool(entry):
    tools = entry["tool_search_results"]
    selected_tool_id = None
    selected_tool_obj = None
    if isinstance(tools, str) and tools.startswith("search_error"):
        selected_tool_id = tools
    elif not tools:
        selected_tool_id = "none"
    else:
        tools_json = json.dumps(tools, ensure_ascii=False)
        prompt = TOOL_SELECTION_PROMPT.format(step=entry["step"], tools_json=tools_json)
        llm_messages = [
            {"role": "system", "content": "You are an expert orchestrator working within the Jentic API ecosystem."},
            {"role": "user", "content": prompt}
        ]
        try:
            selected_tool_id = llm.chat(llm_messages).strip()
            for tool in tools:
                if tool.get("id") == selected_tool_id:
                    selected_tool_obj = tool
                    break
        except Exception as e:
            selected_tool_id = f"llm_error: {e}"
    result = dict(entry)
    result["selected_tool_id"] = selected_tool_id
    if selected_tool_obj:
        result.update(selected_tool_obj)
    if "tool_search_results" in result:
        del result["tool_search_results"]
    if "id" in result and result["id"] == result.get("selected_tool_id"):
        del result["id"]
    return result

if __name__ == "__main__":
    # 1. Generate plans in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        plans = list(tqdm(
            executor.map(generate_plan, SEARCH_QUERIES),
            total=len(SEARCH_QUERIES),
            desc="Generating LLM plans",
            unit="goal"
        ))
    with open(PLAN_RESULTS_FILE, "w") as f:
        json.dump(plans, f, indent=2)

    # 2. Extract steps and keyword queries
    all_step_keyword_entries = []
    for plan_entry in plans:
        all_step_keyword_entries.extend(extract_steps_and_keywords(plan_entry))

    # 3. Tool search in parallel (slower, more stable)
    with concurrent.futures.ThreadPoolExecutor(max_workers=TOOL_SEARCH_WORKERS) as executor:
        tool_search_results = list(tqdm(
            executor.map(tool_search, all_step_keyword_entries),
            total=len(all_step_keyword_entries),
            desc="Tool search",
            unit="query"
        ))
    with open(KEYWORD_TOOL_SEARCH_RESULTS_FILE, "w") as f:
        json.dump(tool_search_results, f, indent=2)

    # 4. Prompt user for expected tool selections
    expected = []
    for entry in tool_search_results:
        selected_tool_id = prompt_user_for_selection(entry)
        expected.append({
            "goal": entry["goal"],
            "step": entry.get("step", ""),
            "keyword_search_query": entry["keyword_search_query"],
            "expected_tool_id": selected_tool_id
        })
        with open(EXPECTED_RESULTS_FILE, "w") as f:
            json.dump(expected, f, indent=2)
    print(f"\nAll selections saved to {EXPECTED_RESULTS_FILE}")

    # 5. Tool selection in parallel (fast)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        selection_results = list(tqdm(
            executor.map(select_tool, tool_search_results),
            total=len(tool_search_results),
            desc="Tool selection",
            unit="step"
        ))
    with open(SELECTION_RESULTS_FILE, "w") as f:
        json.dump(selection_results, f, indent=2)

    # 6. Evaluate
    expected_map = {(e["goal"], e["keyword_search_query"]): e["expected_tool_id"] for e in expected}
    correct = 0
    total = 0
    for entry in selection_results:
        key = (entry["goal"], entry["keyword_search_query"])
        selected = entry.get("selected_tool_id")
        expected_id = expected_map.get(key)
        if expected_id is not None:
            total += 1
            if selected == expected_id:
                correct += 1
    print(f"\nLLM Tool Selection Accuracy: {correct}/{total} = {correct/total:.2%}" if total else "No ground truth to compare.")
