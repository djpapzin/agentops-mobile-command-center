# Architecture

## Overview

The app is intentionally small:

1. **Telegram command entry** becomes a normalized command object.
2. **Router** decides whether the task should use a local/cheap model, Fireworks, or AMD-hosted compute.
3. **Workflow engine** produces a deterministic demo result.
4. **Run logger** writes the decision and outcome to SQLite.
5. **Dashboard** reads the same SQLite data and shows the latest state.

## Components

| Component | Responsibility |
|---|---|
| `app.main` | FastAPI app, HTTP routes, dashboard, and Telegram demo endpoint |
| `app.demo` | Command parsing and mock workflows |
| `app.router` | Model selection and cost/token estimation |
| `app.db` | SQLite schema + persistence |
| `app/templates/index.html` | Mobile-friendly dashboard |

## Decision routing

Routing is based on:

- task type
- expected cost
- confidence
- required accuracy

### Typical outcomes

- **Local/small model**: storage checks, status summaries, low-risk formatting tasks
- **Fireworks model**: triage, summarization, broad synthesis, cost-sensitive reasoning
- **AMD-hosted model**: code-review style tasks and higher-accuracy decision cards

## Demo workflows

- **PR review summary**: mock PR metadata is summarized into a decision card
- **VM storage health check**: local disk metrics are converted into a status card
- **Email triage**: demo inbox items are ranked by urgency and actionability
- **Safe-to-merge**: checks are combined into a final approval recommendation

## Data model

SQLite tables:

- `runs` — every agent run with route metadata
- `approvals` — pending and resolved decision cards
- `state` — current goal and latest review context

## Deployment

The app runs with one container and one SQLite data volume.
That keeps the hackathon submission portable and easy to review.
