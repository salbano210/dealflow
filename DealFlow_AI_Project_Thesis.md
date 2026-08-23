# DealFlow AI — Project Thesis

## 1. Executive Summary

**DealFlow AI** is a portfolio project designed to simulate an internal AI system for a growth-equity investment firm such as Volition Capital.

The core thesis is:

> **AI should not replace the investment analyst. It should reduce the amount of repetitive information gathering, screening, and enrichment that happens before an analyst applies judgment.**

The project will model the earliest stages of the investment funnel:

1. Companies enter the sourcing pipeline.
2. The system enriches and structures available company information.
3. An LLM evaluates each company against a defined investment thesis.
4. The system produces a transparent, evidence-backed screening score.
5. Analysts review the AI output rather than blindly accepting it.
6. Companies that pass screening receive deeper automated research.
7. The system can prepare, but not autonomously send, founder outreach or create follow-up tasks.
8. Every AI-generated recommendation retains its source data, reasoning inputs, and human decision.

The project is intentionally **not** a fake CRM and is intentionally **not** another chatbot.

A lightweight database will serve as the system of record. The value of the project is the AI/data/automation layer built on top of that system.

---

# 2. Why This Project Exists

## The problem

A growth-equity analyst's job involves a large amount of high-value judgment, but also a significant amount of repetitive information processing.

Based on Volition's analyst role, analysts spend substantial time:

- Identifying potential investment opportunities
- Researching companies
- Engaging with founders
- Evaluating investment opportunities
- Conducting financial diligence
- Preparing companies for presentation to the investment team
- Driving diligence as opportunities progress through the funnel

Many of these activities involve collecting information from multiple sources, structuring it, comparing it against investment criteria, and producing an initial recommendation.

The bottleneck is not necessarily a lack of information.

It is the amount of **human time required to turn unstructured information into a useful starting point for judgment.**

## The proposed solution

jack_rAIn creates an automated first-pass research and screening layer.

Instead of asking an analyst to manually investigate every company from scratch, the system produces a standardized research package that answers:

- What is this company?
- Does it appear to fit our investment thesis?
- What evidence supports that conclusion?
- What information is missing?
- What are the most important risks?
- What should the analyst investigate next?

The analyst remains responsible for judgment.

---

# 3. Product Thesis

The fundamental product thesis is:

> **The best use of AI in investment sourcing is not autonomous investment decision-making; it is compressing the time between "we found this company" and "an analyst understands whether this company deserves attention."**

The project therefore optimizes for:

- Speed
- Consistency
- Transparency
- Evidence
- Human review
- Repeatability

It does **not** optimize for:

- Fully autonomous investment decisions
- Generating impressive-looking investment memos without evidence
- Replacing analysts
- Building a proprietary chatbot
- Recreating functionality already available through ChatGPT + MCP

---

# 4. Why Not Just Use ChatGPT + MCP?

This is an important architectural/product question.

If an analyst simply wants to ask:

> "What does this CIM say about revenue growth?"

ChatGPT connected to a document repository through MCP may already be an excellent solution.

There is little value in building a custom RAG chatbot simply to reproduce that experience.

DealFlow AI becomes valuable when the workflow is **persistent, automated, structured, and action-oriented.**

For example:

### ChatGPT + MCP

Human initiates:

> "Analyze Company X."

AI retrieves documents and answers.

### DealFlow AI

A company enters the pipeline.

The system automatically:

1. Detects the new company.
2. Retrieves available information.
3. Structures the information.
4. Applies the investment thesis.
5. Scores the opportunity.
6. Identifies missing information.
7. Generates research questions.
8. Stores the result.
9. Notifies the analyst.
10. Waits for human approval before consequential actions.

The difference is therefore not "better chatbot."

The difference is **workflow automation and system integration.**

---

# 5. Target User

## Primary user

A Volition-style investment analyst or associate responsible for sourcing and evaluating potential investments.

## Secondary users

- VP / Principal reviewing pipeline
- Partner reviewing high-priority opportunities
- Investment team members conducting diligence

The system should be designed around the analyst's workflow, not around showcasing AI features.

---

# 6. The Core User Journey

## Stage 1 — Company enters pipeline

A company record is added to the system.

Example:

```text
Company: Acme Software
Website: acme.com
Industry: B2B SaaS
Estimated Revenue: $45M
Estimated Growth: 38%
Founder-Owned: Unknown
Source: Conference / Founder Referral
Status: New
```

The system assigns the company a unique ID.

---

## Stage 2 — Data enrichment

The application retrieves available public or supplied information.

Potential sources include:

- Company website
- Public company databases
- SEC filings where applicable
- News APIs
- User-provided documents
- Structured company datasets

The goal is not to scrape the entire internet.

The goal is to gather enough information to create a useful first-pass profile.

---

## Stage 3 — Structured extraction

The LLM converts unstructured information into structured fields.

Example:

```json
{
  "business_model": "B2B SaaS",
  "target_customer": "Mid-market manufacturers",
  "estimated_revenue": 45000000,
  "estimated_growth": 0.38,
  "founder_led": true,
  "recurring_revenue": true,
  "market_category": "Supply Chain Software"
}
```

The application should validate this output rather than blindly trusting it.

---

# 7. Investment Thesis

For the purposes of the project, define a simplified hypothetical growth-equity thesis.

Example:

### Target company characteristics

- Founder-owned or founder-led
- B2B software / internet / tech-enabled services
- Attractive secular market
- Strong historical growth
- Meaningful recurring revenue
- Sufficient scale
- Capital-efficient business model
- Defensible competitive position

The actual thresholds should be configurable rather than hard-coded.

For example:

```text
Minimum revenue: $20M
Minimum growth: 25%
Preferred business model: recurring revenue
Founder ownership: preferred
Geography: North America
```

This is intentionally a **simulated investment thesis**, not a claim about Volition's actual proprietary underwriting criteria.

The project should clearly distinguish hypothetical project assumptions from publicly stated firm information.

---

# 8. AI Screening Framework

Each company receives a score based on explicit dimensions.

Example:

| Dimension | Weight |
|---|---:|
| Revenue growth | 25% |
| Business model | 20% |
| Founder ownership | 15% |
| Market attractiveness | 15% |
| Scale | 10% |
| Competitive positioning | 15% |

The exact weights are configurable.

The important design principle is:

> **The AI should explain the score using evidence rather than produce an unexplained 0–100 number.**

Example:

```text
Investment Fit: 87/100

Growth:              24/25
Business Model:      20/20
Founder Ownership:   15/15
Market:              13/15
Scale:                8/10
Competition:          7/15

Primary strengths:
- 38% estimated revenue growth
- Recurring B2B revenue
- Founder-led
- Large addressable market

Primary concerns:
- Competitive intensity appears high
- Limited evidence regarding retention

Missing information:
- Net revenue retention
- Gross margin
- Customer concentration
```

---

# 9. Evidence and Provenance

A critical design principle is that every meaningful AI conclusion should be traceable to evidence.

Instead of:

> "Acme has strong customer retention."

The system should produce:

> "Customer retention appears strong based on [source], which states X."

The application should store:

- Source URL/document
- Extracted text
- Date retrieved
- Data field
- AI-generated conclusion
- Model used
- Timestamp

This allows the analyst to distinguish:

**Known fact → inferred fact → missing information**

That distinction is particularly important in an investment context.

---

# 10. Human-in-the-Loop Design

The AI should not make investment decisions.

The workflow should contain explicit human checkpoints.

### Example

```text
AI Screening
     ↓
Analyst Review
     ↓
┌───────────────┬──────────────┐
│ Reject        │ Pursue       │
└───────────────┴──────────────┘
                      ↓
                AI Research
                      ↓
                Analyst Review
                      ↓
              Founder Outreach
                      ↓
                Human Approval
```

The system may recommend:

> "Pursue"

but the analyst must approve.

Similarly, the system may draft an email, but it should not automatically contact a founder.

---

# 11. Founder Outreach

Once an analyst decides to pursue a company, DealFlow AI can prepare a personalized outreach draft.

The system could use:

- Company description
- Recent company news
- Founder background
- Product information
- Specific reason the company fits the thesis

Example output:

```text
Subject: Acme Software

Hi Jane,

I've been following Acme's expansion into mid-market manufacturing
and was particularly interested in [specific company development].

We spend a lot of time working with founder-led software businesses
at similar stages and would enjoy learning more about what you're
building.

Would you be open to a brief conversation?
```

The important product principle:

> **AI drafts. Human approves.**

---

# 12. Research Questions

One of the highest-value outputs should not be a conclusion.

It should be a list of **questions the analyst should investigate next.**

For example:

```text
Recommended diligence questions:

1. What percentage of revenue is recurring?
2. What is net revenue retention?
3. How concentrated is the customer base?
4. What is gross margin?
5. What is the primary source of recent growth?
6. How much of growth is organic vs. acquired?
7. What is the competitive win/loss rate?
```

This shifts the AI from:

> "Here is my investment decision."

to:

> "Here is how I can help you perform better diligence."

That is the more defensible use case.

---

# 13. Minimal Technical Architecture

The first version should remain intentionally simple.

```text
                    ┌──────────────────┐
                    │ Company Database │
                    │ SQLite/Postgres  │
                    └────────┬─────────┘
                             │
                             ↓
                    ┌──────────────────┐
                    │ Python ETL Layer │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
         Company API     Web Data      Documents
              │              │              │
              └──────────────┼──────────────┘
                             ↓
                    ┌──────────────────┐
                    │ LLM Processing   │
                    │ Structured JSON  │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ Screening Engine │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ Analyst Review   │
                    └────────┬─────────┘
                             ↓
               ┌─────────────┼──────────────┐
               ↓             ↓              ↓
             Slack          CRM         Outreach
```

---

# 14. Suggested Technology Stack

## Backend

**Python**

Primary language for:

- ETL
- API integrations
- data processing
- LLM calls
- scoring
- automation

## API framework

**FastAPI**

Use FastAPI to expose endpoints such as:

```text
POST /companies
POST /companies/{id}/screen
POST /companies/{id}/research
GET  /companies/{id}
POST /companies/{id}/approve
POST /companies/{id}/outreach
```

## Database

Start with:

**SQLite**

Move to:

**PostgreSQL**

if the application becomes more complex.

The database should contain:

- companies
- sources
- extracted attributes
- screening results
- research results
- analyst decisions
- workflow events

## LLM

Use one commercial LLM API.

The goal is not to demonstrate every model provider.

Focus on:

- structured outputs
- tool calling
- prompt design
- error handling
- evaluation

## Frontend

React is already familiar from Cinematic Recall.

A simple dashboard is sufficient.

## Deployment

Deploy the application publicly using an inexpensive/free-tier platform where practical.

The goal is to demonstrate that the application works outside your laptop.

---

# 15. What You Should Learn From Building It

The project should deliberately force you to learn the technical areas missing from your current resume.

### Python

You should become comfortable with:

- functions
- classes
- type hints
- async/await
- requests/http clients
- JSON
- error handling
- environment variables
- pandas
- database access

### APIs

You should understand:

- REST
- authentication
- GET/POST/PATCH
- JSON payloads
- rate limits
- retries
- webhooks

### LLMs

You should understand:

- system prompts
- structured outputs
- tool calling
- context windows
- token usage
- hallucinations
- model selection
- evaluation

### Data pipelines

You should be able to explain:

```text
Raw data
→ validation
→ transformation
→ enrichment
→ storage
→ AI processing
→ output
```

### Production engineering

You should learn:

- Git
- deployment
- logging
- error handling
- monitoring
- secrets management
- basic authentication

---

# 16. Evaluation Strategy

A major goal should be avoiding the mistake:

> "The demo looked good, therefore the AI works."

Create a test dataset.

For example:

**50 companies with known characteristics.**

For each company, define expected outcomes for:

- industry classification
- revenue extraction
- growth extraction
- founder ownership
- investment fit
- missing data

Then measure:

### Extraction accuracy

How often did the AI correctly identify the underlying fact?

### Classification accuracy

How often did it correctly categorize the company?

### Screening accuracy

How often did its recommendation agree with the predefined test outcome?

### Citation accuracy

How often does the cited source actually support the claim?

### False-positive rate

How often does the system recommend companies that clearly should not pass the screen?

### False-negative rate

How often does it reject a company that should receive analyst attention?

This is a critical component of making the project feel like a real AI system rather than a demo.

---

# 17. Failure Modes

The application should explicitly handle cases where AI should not confidently answer.

Examples:

### Missing data

Instead of:

> "Revenue is $50M."

Return:

> "Revenue unavailable."

### Conflicting sources

Return:

> "Sources disagree. Manual review required."

### Low confidence

Return:

> "Insufficient evidence to assess founder ownership."

### Unreliable source

Flag the source for review.

### API failure

Retry, log the failure, and prevent corrupted data from entering the database.

---

# 18. Responsible AI / Compliance Design

The project should demonstrate awareness that an investment firm's data can be sensitive.

At minimum, implement or document:

- API keys stored as environment variables
- No secrets committed to GitHub
- Access controls
- Logging
- Source provenance
- Human approval for external communications
- No autonomous investment decisions
- No autonomous founder outreach
- Clear distinction between facts and AI inference
- Ability to delete or correct stored data

The project should also document what data **should not** be sent to an external LLM without appropriate authorization.

This demonstrates the mindset Volition is specifically asking for around compliance and responsible AI.

---

# 19. What Not to Build

Do not spend time building:

### A fake Salesforce clone

The project doesn't need:

- complex CRM screens
- contact management
- elaborate pipelines
- permissions systems
- calendar functionality

A simple database is enough.

### A generic RAG chatbot

Do not build:

> "Upload a PDF and ask questions."

That is now commodity functionality.

### An autonomous investment agent

Do not build:

> "AI decides whether Volition should invest."

The goal is analyst augmentation, not autonomous underwriting.

### A beautiful frontend

A functional interface is enough.

Your technical architecture and workflow matter more.

---

# 20. MVP Definition

The project is complete when a user can:

1. Add a company.
2. Trigger research.
3. Retrieve structured company information.
4. Run the investment screen.
5. Receive a transparent score.
6. See evidence supporting the score.
7. See missing information.
8. See recommended diligence questions.
9. Approve/reject the opportunity.
10. Generate a personalized outreach draft.
11. View the complete history of AI and human actions.

Anything beyond that is optional.

---

# 21. Stretch Goals

If the MVP works, add:

### Automated sourcing

Pull new companies from an external source on a schedule.

### Slack integration

Send:

> "3 new companies passed the initial screen."

### CRM integration

Use Airtable or another lightweight system as an external system of record.

### Agentic research

Allow an agent to decide which research tools it needs.

### Parallel research

Research multiple companies concurrently.

### Historical similarity

Compare new opportunities with previously evaluated companies.

### Portfolio monitoring

Extend the same architecture to portfolio-company KPI monitoring.

### Evaluation dashboard

Track AI performance over time.

---

# 22. Portfolio Project Narrative

The GitHub README should ultimately tell this story:

> **DealFlow AI is an AI-powered sourcing and diligence workflow designed to augment investment analysts at a growth-equity firm.**
>
> Rather than building another chatbot, the system automates the repetitive information-processing layer between company sourcing and human investment judgment.
>
> Companies are enriched from available data, evaluated against a configurable investment thesis, assigned transparent evidence-backed screening scores, and routed to analysts for human review. Approved opportunities can then receive deeper automated research and personalized outreach drafts.
>
> The system intentionally keeps humans in the loop for investment decisions and external communications, while maintaining source provenance and an audit trail of AI-generated recommendations.

---

# 23. What This Demonstrates to Volition

If executed well, the project gives you concrete evidence for nearly every technical requirement in the AI Specialist JD.

| Volition requirement | Project evidence |
|---|---|
| LLM expertise | LLM API + structured outputs |
| Agentic APIs | Tool-based research workflows |
| Production AI application | Deployed application |
| Internal AI tools | Investment workflow |
| Data pipelines / ETL | Company enrichment pipeline |
| CRM experience | Database/API integration |
| APIs | External data + internal endpoints |
| Python | Core application |
| Cloud | Deployment |
| AI governance | Human approval + provenance |
| Responsible AI | Guardrails + auditability |
| Workflow automation | Automated sourcing/research |
| RAG | Optional document research layer |
| Stakeholder translation | Analyst-oriented workflow design |

The most important thing is that you can **demonstrate the implementation**, not merely list these technologies on your resume.

---

# 24. The Interview Story

The strongest version of the project gives you a 2–3 minute story:

> "I wanted to understand where AI could actually create leverage inside a growth-equity investment process, so I modeled the sourcing and initial diligence workflow. I deliberately didn't build another chatbot because tools like ChatGPT with MCP already solve a lot of ad hoc document retrieval. Instead, I focused on persistent workflow automation: when a company enters the pipeline, the system enriches it, extracts structured data, evaluates it against a configurable thesis, provides evidence for each conclusion, identifies missing information, and routes it to an analyst for review.
>
> I built the backend in Python/FastAPI, integrated external APIs, used structured LLM outputs, stored the results in a database, deployed the application, and added human approval and auditability because I didn't think an AI system should autonomously make investment decisions or contact founders.
>
> The biggest thing I learned was that the hard part isn't calling an LLM. It's designing the system around the LLM—data quality, evaluation, failure modes, integrations, monitoring, and deciding where humans need to remain in the loop."

That is the **real thesis of the project**.

The technology is there to support the thesis—not the other way around.
