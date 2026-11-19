---
name: joystream-ai-lite
description: Analyze Twitch stream CSV/JSON exports and summarize channel performance offline.
---

# JoyStream-AI Lite

Use this skill when a user supplies a CSV or JSON export of Twitch stream metrics and requests a performance review. Do not claim access to live Twitch analytics.

## Procedure
1. Ask for a CSV or JSON file if none was provided. Never request API keys or passwords.
2. Run `python scripts/analyze.py INPUT_PATH` from this skill directory. Python 3.9+; standard library only.
3. Explain the results, distinguishing observed metrics from hypotheses. Never fabricate missing metrics.
4. Read `references/data-format.md` for supported columns and privacy notes.
