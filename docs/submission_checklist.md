# Submission Checklist

Verified on 2026-06-29.

- [x] `docker-compose build` completes successfully with the v2 fallback CLI (`docker compose` plugin is unavailable on this VM)
- [x] Dashboard opens at `http://localhost:8000`
- [x] Telegram demo endpoint responds to `/goal`, `/status`, `/storage`, `/review_pr`, `/approve`, and `/live_demo`
- [x] `/api/demo/live-demo` returns `live=true` with Fireworks routing metadata
- [x] Docker image smoke test passes on `127.0.0.1:8011` using the built image and project `.env`
- [x] `README.md` explains the problem, solution, architecture, AMD/Fireworks usage, setup, demo commands, and pitch
- [x] `docs/demo_script.md` is ready for recording
- [x] `docs/architecture.md` explains the system at a glance
- [x] `.env.example` contains placeholders only
- [x] No real secrets are committed; local `.env` remains untracked
- [x] Tests pass locally: `16 passed`
- [x] Container build works
- [x] Repository is safe to publish publicly
