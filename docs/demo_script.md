# 2-Minute Demo Script

## 0:00 - 0:15 — Open the dashboard

"This is AgentOps Mobile Command Center: a Telegram-first control room with a dashboard for mobile operators. The dashboard shows recent runs, approvals, storage health, and the live smoke-test button."

## 0:15 - 0:35 — Show the live demo path

1. Open the dashboard
2. Click **Live demo smoke test**
3. Show that `/api/demo/live-demo` returns `live=true`

## 0:35 - 1:05 — Show Telegram control

"From Telegram I can set a goal, check status, review a PR, inspect storage, and approve the next step without touching a laptop."

1. Send `/goal Ship the hackathon MVP`
2. Send `/status`
3. Send `/storage`
4. Send `/review_pr https://github.com/example/repo/pull/42`
5. Send `/approve`

## 1:05 - 1:35 — Explain the routing

"The router picks the cheapest capable model first, then escalates to Fireworks or AMD-hosted models when the task needs more accuracy. That keeps the workflow mobile-friendly and cost-aware."

## 1:35 - 2:00 — Close

"The result is a clean mobile ops console for founders who need control, visibility, and a live demo path they can show from a phone."
