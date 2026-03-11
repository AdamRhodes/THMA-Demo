# THMA Integration Demo

A full-stack data integration pipeline demonstrating the core skills for the **Data Integration Engineer** role at The Health Management Academy.

## Architecture

```
                                   ┌──────────────────┐
                                   │  Power Automate   │
                                   │  (Scheduled Flow) │
                                   │  Trigger + Alert  │
                                   └────────┬─────────┘
                                            │ HTTP POST
                                            ▼
┌──────────────┐     REST API      ┌──────────────┐     MERGE/Upsert    ┌──────────────┐
│  Salesforce   │ ──────────────►  │  Python ETL   │ ──────────────────► │  Azure SQL   │
│  (CRM Data)   │   simple-salesforce│  (pandas)    │    sqlalchemy       │  Database    │
└──────────────┘                   └──────────────┘                     └──────┬───────┘
                                                                               │
                                          ┌────────────────────────────────────┤
                                          │                                    │
                                          ▼                                    ▼
                                   ┌──────────────┐                     ┌──────────────┐
                                   │   FastAPI     │                     │   Power BI   │
                                   │  (Your API)   │                     │  Dashboard   │
                                   │  /docs = demo │                     │              │
                                   └──────────────┘                     └──────────────┘
```

**Skills covered:** REST APIs (consuming + building), SQL (Azure SQL), ETL/data pipelines, data modeling, error handling, logging/monitoring, Python, Power BI, Power Automate, Git.

---

## Setup Checklist (Tonight's Plan)

Work through these in order. Each step builds on the previous.

### Step 1: Salesforce Developer Edition (~15 min)

- [ ] Go to https://developer.salesforce.com/signup
- [ ] Fill out the form (use a personal email)
- [ ] Check email for verification link → activate your org
- [ ] Log in at https://login.salesforce.com
- [ ] Explore the UI: click through **Accounts**, **Contacts**, **Opportunities** tabs
- [ ] Note: Dev Edition comes with sample data already populated!
- [ ] Get your Security Token:
  - Click your avatar → **Settings** → **Reset My Security Token**
  - Token is emailed to you (you'll need it for the API)
- [ ] Test the API: In Salesforce, go to **Developer Console** (gear icon → Developer Console)
  - Run a SOQL query: `SELECT Id, Name FROM Account LIMIT 5`
  - This is the same query language the ETL script uses

### Step 2: Azure SQL Database (~20 min)

- [ ] If you don't have an Azure account: https://azure.microsoft.com/free/ ($200 credit)
- [ ] If you already have one: go to https://aka.ms/azuresqlhub
- [ ] Click **Try Azure SQL Database for free**
- [ ] Create the database:
  - Database name: `thma-demo`
  - Create or select a server (remember your admin username/password!)
  - Leave defaults (General Purpose, Serverless)
  - Make sure "Free offer" banner shows $0/month
- [ ] After creation, configure firewall:
  - Go to your SQL Server resource → **Networking**
  - Add your client IP address
  - Toggle **Allow Azure services** to Yes
- [ ] Open **Query Editor** in the portal (on the database page)
  - Log in with your admin credentials
  - Copy/paste the contents of `schema.sql` and run it
  - This creates the tables, indexes, and views

### Step 3: Install ODBC Driver (Windows) (~5 min)

- [ ] Download **ODBC Driver 18 for SQL Server**:
  https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- [ ] Install it (next, next, finish)
- [ ] This is what `pyodbc` uses to connect to Azure SQL

### Step 4: Python Environment (~10 min)

```bash
# Clone or copy this project to your machine
cd thma-integration-demo

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your credentials
copy .env.example .env
# Edit .env with your Salesforce + Azure SQL credentials
```

### Step 5: Run the ETL Pipeline (~15 min)

```bash
# First, do a dry run (extract + transform only, no DB writes)
python pipeline.py --dry-run

# If that looks good, run the full pipeline
python pipeline.py
```

You should see structured log output showing:
- Salesforce authentication
- Records extracted per object
- Transform stats (dedup counts, null counts)
- Records upserted into Azure SQL

**Verify in Azure Portal:**
- Go to your database → Query Editor
- `SELECT COUNT(*) FROM accounts`
- `SELECT COUNT(*) FROM contacts`
- `SELECT * FROM sync_log`

### Step 6: Start the API (~15 min)

```bash
# Start the FastAPI server
uvicorn api.main:app --reload

# Or:
python -m api.main
```

- [ ] Open http://localhost:8000/docs in your browser
- [ ] This is Swagger UI - interactive API documentation!
- [ ] Try the endpoints:
  - **GET /health** - no auth needed
  - Click **Authorize** (top right), enter your API key from .env
  - **GET /accounts** - list all accounts
  - **GET /summary/pipeline** - aggregated pipeline data
  - **POST /sync/trigger** - trigger a sync from the API!

### Step 7: Power BI Dashboard + Power Query (~40 min)

**Power Query is a minimum qualification** — it's the data transformation engine
built into Power BI Desktop. When they say "Microsoft Power Platform (Power Automate,
Power Query)" this is what they mean for the data prep side.

**Connect to Azure SQL:**
- [ ] Open **Power BI Desktop** (install from Microsoft Store if needed)
- [ ] **Get Data** → **Azure SQL Database**
- [ ] Enter your server name and database name
- [ ] Authenticate with your SQL credentials
- [ ] Select tables: `accounts`, `contacts`, `opportunities`
- [ ] **Important: click "Transform Data" instead of "Load"** — this opens Power Query Editor

**Power Query Editor — spend 10-15 minutes here:**
- [ ] Notice it loaded your tables as queries on the left panel
- [ ] On the `contacts` table, try these transforms:
  - **Remove columns**: drop `synced_at` (Home → Remove Columns)
  - **Rename columns**: right-click `last_name` → Rename to "Last Name" (user-friendly)
  - **Change types**: click the type icon on `created_date` → change to Date/Time
  - **Filter rows**: click the dropdown on `department` → uncheck (null) to remove blanks
  - **Merge queries**: Home → Merge Queries → join `contacts` to `accounts` on `account_id` = `id`
    - Expand the merged column to pull in `name` as "Account Name"
    - This is the Power Query equivalent of a SQL JOIN
- [ ] On the `opportunities` table:
  - **Add custom column**: Add Column → Custom Column → name it "Deal Size"
    - Formula: `if [amount] > 50000 then "Large" else if [amount] > 10000 then "Medium" else "Small"`
    - This is Power Query's M language — the equivalent of pandas transforms
  - **Group by**: try Home → Group By → group by `stage_name`, sum of `amount`
    - Cancel this after seeing the result (you want the raw data for visuals)
- [ ] Notice the **Applied Steps** panel on the right — this is the transform history
  - Each step is recorded and replayable (like a visual version of your transform.py)
  - Steps can be reordered, deleted, edited
  - This is what they mean by Power Query in the job posting
- [ ] Click **Close & Apply** to load the transformed data into the report

**Build your visuals:**
- [ ] Build 2-3 visuals:
  - **Bar chart**: Pipeline value by stage (drag `stage_name` to Axis, `amount` to Values)
  - **Table**: Top accounts by opportunity value
  - **Card**: Total pipeline value, total contacts
  - (Optional) **Donut chart**: Opportunities by Deal Size (your custom column!)
- [ ] Save the .pbix file in the project directory

**What to be able to talk about:**
- Power Query M language vs. DAX: M is for data prep (ETL), DAX is for measures/calculations
- Power Query is the low-code equivalent of your pandas transform.py
- The Applied Steps panel = a visual pipeline, just like your ETL phases
- In production at THMA, Power Query would handle lighter transforms (renaming, filtering,
  type casting) while heavier logic stays in Python or the Azure SQL views

### Step 8: Power Automate — Scheduled Sync Flow (~30 min)

This is a minimum qualification on the posting. You're building a cloud flow that
automates your ETL pipeline on a schedule and sends a notification — exactly what
this role does day-to-day with Power Automate.

**Sign up:**
- [ ] Go to https://make.powerautomate.com
- [ ] Sign in with a Microsoft account (personal works for trial)
- [ ] If prompted, start the free 30-day trial for premium connectors

**Build the flow — Option A (calls your FastAPI directly):**

This is the best option if your API is running and reachable (e.g., via ngrok or
deployed somewhere). It shows Power Automate triggering your custom API.

- [ ] Click **+ Create** → **Scheduled cloud flow**
- [ ] Name it: `Daily Salesforce Sync`
- [ ] Set schedule: every 1 day (or every 5 minutes for demo purposes)
- [ ] **Add action** → search for **HTTP** (premium connector)
  - Method: `POST`
  - URI: `http://your-api-url:8000/sync/trigger`
  - Headers: `X-API-Key` = your API key from .env
- [ ] **Add action** → **Condition**
  - Check if Status Code equals 200
- [ ] **If yes** branch → Add action → **Send an email (V2)** (Outlook connector)
  - To: your email
  - Subject: `✅ THMA Sync Complete`
  - Body: `Pipeline sync triggered successfully at @{utcNow()}`
- [ ] **If no** branch → Add action → **Send an email (V2)**
  - Subject: `❌ THMA Sync Failed`
  - Body: `Pipeline sync failed. Check /sync/status for details.`
- [ ] Click **Save** → **Test** → **Manually** → **Run flow**
- [ ] Screenshot the successful run — great for the interview!

**Build the flow — Option B (monitors Azure SQL directly):**

This works even if your API isn't publicly accessible. It shows Power Automate
connecting directly to Azure SQL — one of the core patterns THMA uses.

- [ ] Click **+ Create** → **Scheduled cloud flow**
- [ ] Name it: `Sync Monitor & Alert`
- [ ] Set schedule: every 1 hour
- [ ] **Add action** → search for **SQL Server** → **Execute a SQL query (V2)**
  - Server: your-server.database.windows.net
  - Database: thma-demo
  - Query:
    ```sql
    SELECT TOP 1 run_id, status, error_message, completed_at
    FROM sync_log
    ORDER BY started_at DESC
    ```
- [ ] **Add action** → **Condition**
  - `status` is equal to `failed`
- [ ] **If yes** → **Send an email (V2)**
  - Subject: `⚠️ Pipeline Failure Detected`
  - Body: `Run @{items('...')?['run_id']} failed: @{items('...')?['error_message']}`
- [ ] **If no** → do nothing (or optionally log to a SharePoint list)
- [ ] **Save** and **Test**

**Bonus things to explore (if time allows):**
- [ ] Look at the **Flow checker** — shows errors and warnings (like a linter)
- [ ] Check the **Run history** — shows execution time, inputs/outputs per step
- [ ] Try the **Power Query** connector — this is Power Platform's built-in ETL tool
- [ ] Browse the connector gallery — note that Salesforce, Azure SQL, and
      many of the SaaS tools THMA uses have pre-built connectors

**What to notice and be able to talk about:**
- The visual flow builder is a no-code/low-code version of the Python pipeline
  you built — same concepts (trigger → action → condition → action)
- Connectors abstract away REST API details (auth, endpoints, pagination)
- Run history = built-in monitoring (like your sync_log table but visual)
- Error handling uses the same pattern: try/catch with branching
- In production, THMA would likely use Power Automate for simpler flows
  (notifications, approvals, file sync) and Python/Tray.io for heavier ETL

### Step 9: Git (~5 min)

```bash
git init
git add .
git commit -m "Initial commit: Salesforce-Azure SQL integration pipeline"
```

Add a `.gitignore`:
```
.env
venv/
__pycache__/
*.pyc
pipeline.log
*.pbix
```

---

## What to Emphasize in the Interview

1. **REST API fluency**: "I consumed the Salesforce REST API for extraction and built my own API with FastAPI to serve the data. I understand authentication, endpoints, error handling, and pagination on both sides."

2. **Data pipeline design**: "The pipeline follows a clean ETL pattern with separation of concerns. Each phase is independently testable. The MERGE/upsert pattern handles both new and updated records idempotently."

3. **Error handling & monitoring**: "I built in retry logic with exponential backoff for transient API failures, structured logging to both console and file, and a sync_log table that tracks every pipeline run - records extracted, loaded, and any errors."

4. **Data modeling**: "I designed the SQL schema to mirror the Salesforce object model while optimizing for reporting queries. The views provide denormalized data ready for Power BI. Indexes target the most common filter patterns."

5. **Power Query**: "When I connected Power BI to Azure SQL, I used Power Query Editor to do additional transforms — renaming columns for business users, filtering nulls, merging tables with joins, and creating custom columns with conditional logic. The Applied Steps panel is basically a visual transform pipeline, like a low-code version of pandas. I understand that M language handles data prep while DAX handles calculations and measures."

6. **Power Automate**: "I built a scheduled cloud flow that triggers my sync pipeline and sends email alerts on success or failure. The visual builder is intuitive — connectors abstract away the REST API details, and the run history gives you built-in monitoring. I can see how THMA would use this for lighter automation like approval workflows, notifications, and file routing between SaaS apps."

7. **Tray.io / iPaaS concepts**: "I haven't used Tray.io directly, but I understand it fills the iPaaS role — a visual platform for building the same integration logic I wrote in Python: connecting APIs, mapping data between schemas, handling errors, and scheduling syncs. The concepts are identical. My Python pipeline is essentially a code-first version of what Tray.io does with a drag-and-drop interface. I'd ramp up on the visual builder quickly because I already understand the underlying architecture — auth flows, webhooks, data transformation, retry logic. In practice, you'd choose between code (Python) and iPaaS (Tray.io) depending on the complexity: Tray.io for standard connector-to-connector flows, Python for heavy transforms or custom logic."

8. **Adaptability**: "If THMA needed to add a new data source like Cvent or NetSuite, the architecture supports it — add a new extract module, transform module, and table. The pattern is the same. In Power Automate or Tray.io, it's the same idea: add a new connector and wire it into the existing flow."

---

## THMA SaaS Ecosystem — API Cheat Sheet

You won't have hands-on time with all of these tonight, but if the interviewer
asks "how would you approach integrating X?" you should be able to speak to each
one. Here's what you need to know:

### Salesforce (CRM) — You Built This

- **Auth**: OAuth 2.0 (connected app flow for production, username+password+token for dev)
- **Query language**: SOQL (Salesforce Object Query Language) — SQL-like but Salesforce-specific
- **Key objects for THMA**: Account (health systems), Contact (people), Opportunity (pipeline),
  Campaign (marketing), Event (custom objects for their convenings)
- **Pagination**: `query_all()` handles it, but raw API uses `nextRecordsUrl` cursor
- **Rate limits**: 15,000 API calls per 24 hours for Developer Edition
- **Cvent also has a pre-built Salesforce connector** — so some data may flow
  Cvent → Salesforce → Azure SQL rather than Cvent → Azure SQL directly

### Cvent (Events Platform)

- **What it does for THMA**: Manages their convenings, meetings, and events — registration,
  attendee tracking, session management. THMA is a membership org that runs executive meetings,
  so this is a core business tool.
- **API**: REST API with OAuth 2.0 client credentials flow
- **Key objects**: Events, Contacts, Attendees, Sessions, Registrations
- **Integration pattern for THMA**: Pull event + attendee data → join with Salesforce Contacts
  in Azure SQL → "Which members attended which convenings?" → Power BI dashboard showing
  member engagement
- **Rate limits**: Tiered — Free (1,000/day), Professional (15,000/day), Enterprise (500,000/day)
- **Gotcha**: Cvent has both REST and legacy SOAP APIs — they're migrating to REST

### Alchemer (Surveys, formerly SurveyGizmo)

- **What it does for THMA**: Likely used for member satisfaction surveys, event feedback,
  and research data collection from health system executives
- **API**: Simple REST API, v5 is current. Auth via API key + token in query params
- **Key objects**: Survey, SurveyResponse, SurveyQuestion, SurveyContact
- **Integration pattern for THMA**: Pull survey responses → match respondents to Salesforce
  Contacts by email → load into Azure SQL → "How satisfied are our members?" or
  "What topics do executives want at the next convening?"
- **Pagination**: 50 results per page default, max 500 via `resultsperpage` param
- **Note**: Responses are keyed by email, making the join to Salesforce Contacts natural

### NetSuite (ERP — Finance)

- **What it does for THMA**: Financial system — invoicing, revenue, accounts receivable,
  membership billing. Finance team needs this data joined with CRM data.
- **API**: SuiteTalk REST Web Services. Auth via OAuth 2.0 or Token-Based Authentication (TBA)
- **Key objects**: Customer, Invoice, SalesOrder, Transaction, Vendor, Item
- **Query language**: SuiteQL — a SQL-like language for complex queries and joins
- **Integration pattern for THMA**: Pull invoice/revenue data → join with Salesforce Accounts
  in Azure SQL → "Revenue by member organization" or "Outstanding invoices by account"
  → Power BI dashboard for Finance team
- **Gotcha**: NetSuite has SOAP and REST APIs. REST is newer and simpler but SOAP
  is more mature with fuller feature coverage. THMA likely uses both.

### Marketo / Salesloft (Marketing & Sales Engagement)

- **What they do for THMA**: Marketo = marketing automation (email campaigns, lead scoring,
  nurture programs). Salesloft = sales engagement (outreach cadences, email tracking).
- **Marketo API**: REST with OAuth 2.0. Key objects: Leads, Activities, Programs, Campaigns.
  Marketo Leads map to Salesforce Contacts/Leads via a native sync.
- **Salesloft API**: REST with OAuth 2.0. Key objects: People, Cadences, Emails, Calls.
- **Integration pattern for THMA**: Marketing engagement data → Azure SQL → join with
  Salesforce pipeline data → "Which campaigns are driving membership renewals?"
  → Power BI for Marketing and Sales leadership

### Asana (Project Management)

- **What it does for THMA**: Internal project tracking, probably for convening planning,
  content development, and cross-team coordination
- **API**: REST with Personal Access Token or OAuth 2.0
- **Key objects**: Tasks, Projects, Workspaces, Sections, Custom Fields
- **Integration pattern for THMA**: Likely lighter integration — maybe syncing task
  completion status to a dashboard, or auto-creating Asana tasks when a Salesforce
  Opportunity hits a certain stage (via Power Automate or Tray.io)

### Zoom Meetings/Webinars

- **What it does for THMA**: Virtual convenings and member meetings
- **API**: REST with OAuth 2.0 or JWT. Key objects: Meetings, Webinars, Registrants,
  Participants, Reports
- **Integration pattern for THMA**: Pull meeting/webinar attendance → join with Cvent
  registration and Salesforce Contacts → "Member participation across virtual and
  in-person events" → comprehensive engagement dashboard

### The Big Picture for THMA

All of these systems need to flow into a **single source of truth** in Azure SQL:

```
Salesforce ──┐
Cvent ───────┤
Alchemer ────┤     Azure SQL          Power BI
NetSuite ────┼──►  (unified schema) ──► (dashboards for Sales,
Marketo ─────┤                           Marketing, Finance)
Salesloft ───┤
Asana ───────┤
Zoom ────────┘
```

The job is making sure data flows reliably from left to right, stays clean,
and the business teams on the right can trust what they see. That's exactly
what your demo project does for the Salesforce slice — and in the interview
you can articulate how you'd extend it to each additional system.

---

## Project Structure

```
thma-integration-demo/
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── config.py             # Centralized settings (pydantic-settings)
├── schema.sql            # Azure SQL table definitions + views
├── pipeline.py           # ETL orchestrator with logging
├── etl/
│   ├── extract.py        # Salesforce API extraction + retry logic
│   ├── transform.py      # pandas cleaning & normalization
│   └── load.py           # Azure SQL upsert via MERGE
├── api/
│   ├── main.py           # FastAPI application (your API!)
│   ├── models.py         # Pydantic data models
│   └── database.py       # DB connection helper
└── README.md             # This file
```
