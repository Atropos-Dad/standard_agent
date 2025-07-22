import json

# File paths
SELECTION_RESULTS_FILE = "tool_selection_results.json"
KEYWORD_TOOL_SEARCH_RESULTS_FILE = "keyword_tool_search_results.json"
OUTPUT_FILE = "tool_selection_results_enriched.json"

# Load data
with open(SELECTION_RESULTS_FILE, "r") as f:
    selection_results = json.load(f)
with open(KEYWORD_TOOL_SEARCH_RESULTS_FILE, "r") as f:
    tool_search_data = json.load(f)

# Build a mapping: (goal, keyword_search_query) -> tool_search_results
search_map = {
    (entry["goal"], entry["keyword_search_query"]): entry["tool_search_results"]
    for entry in tool_search_data
}

enriched_results = []
for result in selection_results:
    goal = result["goal"]
    keyword_query = result["keyword_search_query"]
    selected_tool_id = result.get("selected_tool_id")
    # Find the tool list for this goal/query
    tools = search_map.get((goal, keyword_query), [])
    # Find the full tool object
    tool_obj = None
    if isinstance(tools, list) and selected_tool_id and not str(selected_tool_id).startswith("llm_error"):
        for tool in tools:
            if tool.get("id") == selected_tool_id:
                tool_obj = tool
                break
    enriched = dict(result)
    if tool_obj:
        enriched.update(tool_obj)
    enriched_results.append(enriched)

with open(OUTPUT_FILE, "w") as f:
    json.dump(enriched_results, f, indent=2)

print(f"Enriched results written to {OUTPUT_FILE}")