"""MCP server: drive the factory from Claude (or any MCP client) over stdio.

It is a thin client of the local engine (`factory serve`, started on demand), so the app and an agent share one job
queue. Replies are short text built for an agent's context: one line per episode or job, image prompts and frame
files left out unless asked, and waiting happens inside the engine (long-poll) instead of in polling loops."""
