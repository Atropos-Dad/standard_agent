import json
import os
from tqdm import tqdm
import concurrent.futures
from jentic_agents.utils.llm import LiteLLMChatLLM
from prompt_experimentation._prompts import TOOL_SELECTION_PROMPT
import toml

config = toml.load(os.path.join(os.path.dirname(__file__), "config.toml"))
llm_cfg = config["llm_tool_selection_and_eval"]
paths_cfg = config["paths"]

model_name = llm_cfg["llm_model"]
LLM_WORKERS = llm_cfg["llm_workers"]
KEYWORD_TOOL_SEARCH_RESULTS_FILE = paths_cfg["keyword_tool_search_results"]
EXPECTED_RESULTS_FILE = paths_cfg["expected_tool_selections"]
SELECTION_RESULTS_FILE = paths_cfg["tool_selection_results"]

llm = LiteLLMChatLLM(model=model_name, temperature=llm_cfg["llm_temperature"])

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
    with open(KEYWORD_TOOL_SEARCH_RESULTS_FILE, "r") as f:
        tool_search_results = json.load(f)
    with open(EXPECTED_RESULTS_FILE, "r") as f:
        expected = json.load(f)

    # Assign pair_id as a simple string index
    for idx, entry in enumerate(tool_search_results, 1):
        entry["pair_id"] = str(idx)

    with concurrent.futures.ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        selection_results = list(tqdm(
            executor.map(select_tool, tool_search_results),
            total=len(tool_search_results),
            desc="Tool selection",
            unit="step"
        ))

    # Copy pair_id to tool selection results
    pair_id_map = {}
    for entry in tool_search_results:
        key = (entry["goal"], entry["step"], entry["keyword_search_query"])
        pair_id_map[key] = entry.get("pair_id")

    for result in selection_results:
        key = (result["goal"], result["step"], result["keyword_search_query"])
        result["pair_id"] = pair_id_map.get(key)

    with open(SELECTION_RESULTS_FILE, "w") as f:
        json.dump(selection_results, f, indent=2)

    expected_map = {(e["goal"], e["keyword_search_query"]): e["expected_tool_id"] for e in expected}
    correct = 0
    total = 0
    for entry in selection_results:
        key = (entry["goal"], entry["keyword_search_query"])
        selected = entry.get("selected_tool_id")
        expected_ids = expected_map.get(key)
        # Support both comma-separated string and list
        if isinstance(expected_ids, str):
            expected_ids = [x.strip() for x in expected_ids.split(",")]
        elif not isinstance(expected_ids, list):
            expected_ids = [str(expected_ids)]
        if expected_ids:
            total += 1
            if selected in expected_ids:
                correct += 1
    print(f"\nLLM Tool Selection Accuracy: {correct}/{total} = {correct/total:.2%}" if total else "No ground truth to compare.") 