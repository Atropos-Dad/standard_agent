import json
import os
import toml
from tqdm import tqdm

# Load config
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
config = toml.load(config_path)
paths_cfg = config["paths"]

EXPECTED_FILE = paths_cfg["expected_tool_selections"]
TOOL_SEARCH_FILE = paths_cfg["keyword_tool_search_results"]
REPORT_FILE = paths_cfg["keyword_search_ranking_report"]

# Ensure output directory exists
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

# Load data
with open(EXPECTED_FILE) as f:
    expected = json.load(f)
with open(TOOL_SEARCH_FILE) as f:
    tool_search = json.load(f)

# Build lookup for tool_search_results
search_map = {}
for entry in tool_search:
    key = (entry["goal"], entry["keyword_search_query"])
    tools = entry.get("tool_search_results", [])
    if isinstance(tools, str):
        tools = []
    search_map[key] = tools

results = []
total_score = 0
max_score = 0
for e in tqdm(expected, desc="Evaluating keyword search ranking"):
    expected_id = e["expected_tool_id"]
    if expected_id == "none" or not expected_id:
        continue
    key = (e["goal"], e["keyword_search_query"])
    tools = search_map.get(key, [])
    tool_ids = [t.get("id") for t in tools]
    # Support multiple expected IDs (comma-separated)
    if isinstance(expected_id, str):
        expected_ids = [x.strip() for x in expected_id.split(",")]
    else:
        expected_ids = [str(expected_id)]
    best_rank = None
    for eid in expected_ids:
        if eid in tool_ids:
            rank = tool_ids.index(eid)
            if best_rank is None or rank < best_rank:
                best_rank = rank
    if best_rank is not None:
        # Score: 10 for first, 1 for last, linear in between
        n = len(tool_ids)
        score = 10 if n == 1 else max(1, 10 - int(9 * best_rank / max(n-1,1)))
    else:
        score = 0
    total_score += score
    max_score += 10
    results.append({
        "goal": e["goal"],
        "step": e.get("step", ""),
        "keyword_search_query": e["keyword_search_query"],
        "expected_tool_id": expected_id,
        "tool_ids": tool_ids,
        "rank": (best_rank + 1) if best_rank is not None else None,
        "score": score
    })

average_score = total_score / max_score * 10 if max_score else 0

report = {
    "average_score": average_score,
    "total_score": total_score,
    "max_score": max_score,
    "results": results
}

with open(REPORT_FILE, "w") as f:
    json.dump(report, f, indent=2)

print(f"\nKeyword Search Ranking Evaluation Report")
print(f"Average Score: {average_score:.2f} / 10.00")
print(f"Total Score: {total_score} / {max_score}")
print(f"Evaluated {len(results)} queries (skipped 'none' expected_tool_id)")
print(f"Detailed report saved to {REPORT_FILE}") 