import json
from collections import defaultdict

RESULTS_FILE = "prompt_experimentation/data/param_generation_results.json"
REPORT_FILE = "prompt_experimentation/data/param_generation_comparison_report.json"

def analyze_common_errors(results):
    """Analyze common patterns in parameter generation errors"""
    
    error_patterns = {
        "json_parse_errors": [],
        "missing_required_keys": defaultdict(int),
        "extra_keys_added": defaultdict(int),
        "value_type_mismatches": defaultdict(int),
        "common_mistakes": []
    }
    
    for result in results:
        if "evaluation" not in result:
            continue
            
        evaluation = result["evaluation"]
        details = evaluation["details"]
        
        # JSON parse errors
        if details.get("json_parse_error"):
            error_patterns["json_parse_errors"].append({
                "scenario": result["id"],
                "error": details["json_parse_error"],
                "raw_response": result["raw_response"][:100] + "..."
            })
        
        # Missing keys
        for key in details.get("missing_keys", []):
            error_patterns["missing_required_keys"][key] += 1
        
        # Extra keys
        for key in details.get("extra_keys", []):
            error_patterns["extra_keys_added"][key] += 1
        
        # Value mismatches
        for mismatch in details.get("value_mismatches", []):
            key = mismatch["key"]
            expected_type = type(mismatch["expected"]).__name__
            generated_type = type(mismatch["generated"]).__name__
            error_patterns["value_type_mismatches"][f"{key}: {expected_type} -> {generated_type}"] += 1
    
    return error_patterns

def generate_insights(results, error_patterns):
    """Generate insights and recommendations"""
    
    insights = []
    
    # Overall performance
    total_scenarios = len([r for r in results if "evaluation" in r])
    if total_scenarios > 0:
        high_scoring = len([r for r in results if r.get("evaluation", {}).get("scores", {}).get("total_score", 0) > 0.8])
        insights.append(f"High performance (>0.8 score): {high_scoring}/{total_scenarios} scenarios ({high_scoring/total_scenarios:.1%})")
    
    # JSON validity issues
    json_errors = len(error_patterns["json_parse_errors"])
    if json_errors > 0:
        insights.append(f"JSON formatting issues in {json_errors} scenarios - prompt may need clearer output format instructions")
    
    # Most problematic keys
    missing_keys = error_patterns["missing_required_keys"]
    if missing_keys:
        top_missing = sorted(missing_keys.items(), key=lambda x: x[1], reverse=True)[:3]
        insights.append(f"Most frequently missing keys: {', '.join([f'{k}({v}x)' for k, v in top_missing])}")
    
    # Unnecessary keys
    extra_keys = error_patterns["extra_keys_added"]
    if extra_keys:
        top_extra = sorted(extra_keys.items(), key=lambda x: x[1], reverse=True)[:3]
        insights.append(f"Most frequently added extra keys: {', '.join([f'{k}({v}x)' for k, v in top_extra])}")
    
    # Memory extraction issues
    memory_dependent_failures = 0
    for result in results:
        if (result.get("step_inputs") and 
            result.get("evaluation", {}).get("scores", {}).get("total_score", 0) < 0.5):
            memory_dependent_failures += 1
    
    if memory_dependent_failures > 0:
        insights.append(f"{memory_dependent_failures} scenarios with memory data had low scores - may indicate extraction issues")
    
    return insights

def create_detailed_report(results):
    """Create a detailed comparison report"""
    
    # Basic statistics
    total_scenarios = len(results)
    evaluated_scenarios = [r for r in results if "evaluation" in r]
    
    if not evaluated_scenarios:
        return {
            "summary": {
                "total_scenarios": total_scenarios,
                "evaluated_scenarios": 0,
                "message": "No evaluation data available. Run 02_pick_expected_params.py first."
            },
            "results": results
        }
    
    # Calculate metrics
    scores = [r["evaluation"]["scores"] for r in evaluated_scenarios]
    
    avg_json_valid = sum(s["json_valid"] for s in scores) / len(scores)
    avg_keys_correct = sum(s["keys_correct"] for s in scores) / len(scores)
    avg_values_appropriate = sum(s["values_appropriate"] for s in scores) / len(scores)
    avg_total_score = sum(s["total_score"] for s in scores) / len(scores)
    
    # Success rates
    high_performers = len([s for s in scores if s["total_score"] > 0.8])
    medium_performers = len([s for s in scores if 0.5 < s["total_score"] <= 0.8])
    low_performers = len([s for s in scores if s["total_score"] <= 0.5])
    
    # Error analysis
    error_patterns = analyze_common_errors(evaluated_scenarios)
    insights = generate_insights(evaluated_scenarios, error_patterns)
    
    # Best and worst performing scenarios
    best_scenarios = sorted(evaluated_scenarios, 
                           key=lambda x: x["evaluation"]["scores"]["total_score"], 
                           reverse=True)[:3]
    worst_scenarios = sorted(evaluated_scenarios, 
                            key=lambda x: x["evaluation"]["scores"]["total_score"])[:3]
    
    summary = {
        "total_scenarios": total_scenarios,
        "evaluated_scenarios": len(evaluated_scenarios),
        "performance_metrics": {
            "avg_json_validity": round(avg_json_valid, 3),
            "avg_key_correctness": round(avg_keys_correct, 3),
            "avg_value_appropriateness": round(avg_values_appropriate, 3),
            "avg_total_score": round(avg_total_score, 3)
        },
        "performance_distribution": {
            "high_performers": f"{high_performers}/{len(evaluated_scenarios)} ({high_performers/len(evaluated_scenarios):.1%})",
            "medium_performers": f"{medium_performers}/{len(evaluated_scenarios)} ({medium_performers/len(evaluated_scenarios):.1%})",
            "low_performers": f"{low_performers}/{len(evaluated_scenarios)} ({low_performers/len(evaluated_scenarios):.1%})"
        },
        "error_analysis": {
            "json_parse_errors": len(error_patterns["json_parse_errors"]),
            "most_missing_keys": dict(list(error_patterns["missing_required_keys"].items())[:5]),
            "most_extra_keys": dict(list(error_patterns["extra_keys_added"].items())[:5])
        },
        "insights": insights,
        "best_performing_scenarios": [
            {
                "id": s["id"],
                "step": s["step"][:60] + "...",
                "score": s["evaluation"]["scores"]["total_score"]
            } for s in best_scenarios
        ],
        "worst_performing_scenarios": [
            {
                "id": s["id"],
                "step": s["step"][:60] + "...",
                "score": s["evaluation"]["scores"]["total_score"],
                "main_issues": s["evaluation"]["details"].get("json_parse_error") or 
                              f"Missing: {len(s['evaluation']['details'].get('missing_keys', []))} keys"
            } for s in worst_scenarios
        ]
    }
    
    return {
        "summary": summary,
        "error_patterns": error_patterns,
        "results": results
    }

if __name__ == "__main__":
    # Load results
    try:
        with open(RESULTS_FILE, "r") as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"Error: {RESULTS_FILE} not found. Run 03_llm_param_generation_and_eval.py first.")
        exit(1)
    
    print("Generating parameter generation comparison report...")
    
    # Create detailed report
    report = create_detailed_report(results)
    
    # Save report
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    summary = report["summary"]
    
    print(f"\n{'='*60}")
    print("📊 PARAMETER GENERATION REPORT")
    print(f"{'='*60}")
    
    if "message" in summary:
        print(f"⚠️  {summary['message']}")
    else:
        print(f"📈 Scenarios Evaluated: {summary['evaluated_scenarios']}")
        print(f"📊 Average Total Score: {summary['performance_metrics']['avg_total_score']}")
        print(f"🎯 High Performers (>0.8): {summary['performance_distribution']['high_performers']}")
        
        print(f"\n🔍 Key Insights:")
        for insight in summary['insights']:
            print(f"  • {insight}")
        
        print(f"\n⭐ Best Performing:")
        for scenario in summary['best_performing_scenarios']:
            print(f"  • {scenario['id']}: {scenario['score']:.3f}")
        
        print(f"\n⚠️  Worst Performing:")
        for scenario in summary['worst_performing_scenarios']:
            print(f"  • {scenario['id']}: {scenario['score']:.3f} - {scenario['main_issues']}")
    
    print(f"\n📁 Full report saved to {REPORT_FILE}")
    print(f"{'='*60}")