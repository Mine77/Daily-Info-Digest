# CLAUDE.md

Behavioral guidelines for AI agents working on the Daily Info Digest project. Adapted from Andrej Karpathy's guidelines and Matt Pocock's skill patterns.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**Context awareness:** Check `CONTEXT.md` before using domain terms. If a term conflicts with the glossary, call it out immediately.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add RSS source" → "Add source to config, verify RSS fetches correctly, confirm items appear in timeline"
- "Fix image display" → "Identify broken image URLs, fix fetching logic, verify images render in report"
- "Refactor app.py" → "Ensure reports generate correctly before and after refactor"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

## 5. Documentation Discipline

**Write ADRs for hard-to-reverse decisions. Update CONTEXT.md for new terms.**

When making architectural or design decisions:
- If it meets ADR criteria (hard to reverse, surprising, real trade-off), create an ADR in `docs/adr/`.
- If introducing new domain terminology, add it to `CONTEXT.md`.
- If the decision affects the roadmap, update `ROADMAP.md`.

Before creating an ADR, check if one already exists on the topic. If superseding an old ADR, mark it as deprecated.

## 6. Hermes Environment Awareness

**This project runs on a VPS with root privileges. Be cautious.**

- Never modify, restart, or bind to port 443 (Xray Reality VPN runs there).
- Use systemd for service management (`systemctl restart follow-builders-web`).
- GitHub repo is `Mine77/agent-workspace` — project lives under `Daily-Info-Digest/`.
- Reports are generated via `python3 app.py generate` in `web/` directory.
- Flask server runs on `127.0.0.1:25520`, proxied by nginx on `fb.x-nuwa.com:8445`.

## 7. Testing Before Committing

**Always verify before declaring done.**

- After code changes: generate a test report (`python3 app.py generate`).
- After template changes: view the HTML in browser or via screenshot.
- Before git push: review `git diff` to ensure only intended changes are included.
- After push: verify the service is running (`curl -s http://127.0.0.1:25520/`).

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, clarifying questions come before implementation rather than after mistakes, and ADRs accumulate naturally as the project evolves.
