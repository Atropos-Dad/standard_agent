import json
import os
from jentic_agents.utils.llm import LiteLLMChatLLM
from tqdm import tqdm
import concurrent.futures
import threading

TOOL_SELECTION_PROMPT = (
    """
    <role>
    You are an expert orchestrator working within the Jentic API ecosystem.
    Your job is to select the best tool to execute a specific plan step, using a list of available tools. Each tool may vary in API domain, supported actions, and required parameters. You must evaluate each tool's suitability and return the **single best matching tool** — or the wordnone if none qualify.

    Your selection will be executed by an agent, so precision and compatibility are critical.
    </role>

    <instructions>
    Analyze the provided step and evaluate all candidate tools. Use the scoring criteria to assess each tool’s fitness for executing the step. Return the tool `id` with the highest total score. If no tool scores ≥60, return the word none.
    You are selecting the **most execution-ready** tool, not simply the closest match.
    </instructions>

    <input>
    Step:
    {step}

    Tools (JSON):
    {tools_json}
    </input>

    <scoring_criteria>
    - **API Domain Match** (30 pts): Relevance of the tool’s API domain to the step's intent.
    - **Action Compatibility** (25 pts): How well the tool’s action matches the step’s intent, considering common verb synonyms (e.g., "send" maps well to "post", "create" to "add").
    - **Parameter Compatibility** (20 pts): Whether required parameters are available or can be inferred from the current context.
    - **Workflow Fit** (15 pts): Alignment with the current workflow’s sequence and memory state.
    - **Simplicity & Efficiency** (10 pts): Prefer tools that perform the intended action directly and efficiently; if both an operation and a workflow accomplish the same goal, favor the simpler operation unless the workflow provides a clear added benefit.
    </scoring_criteria>

    <rules>
    1. Score each tool using the weighted criteria above. Max score: 100 points.
    2. Select the tool with the highest total score.
    3. If no tool scores at least 60 points, return none.
    4. Do **not** include any explanation, formatting, or metadata — only the tool `id` or none.
    5. Use available step context and known inputs to inform scoring.
    6. Penalize tools misaligned with the intended action.
    </rules>

    <output_format>
    Respond with a **single line** which only includes the selected tool’s `id`
    **No additional text** should be included.
    </output_format>
    """
)

MODEL_NAME = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
KEYWORD_TOOL_SEARCH_RESULTS_FILE = "keyword_tool_search_results.json"
SELECTION_RESULTS_FILE = "tool_selection_results.json"

def select_tool(entry, llm):
    goal = entry["goal"]
    keyword_query = entry["keyword_search_query"]
    tools = entry["tool_search_results"]
    selected_tool_id = None
    remaining_requests = None
    selected_tool_obj = None
    if isinstance(tools, str) and tools.startswith("search_error"):
        selected_tool_id = tools
    elif not tools:
        selected_tool_id = "none"
    else:
        tools_json = json.dumps(tools, ensure_ascii=False)
        prompt = TOOL_SELECTION_PROMPT.format(step=keyword_query, tools_json=tools_json)
        llm_messages = [
            {"role": "system", "content": "You are an expert orchestrator working within the Jentic API ecosystem."},
            {"role": "user", "content": prompt}
        ]
        try:
            selected_tool_id = llm.chat(llm_messages).strip()
            model_header = f"x-litellm-key-remaining-requests-{llm.model}"
            remaining_requests = llm.last_headers.get(model_header)
            if remaining_requests is not None:
                print(f"[{llm.model}] Remaining requests: {remaining_requests}")
            # Find the full tool object by id
            for tool in tools:
                if tool.get("id") == selected_tool_id:
                    selected_tool_obj = tool
                    break
        except Exception as e:
            selected_tool_id = f"llm_error: {e}"
    result = {
        "goal": goal,
        "keyword_search_query": keyword_query,
        "selected_tool_id": selected_tool_id,
        "remaining_requests": remaining_requests
    }
    if selected_tool_obj:
        result.update(selected_tool_obj)
    return result

if __name__ == "__main__":
    with open(KEYWORD_TOOL_SEARCH_RESULTS_FILE, "r") as f:
        search_data = json.load(f)
    llm = LiteLLMChatLLM(model=MODEL_NAME, temperature=0.2)
    selection_results = []

    # First, do a single call to get the current remaining requests
    first_entry = search_data[0]
    first_result = select_tool(first_entry, llm)
    selection_results.append(first_result)
    try:
        remaining = int(first_result["remaining_requests"])
    except (TypeError, ValueError):
        remaining = 1
    max_workers = min(5, max(1, remaining))
    print(f"[INFO] Using max_workers={max_workers} based on remaining requests: {remaining}")

    # Now process the rest in parallel
    rest_entries = search_data[1:]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(select_tool, entry, llm)
            for entry in rest_entries
        ]
        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Selecting tools", unit="step"):
            selection_results.append(f.result())

    # Overwrite tool_selection_results.json with the new format
    with open(SELECTION_RESULTS_FILE, "w") as f:
        json.dump(selection_results, f, indent=2)
    print(f"Saved tool selection results to {SELECTION_RESULTS_FILE}")