import json
import questionary
import toml
import os

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.toml")
config = toml.load(config_path)
pick_cfg = config["pick_expected_tools"]
paths_cfg = config["paths"]

TOOL_SEARCH_RESULTS_FILE = paths_cfg["keyword_tool_search_results"]
EXPECTED_RESULTS_FILE = paths_cfg["expected_tool_selections"]

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

def main():
    with open(TOOL_SEARCH_RESULTS_FILE, "r") as f:
        search_results = json.load(f)
    expected = []
    for entry in search_results:
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

if __name__ == "__main__":
    main() 