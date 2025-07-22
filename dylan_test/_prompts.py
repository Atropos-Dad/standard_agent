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