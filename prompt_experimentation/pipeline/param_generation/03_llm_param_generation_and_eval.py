import json
import os
from tqdm import tqdm
import concurrent.futures
from jentic_agents.utils.llm import LiteLLMChatLLM
from prompt_experimentation._prompts import PARAMETER_GENERATION_PROMPT

model_name = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
LLM_WORKERS = 60

SCENARIOS_FILE = "prompt_experimentation/data/param_generation/param_generation_scenarios.json"
EXPECTED_RESULTS_FILE = "prompt_experimentation/data/param_generation/expected_param_results.json"
OUTPUT_FILE = "prompt_experimentation/data/param_generation/param_generation_results.json"

llm = LiteLLMChatLLM(model=model_name, temperature=0.2)

def is_valid_json(text):
    """Check if text is valid JSON"""
    try:
        json.loads(text)
        return True
    except:
        return False

def extract_json_from_response(response):
    """Extract JSON from LLM response, handling various formats"""
    response = response.strip()
    
    # If it's already valid JSON, return it
    if is_valid_json(response):
        return response
    
    # Try to find JSON in code blocks
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end != -1:
            json_part = response[start:end].strip()
            if is_valid_json(json_part):
                return json_part
    
    # Try to find JSON between { and }
    start = response.find('{')
    if start != -1:
        # Find the matching closing brace
        brace_count = 0
        end = start
        for i, char in enumerate(response[start:], start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        json_part = response[start:end]
        if is_valid_json(json_part):
            return json_part
    
    # Return original if no valid JSON found
    return response

def evaluate_param_generation(scenario, generated_params, expected_params):
    """Evaluate the quality of generated parameters"""
    
    scores = {
        "json_valid": 0,
        "keys_correct": 0,
        "values_appropriate": 0,
        "total_score": 0
    }
    
    details = {
        "json_parse_error": None,
        "missing_keys": [],
        "extra_keys": [],
        "value_mismatches": []
    }
    
    # Check if generated params is valid JSON
    try:
        if isinstance(generated_params, str):
            parsed_params = json.loads(generated_params)
        else:
            parsed_params = generated_params
        scores["json_valid"] = 1
    except Exception as e:
        details["json_parse_error"] = str(e)
        scores["total_score"] = 0
        return scores, details
    
    # Check keys
    expected_keys = set(expected_params.keys())
    generated_keys = set(parsed_params.keys())
    
    missing_keys = expected_keys - generated_keys
    extra_keys = generated_keys - expected_keys
    correct_keys = expected_keys & generated_keys
    
    details["missing_keys"] = list(missing_keys)
    details["extra_keys"] = list(extra_keys)
    
    # Score key correctness (penalize missing required keys more than extra keys)
    key_score = len(correct_keys) / len(expected_keys) if expected_keys else 1
    key_score -= 0.5 * len(missing_keys) / len(expected_keys) if expected_keys else 0
    key_score -= 0.1 * len(extra_keys) / max(len(expected_keys), 1)
    scores["keys_correct"] = max(0, key_score)
    
    # Check value appropriateness for matching keys
    value_score = 0
    for key in correct_keys:
        expected_val = expected_params[key]
        generated_val = parsed_params[key]
        
        # Simple value comparison (can be enhanced)
        if expected_val == generated_val:
            value_score += 1
        elif isinstance(expected_val, str) and isinstance(generated_val, str):
            # For strings, check if key content is similar
            if len(expected_val) > 0 and len(generated_val) > 0:
                value_score += 0.5  # Partial credit for having some content
        elif type(expected_val) == type(generated_val):
            value_score += 0.3  # Partial credit for correct type
        else:
            details["value_mismatches"].append({
                "key": key,
                "expected": expected_val,
                "generated": generated_val
            })
    
    scores["values_appropriate"] = value_score / len(correct_keys) if correct_keys else 0
    
    # Calculate total score (weighted)
    scores["total_score"] = (
        0.3 * scores["json_valid"] +
        0.4 * scores["keys_correct"] + 
        0.3 * scores["values_appropriate"]
    )
    
    return scores, details

def generate_parameters(scenario):
    """Generate parameters for a single scenario using LLM"""
    
    # Format the prompt
    prompt = PARAMETER_GENERATION_PROMPT.format(
        step=scenario["step"],
        step_inputs=json.dumps(scenario["step_inputs"], indent=2),
        tool_schema=json.dumps(scenario["tool_schema"], indent=2),
        allowed_keys=json.dumps(scenario["allowed_keys"])
    )
    
    llm_messages = [
        {"role": "system", "content": "You are a Parameter Builder within the Jentic agent ecosystem."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = llm.chat(llm_messages).strip()
        
        # Extract JSON from response
        clean_response = extract_json_from_response(response)
        
        return {
            "pair_id": scenario["pair_id"],
            "id": scenario["id"],
            "step": scenario["step"],
            "generated_params": clean_response,
            "raw_response": response,
            "step_inputs": scenario["step_inputs"],
            "allowed_keys": scenario["allowed_keys"]
        }
        
    except Exception as e:
        return {
            "pair_id": scenario["pair_id"],
            "id": scenario["id"],
            "step": scenario["step"],
            "generated_params": f"llm_error: {e}",
            "raw_response": f"error: {e}",
            "step_inputs": scenario["step_inputs"],
            "allowed_keys": scenario["allowed_keys"]
        }

if __name__ == "__main__":
    # Load scenarios
    with open(SCENARIOS_FILE, "r") as f:
        scenarios = json.load(f)
    
    # Load expected results
    try:
        with open(EXPECTED_RESULTS_FILE, "r") as f:
            expected_results = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {EXPECTED_RESULTS_FILE} not found. Run 02_pick_expected_params.py first.")
        expected_results = []
    
    # Create expected results map
    expected_map = {e["id"]: e["expected_params"] for e in expected_results}
    
    print(f"Generating parameters for {len(scenarios)} scenarios...")
    
    # Generate parameters in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=LLM_WORKERS) as executor:
        results = list(tqdm(
            executor.map(generate_parameters, scenarios),
            total=len(scenarios),
            desc="Parameter generation",
            unit="scenario"
        ))
    
    # Evaluate results if we have expected data
    evaluated_results = []
    correct_count = 0
    total_score = 0
    
    for result in results:
        scenario_id = result["id"]
        
        if scenario_id in expected_map:
            expected_params = expected_map[scenario_id]
            
            scores, details = evaluate_param_generation(
                {"id": scenario_id},
                result["generated_params"],
                expected_params
            )
            
            result["evaluation"] = {
                "expected_params": expected_params,
                "scores": scores,
                "details": details
            }
            
            # Count as correct if total score > 0.7
            if scores["total_score"] > 0.7:
                correct_count += 1
            
            total_score += scores["total_score"]
        
        evaluated_results.append(result)
    
    # Save results
    with open(OUTPUT_FILE, "w") as f:
        json.dump(evaluated_results, f, indent=2)
    
    # Print summary
    if expected_map:
        accuracy = correct_count / len(expected_map) if expected_map else 0
        avg_score = total_score / len(expected_map) if expected_map else 0
        
        print(f"\n✅ Parameter Generation Results:")
        print(f"📊 Accuracy (>0.7 score): {correct_count}/{len(expected_map)} = {accuracy:.2%}")
        print(f"📊 Average Score: {avg_score:.3f}")
        print(f"📁 Results saved to {OUTPUT_FILE}")
    else:
        print(f"\n✅ Generated parameters for {len(scenarios)} scenarios")
        print(f"📁 Results saved to {OUTPUT_FILE}")
        print("⚠️  No evaluation performed - run 02_pick_expected_params.py to set expected results")