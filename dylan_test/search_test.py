import json
from jentic_agents.platform.jentic_client import JenticClient
import os
from jentic_agents.utils.llm import LiteLLMChatLLM
import re

QUERIES_FILE = "search_queries.json"
RESULTS_FILE = "search_results.json"
TOP_K = 10

SEARCH_QUERIES = [
    {"provider": "Google", "goal": "Email John about the project update using Gmail"},
    {"provider": "Google", "goal": "Add a team sync to my Google Calendar for next Friday at 2pm"},
    {"provider": "Google", "goal": "Put the quarterly report in my Drive, in the Reports folder"},
    {"provider": "Google", "goal": "Show me NASA’s latest YouTube videos"},
    {"provider": "Microsoft", "goal": "Set up a Teams meeting with marketing for Thursday afternoon"},
    {"provider": "Microsoft", "goal": "Remind my team about the deadline via Outlook"},
    {"provider": "Slack", "goal": "Say good morning to everyone in #general on Slack"},
    {"provider": "Twilio", "goal": "Text me a 2FA code with Twilio"},
    {"provider": "GitHub", "goal": "Open a bug for the website’s contact form on GitHub"},
    {"provider": "Discord", "goal": "Welcome new members in the introductions channel on Discord"},
    {"provider": "Stripe", "goal": "Make a $50 donation link with Stripe and send it to the donor"},
    {"provider": "Notion", "goal": "Start a 2024 Goals page in Notion with a checklist"},
    {"provider": "Asana", "goal": "Assign Alex to review the Q2 budget in Asana, due next Monday"},
    {"provider": "Trello", "goal": "Add a card to update the homepage on my Trello board"},
    {"provider": "Zapier", "goal": "Automatically save Gmail attachments to Dropbox with Zapier"},
    {"provider": "Jira", "goal": "File a login bug in the Mobile App project on Jira"},
    {"provider": "Salesforce", "goal": "Add Jamie Smith as a lead in Salesforce, jamie@example.com"},
    {"provider": "HubSpot", "goal": "Log a new contact from the conference in HubSpot"},
    {"provider": "Dropbox", "goal": "Upload the latest team photo to Dropbox, Team Photos folder"},
    {"provider": "Shopify", "goal": "Get my most recent Shopify orders"},
    {"provider": "Zoom", "goal": "Book a Zoom call for the product team next Wednesday at 10am"},
    {"provider": "SendGrid", "goal": "Email my newsletter list about our new product launch using SendGrid"},
    {"provider": "Mailchimp", "goal": "Add newuser@example.com to my Mailchimp list"},
    {"provider": "Airtable", "goal": "Add Blue Widget to my Inventory base in Airtable"},
    {"provider": "Box", "goal": "Put the signed contract in my Box Contracts folder"},
    {"provider": "OneDrive", "goal": "Save the updated project plan to OneDrive, Projects/2024"},
    {"provider": "Twitter", "goal": "Tweet that our new app is live!"},
    {"provider": "Spotify", "goal": "Add Here Comes the Sun to my Morning Motivation playlist on Spotify"},
    {"provider": "Telegram", "goal": "Let my Telegram group know the meeting starts in 10 minutes"},
    {"provider": "OpenAI", "goal": "Summarize this article about climate change in 2024 using OpenAI"},
]

def save_queries_to_file(filename, queries):
    with open(filename, 'w') as f:
        json.dump(queries, f, indent=2)

def load_queries_from_file(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def save_results_to_file(filename, results):
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)

# Save queries to file if not already present
if not os.path.exists(QUERIES_FILE):
    save_queries_to_file(QUERIES_FILE, SEARCH_QUERIES)
    print(f"Saved {len(SEARCH_QUERIES)} queries to {QUERIES_FILE}")

API_KEY = os.getenv("JENTIC_API_KEY")

LLM_BULLET_PROMPT = """
    <role>
    You are a world-class planning assistant operating within the Jentic platform.
    Jentic enables agentic systems to discover, evaluate, and execute API operations through a unified agent interface, powered by the Open Agentic Knowledge (OAK) project and MCP (Multi-Agent Coordination Protocol) protocol. You specialize in transforming high-level user goals into structured, step-by-step plans that can be executed by Jentic-aligned agents.

    Your responsibilities include:
    - Decomposing goals into modular, API-compatible actions
    - Sequencing steps logically with clear data flow
    - Labeling outputs for downstream use in later steps
    - Anticipating failure points and providing graceful fallback logic

    Each step you output may correspond to an API lookup, data transformation, or action — and is designed to be executed by another system, not a human. Your plans must be structurally strict and executable without revision.
    </role>

    <main_instructions>
    Transform the user’s goal into a structured **markdown bullet-list plan**, optimized for execution by API-integrated agents.

    Output rules:
    1. Output only the fenced list using triple backticks — no prose before or after.
    2. Top-level steps begin with `- ` and no indentation.
    3. Sub-steps must be indented by exactly two spaces.
    4. Each step must follow this format:  
      `<verb> <object>` followed by:
      - `(input: input_a, input_b)` — if the step requires prior outputs
      - `(output: result_key)` — a **required** unique snake_case identifier
    5. Use `input:` only when the step depends on earlier step outputs.
    6. Do **not** include tool names, APIs, markdown formatting outside the fenced block, or explanatory prose.
    7. Try to use CRUD specific verbs in your steps.
    </main_instructions>

    <keyword_instructions>
    For each step that requires an API or tool call (e.g., a Jentic tool execution), generate a concise keyword search query to facilitate tool discovery:
    - Create a search query of 5-7 capability-focused keywords describing the required functionality for that step.
    - Include EXACTLY ONE provider/platform keyword (e.g., 'github', 'discord', 'trello') if the platform is clear from the step context; otherwise omit.
    - Do NOT combine multiple providers or API platforms in the same query.
    - Do NOT include irrelevant terms.
    - Focus on clear, action-oriented keywords and CRUD specific verbs based on the current step, yet taking the overall goal into consideration.
    - Output the keyword search query as a sibling bullet under the step, prefixed by: `→ keyword search query: "<query>"`.
    - If the step is a reasoning, data transformation, summarization, or any AI-only operation that does not require an API/tool call, do **not** output a keyword search query line.
    </keyword_instructions>

    <self_check>
    Before returning your answer, silently confirm all of the following:
    - All output keys are unique and use snake_case.
    - All input keys reference a valid prior `output:` key.
    - Indentation is strictly correct: 0 for top-level, 2 spaces for sub-items.
    - No extraneous text or formatting appears outside the code block.
    </self_check>

    <examples>
    Example 1 — Goal: “Search NYT articles about artificial intelligence and send them to Discord channel 12345”
    ```
    - Get recent New York Times (NYT) articles mentioning “artificial intelligence” (output: nyt_articles)
      → keyword search query: "get article nytimes new york times search query filter"
    - send articles as a Discord message to Discord channel 12345 (input: nyt_articles) (output: post_confirmation)
      → keyword search query: "send message discord channel post content"
    ```

    Example 2 — Goal: “Gather the latest 10 Hacker News posts about ‘AI’, summarise them, and email the summary to alice@example.com”
    ```
    - fetch latest 10 Hacker News posts containing “AI” (output: hn_posts)
      → keyword search query: "get fetch posts hackernews searchquery filter"
    - summarise hn_posts into a concise bullet list (input: hn_posts) (output: summary_text)
    - email summary_text to alice@example.com (input: summary_text) (output: email_confirmation)
      → keyword search query: "post send email gmail to user"
    ```
    </examples>

    <goal>
    Goal: {goal}
    </goal>
"""

LLM_RESULTS_FILE = "llm_tool_selection_results.json"

PLAN_RESULTS_FILE = "llm_bullet_plans.json"
KEYWORD_QUERIES_FILE = "llm_keyword_search_queries.json"
KEYWORD_TOOL_SEARCH_RESULTS_FILE = "keyword_tool_search_results.json"

model_name = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")

if __name__ == "__main__":
    queries = load_queries_from_file(QUERIES_FILE)
    client = JenticClient(api_key=API_KEY)
    llm = LiteLLMChatLLM(model=model_name, temperature=0.2)
    all_results = []
    all_plans = []
    all_keyword_queries = []
    all_keyword_tool_search_results = []
    for entry in queries:
        provider = entry["provider"]
        goal = entry["goal"]
        print(f"\n=== Provider: {provider} | Goal: {goal} ===")
        prompt = LLM_BULLET_PROMPT.format(goal=goal)
        llm_messages = [
            {"role": "system", "content": "You are a world-class planning assistant operating within the Jentic platform."},
            {"role": "user", "content": prompt}
        ]
        try:
            plan = llm.chat(llm_messages).strip()
        except Exception as e:
            plan = f"llm_error: {e}"
        all_plans.append({
            "provider": provider,
            "goal": goal,
            "plan": plan
        })
        # Extract keyword search queries from the plan
        keyword_queries = []
        if plan.startswith("```"):
            plan_body = plan.strip('`\n')
        else:
            plan_body = plan
        for match in re.finditer(r'→ keyword search query: "([^"]+)"', plan_body):
            keyword_queries.append(match.group(1))
        all_keyword_queries.append({
            "provider": provider,
            "goal": goal,
            "keyword_search_queries": keyword_queries
        })
        # For each keyword search query, perform a tool search and save results
        for keyword_query in keyword_queries:
            try:
                search_results = client.search(keyword_query, top_k=10)
            except Exception as e:
                search_results = f"search_error: {e}"
            all_keyword_tool_search_results.append({
                "provider": provider,
                "goal": goal,
                "keyword_search_query": keyword_query,
                "tool_search_results": search_results
            })
    save_results_to_file(PLAN_RESULTS_FILE, all_plans)
    save_results_to_file(KEYWORD_QUERIES_FILE, all_keyword_queries)
    save_results_to_file(KEYWORD_TOOL_SEARCH_RESULTS_FILE, all_keyword_tool_search_results)
    print(f"\nSaved all LLM bullet plans to {PLAN_RESULTS_FILE}")
    print(f"Saved all extracted keyword search queries to {KEYWORD_QUERIES_FILE}")
    print(f"Saved all tool search results for keyword queries to {KEYWORD_TOOL_SEARCH_RESULTS_FILE}")


