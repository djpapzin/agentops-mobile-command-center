# Security

## Principles

- Keep secrets out of the repository.
- Use `.env.example` for placeholders only.
- Use demo or mock data by default.
- Do not connect the MVP to production OddsEdge/OpenClaw services without explicit approval.

## Recommended secret handling

- Copy `.env.example` to `.env` locally if you want to override defaults.
- Never commit `.env`, API keys, bot tokens, or private credentials.
- Rotate anything that was accidentally exposed.

## Public-release checks

Before publishing a release or submission:

- scan the repo for secret-looking strings
- verify `.gitignore` blocks local env files and SQLite data
- confirm no live support inboxes or production VMs are touched by the demo
- keep all workflow examples deterministic and safe to re-run
