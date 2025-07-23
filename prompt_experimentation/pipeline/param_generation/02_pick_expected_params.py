import json
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

def display_scenario(scenario):
    """Display scenario details in a nice format"""
    
    console.print(f"\n[bold blue]Scenario: {scenario['id']}[/bold blue]")
    console.print(f"[bold]Step:[/bold] {scenario['step']}")
    
    # Show memory data if available
    if scenario['step_inputs']:
        console.print(f"\n[bold]Available Memory:[/bold]")
        memory_json = json.dumps(scenario['step_inputs'], indent=2)
        syntax = Syntax(memory_json, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print("\n[dim]No memory data available[/dim]")
    
    # Show tool schema
    console.print(f"\n[bold]Tool Schema:[/bold]")
    schema_json = json.dumps(scenario['tool_schema'], indent=2)
    syntax = Syntax(schema_json, "json", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    console.print(f"\n[bold]Allowed Keys:[/bold] {', '.join(scenario['allowed_keys'])}")

def get_expected_params_for_scenario(scenario):
    """Interactively get expected parameters for a scenario"""
    
    display_scenario(scenario)
    
    console.print(f"\n[bold green]What should the LLM generate for this scenario?[/bold green]")
    console.print("[dim]Enter the expected JSON parameters (one key-value pair at a time)[/dim]")
    
    expected_params = {}
    allowed_keys = scenario['allowed_keys']
    
    while True:
        # Show current parameters
        if expected_params:
            console.print(f"\n[bold]Current expected parameters:[/bold]")
            current_json = json.dumps(expected_params, indent=2)
            syntax = Syntax(current_json, "json", theme="monokai")
            console.print(syntax)
        
        # Ask for next parameter
        remaining_keys = [key for key in allowed_keys if key not in expected_params]
        
        if not remaining_keys:
            break
            
        choices = remaining_keys + ["[DONE]", "[SKIP SCENARIO]"]
        
        key_choice = questionary.select(
            "Select parameter to set:",
            choices=choices
        ).ask()
        
        if key_choice == "[DONE]":
            break
        elif key_choice == "[SKIP SCENARIO]":
            return None
        
        # Get value for the key
        value = questionary.text(
            f"Enter value for '{key_choice}':",
            instruction="(Use JSON format for arrays/objects)"
        ).ask()
        
        # Try to parse as JSON, fallback to string
        try:
            if value.startswith('[') or value.startswith('{'):
                parsed_value = json.loads(value)
            else:
                # Try to parse numbers
                if value.isdigit():
                    parsed_value = int(value)
                elif value.replace('.', '').isdigit():
                    parsed_value = float(value)
                else:
                    parsed_value = value
        except:
            parsed_value = value
        
        expected_params[key_choice] = parsed_value
    
    if not expected_params:
        console.print("[yellow]No parameters set for this scenario[/yellow]")
        return None
        
    return expected_params

def pick_expected_params():
    """Main function to pick expected parameters for all scenarios"""
    
    # Load scenarios
    scenarios_file = "prompt_experimentation/data/param_generation/param_generation_scenarios.json"
    try:
        with open(scenarios_file, "r") as f:
            scenarios = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: {scenarios_file} not found. Run 01_generate_param_scenarios.py first.[/red]")
        return
    
    console.print(Panel.fit(
        "[bold blue]Parameter Generation - Expected Results Picker[/bold blue]\n"
        f"Setting expected parameters for {len(scenarios)} scenarios",
        border_style="blue"
    ))
    
    expected_results = []
    
    for i, scenario in enumerate(scenarios, 1):
        console.print(f"\n[bold cyan]Progress: {i}/{len(scenarios)}[/bold cyan]")
        
        expected_params = get_expected_params_for_scenario(scenario)
        
        if expected_params is not None:
            expected_results.append({
                "pair_id": scenario["pair_id"],
                "id": scenario["id"],
                "step": scenario["step"],
                "expected_params": expected_params
            })
            console.print("[green]✅ Expected parameters saved[/green]")
        else:
            console.print("[yellow]⏭️  Scenario skipped[/yellow]")
        
        # Ask if user wants to continue
        if i < len(scenarios):
            continue_choice = questionary.confirm("Continue to next scenario?").ask()
            if not continue_choice:
                break
    
    # Save expected results
    output_file = "prompt_experimentation/data/param_generation/expected_param_results.json"
    with open(output_file, "w") as f:
        json.dump(expected_results, f, indent=2)
    
    console.print(f"\n[bold green]✅ Saved {len(expected_results)} expected parameter sets to {output_file}[/bold green]")

if __name__ == "__main__":
    pick_expected_params()