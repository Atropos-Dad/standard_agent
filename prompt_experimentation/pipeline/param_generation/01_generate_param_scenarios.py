import json
import os
from tqdm import tqdm

# Parameter generation test scenarios - similar to SEARCH_QUERIES but for parameter testing
PARAMETER_TEST_SCENARIOS = [
    {
        "id": "discord_simple_message",
        "step": "send message 'Hello team!' to Discord channel 12345",
        "step_inputs": {},
        "tool_schema": {
            "parameters": {
                "channel_id": {"type": "string", "required": True},
                "content": {"type": "string", "required": True}
            }
        },
        "allowed_keys": ["channel_id", "content"]
    },
    {
        "id": "discord_news_articles",
        "step": "send the latest 3 news articles to Discord channel #general",
        "step_inputs": {
            "news_articles": [
                {
                    "title": "AI Breakthrough in 2024",
                    "url": "https://techcrunch.com/ai-breakthrough",
                    "summary": "Scientists achieve new milestone in AI research"
                },
                {
                    "title": "Tech Market Updates",
                    "url": "https://bloomberg.com/tech-market",
                    "summary": "Markets show positive trends for tech stocks"
                },
                {
                    "title": "Climate Change Report",
                    "url": "https://reuters.com/climate-report",
                    "summary": "New climate data shows concerning trends"
                },
                {
                    "title": "Space Exploration",
                    "url": "https://nasa.gov/mars-mission",
                    "summary": "Mars mission shows promising results"
                }
            ]
        },
        "tool_schema": {
            "parameters": {
                "channel_id": {"type": "string", "required": True},
                "content": {"type": "string", "required": True}
            }
        },
        "allowed_keys": ["channel_id", "content"]
    },
    {
        "id": "gmail_project_update",
        "step": "email john@company.com about the project status with subject 'Weekly Update'",
        "step_inputs": {
            "project_status": {
                "name": "Website Redesign",
                "completion": "75%",
                "next_milestone": "User Testing",
                "due_date": "2024-02-15",
                "blockers": ["Waiting for content from marketing team"]
            }
        },
        "tool_schema": {
            "parameters": {
                "to": {"type": "string", "required": True},
                "subject": {"type": "string", "required": True},
                "body": {"type": "string", "required": True}
            }
        },
        "allowed_keys": ["to", "subject", "body"]
    },
    {
        "id": "calendar_team_meeting",
        "step": "create a team meeting for next Friday at 2pm with Alice, Bob, and Charlie",
        "step_inputs": {
            "team_members": [
                {"name": "Alice", "email": "alice@company.com"},
                {"name": "Bob", "email": "bob@company.com"},
                {"name": "Charlie", "email": "charlie@company.com"}
            ],
            "next_friday": "2024-02-09"
        },
        "tool_schema": {
            "parameters": {
                "summary": {"type": "string", "required": True},
                "start": {"type": "string", "required": True},
                "attendees": {"type": "array", "required": False}
            }
        },
        "allowed_keys": ["summary", "start", "attendees"]
    },
    {
        "id": "github_bug_issue",
        "step": "create a GitHub issue for the login bug with priority high",
        "step_inputs": {
            "bug_report": {
                "title": "Users cannot login with Google OAuth",
                "description": "Multiple users report 500 error when using Google login",
                "steps_to_reproduce": [
                    "Go to login page",
                    "Click 'Sign in with Google'",
                    "Complete OAuth flow",
                    "Observe 500 error"
                ],
                "severity": "high",
                "reporter": "jane@company.com"
            }
        },
        "tool_schema": {
            "parameters": {
                "title": {"type": "string", "required": True},
                "body": {"type": "string", "required": True},
                "labels": {"type": "array", "required": False}
            }
        },
        "allowed_keys": ["title", "body", "labels"]
    },
    {
        "id": "slack_metrics_summary",
        "step": "post a few key metrics to #analytics channel",
        "step_inputs": {
            "daily_metrics": {
                "active_users": 1247,
                "revenue": "$23,456",
                "conversion_rate": "3.2%",
                "errors": 12,
                "response_time": "245ms",
                "new_signups": 34
            }
        },
        "tool_schema": {
            "parameters": {
                "channel": {"type": "string", "required": True},
                "text": {"type": "string", "required": True}
            }
        },
        "allowed_keys": ["channel", "text"]
    },
    {
        "id": "twitter_ai_thread",
        "step": "create a Twitter thread about recent AI developments",
        "step_inputs": {
            "ai_developments": [
                {
                    "title": "GPT-4 Vision Released",
                    "summary": "OpenAI releases multimodal capabilities",
                    "impact": "High",
                    "date": "2024-01-15"
                },
                {
                    "title": "Google Gemini Update", 
                    "summary": "Improved reasoning and coding abilities",
                    "impact": "High",
                    "date": "2024-01-20"
                },
                {
                    "title": "Meta AI Assistant",
                    "summary": "New AI assistant for Instagram and WhatsApp",
                    "impact": "Medium",
                    "date": "2024-01-25"
                }
            ]
        },
        "tool_schema": {
            "parameters": {
                "text": {"type": "string", "required": True}
            }
        },
        "allowed_keys": ["text"]
    },
    {
        "id": "drive_quarterly_report",
        "step": "upload the quarterly report to Google Drive Reports folder",
        "step_inputs": {
            "quarterly_report": {
                "filename": "Q4_Report_2024.pdf",
                "content": "Financial report showing 25% growth in Q4...",
                "size": "2.5MB"
            }
        },
        "tool_schema": {
            "parameters": {
                "name": {"type": "string", "required": True},
                "parents": {"type": "array", "required": False},
                "media_body": {"type": "string", "required": True}
            }
        },
        "allowed_keys": ["name", "parents", "media_body"]
    },
    {
        "id": "stripe_invoice_client",
        "step": "create an invoice for John Smith for web development services ($2,500)",
        "step_inputs": {
            "client_info": {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "company": "Smith Consulting"
            },
            "service_details": {
                "description": "Web development services - Q4 2024",
                "amount": 2500,
                "currency": "USD",
                "hours": 50,
                "hourly_rate": 50
            }
        },
        "tool_schema": {
            "parameters": {
                "customer_email": {"type": "string", "required": True},
                "amount": {"type": "number", "required": True},
                "currency": {"type": "string", "required": True},
                "description": {"type": "string", "required": False}
            }
        },
        "allowed_keys": ["customer_email", "amount", "currency", "description"]
    },
    {
        "id": "asana_task_assignment",
        "step": "assign Alex to review the Q2 budget in Asana, due next Monday",
        "step_inputs": {
            "budget_info": {
                "title": "Q2 Budget Review",
                "file_location": "/shared/budgets/Q2_2024.xlsx",
                "priority": "high"
            },
            "assignee": {
                "name": "Alex",
                "email": "alex@company.com"
            },
            "next_monday": "2024-02-12"
        },
        "tool_schema": {
            "parameters": {
                "name": {"type": "string", "required": True},
                "assignee": {"type": "string", "required": True},
                "due_on": {"type": "string", "required": False},
                "notes": {"type": "string", "required": False}
            }
        },
        "allowed_keys": ["name", "assignee", "due_on", "notes"]
    },
    {
        "id": "zoom_product_meeting",
        "step": "schedule a Zoom call for the product team next Wednesday at 10am",
        "step_inputs": {
            "meeting_details": {
                "topic": "Product roadmap discussion",
                "duration": 60,
                "agenda": ["Q1 features", "User feedback review", "Technical debt"]
            },
            "product_team": [
                {"name": "Sarah", "email": "sarah@company.com"},
                {"name": "Mike", "email": "mike@company.com"},
                {"name": "Lisa", "email": "lisa@company.com"}
            ],
            "next_wednesday": "2024-02-07T10:00:00"
        },
        "tool_schema": {
            "parameters": {
                "topic": {"type": "string", "required": True},
                "start_time": {"type": "string", "required": True},
                "duration": {"type": "number", "required": False}
            }
        },
        "allowed_keys": ["topic", "start_time", "duration"]
    },
    {
        "id": "shopify_recent_orders",
        "step": "get my most recent Shopify orders from the last week",
        "step_inputs": {
            "time_filter": {
                "period": "last_week",
                "start_date": "2024-01-29",
                "end_date": "2024-02-05"
            }
        },
        "tool_schema": {
            "parameters": {
                "created_at_min": {"type": "string", "required": False},
                "created_at_max": {"type": "string", "required": False},
                "limit": {"type": "number", "required": False}
            }
        },
        "allowed_keys": ["created_at_min", "created_at_max", "limit"]
    }
]

def generate_param_scenarios():
    """Generate parameter generation test scenarios"""
    
    print(f"Generating {len(PARAMETER_TEST_SCENARIOS)} parameter generation test scenarios...")
    
    # Add pair_id to each scenario
    for idx, scenario in enumerate(PARAMETER_TEST_SCENARIOS, 1):
        scenario["pair_id"] = str(idx)
    
    # Save to file
    output_file = "prompt_experimentation/data/param_generation_scenarios.json"
    with open(output_file, "w") as f:
        json.dump(PARAMETER_TEST_SCENARIOS, f, indent=2)
    
    print(f"✅ Generated {len(PARAMETER_TEST_SCENARIOS)} scenarios")
    print(f"📁 Saved to {output_file}")
    
    # Print scenario summary
    print("\n📊 Scenario Summary:")
    for scenario in PARAMETER_TEST_SCENARIOS:
        memory_keys = list(scenario['step_inputs'].keys()) if scenario['step_inputs'] else []
        memory_info = f" (memory: {', '.join(memory_keys)})" if memory_keys else " (no memory)"
        print(f"  • {scenario['id']}: {scenario['step'][:50]}...{memory_info}")

if __name__ == "__main__":
    generate_param_scenarios()