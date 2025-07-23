import json
import toml
import os

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
config = toml.load(config_path)
paths_cfg = config["paths"]

EXPECTED_FILE = paths_cfg["expected_tool_selections"]
ACTUAL_FILE = paths_cfg["tool_selection_results"]
TOOL_SEARCH_FILE = paths_cfg["keyword_tool_search_results"]
REPORT_FILE = paths_cfg["tool_selection_comparison_report"]

# Load files
with open(EXPECTED_FILE) as f:
    expected = json.load(f)
with open(ACTUAL_FILE) as f:
    actual = json.load(f)
with open(TOOL_SEARCH_FILE) as f:
    tool_search = json.load(f)

# Build lookup for tool_search_results
tool_search_map = {}
for entry in tool_search:
    key = (entry["goal"], entry["keyword_search_query"])
    tools = entry.get("tool_search_results", [])
    if isinstance(tools, str):
        tools = []
    tool_search_map[key] = {tool.get("id"): tool for tool in tools}

# Build lookup for actual results
actual_map = {(a["goal"], a["keyword_search_query"]): a for a in actual}

report = []
success_count = 0
for e in expected:
    key = (e["goal"], e["keyword_search_query"])
    expected_ids = e["expected_tool_id"]
    # Support both comma-separated string and list
    if isinstance(expected_ids, str):
        expected_ids = [x.strip() for x in expected_ids.split(",")]
    elif not isinstance(expected_ids, list):
        expected_ids = [str(expected_ids)]
    actual_entry = actual_map.get(key, {})
    actual_id = actual_entry.get("selected_tool_id")
    # Get full tool objects
    expected_tool = None
    for eid in expected_ids:
        t = tool_search_map.get(key, {}).get(eid)
        if t:
            expected_tool = t
            break
    actual_tool = tool_search_map.get(key, {}).get(actual_id)
    success = actual_id in expected_ids
    if success:
        success_count += 1
    report_entry = {
        "goal": e["goal"],
        "step": e.get("step", ""),
        "keyword_search_query": e["keyword_search_query"],
        "expected": expected_tool if expected_tool else {"ids": expected_ids, "not_found": True},
        "actual": actual_tool if actual_tool else {"id": actual_id, "not_found": True},
        "success": success
    }
    report.append(report_entry)

summary = {
    "total_success": success_count,
    "total": len(report),
    "accuracy": round(success_count / len(report), 4) if report else None
}

with open(REPORT_FILE, "w") as f:
    json.dump({"summary": summary, "results": report}, f, indent=2)

print(f"\nComparison report saved to {REPORT_FILE}")
print(f"Total successes: {success_count}/{len(report)} ({success_count/len(report):.2%})")
