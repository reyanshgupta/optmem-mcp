# optmem-mcp

An [MCP](https://modelcontextprotocol.io) server for [OptMem](https://github.com/VictorTaelin/OptMem), Victor Taelin's permanent memory for AI agents.

OptMem keeps every memory as one line in an append-only log and builds a binary tree of one-line summaries over it. The summaries are written by the agent itself, when OptMem asks. The CLI is meant to be run from a shell. This server exposes the same commands as MCP tools, so agents without shell access can use it too: Claude Desktop, Cursor, LangGraph, the OpenAI Agents SDK, or anything else that speaks MCP.

## Install

1. Install OptMem itself (this server does not bundle it):
   ```sh
   curl -fsSL https://raw.githubusercontent.com/VictorTaelin/OptMem/main/install.sh | sh
   ```
2. Register the server with your client. With [uv](https://docs.astral.sh/uv/), nothing else is needed:

   **Claude Code**
   ```sh
   claude mcp add optmem -- uvx --from git+https://github.com/reyanshgupta/optmem-mcp optmem-mcp
   ```

   **Claude Desktop / Cursor** (`mcpServers` in the client's config)
   ```json
   {
     "mcpServers": {
       "optmem": {
         "command": "uvx",
         "args": ["--from", "git+https://github.com/reyanshgupta/optmem-mcp", "optmem-mcp"]
       }
     }
   }
   ```

   **LangGraph** (`langchain-mcp-adapters`)
   ```python
   client = MultiServerMCPClient({
       "optmem": {
           "transport": "stdio",
           "command": "uvx",
           "args": ["--from", "git+https://github.com/reyanshgupta/optmem-mcp", "optmem-mcp"],
           "env": {"MEMORY_DIR": "/data/memory"},
       }
   })
   ```

## Tools

| Tool | OptMem command | What it does |
|---|---|---|
| `read_memory_context()` | `memo wake` | Recent memories plus summaries of older ones. Call it first in every session. |
| `remember_fact(text)` | `memo note` | Record one line (≤ 280 bytes). May reply with a compression request. |
| `summarize_memory_block(block_id, summary)` | `memo nap` | Answer a compression request with a one-line summary. |
| `search_memories(pattern)` | `memo recall` | Regex search over every memory, word for word. |
| `expand_memory_block(block_id)` | `memo zoom` | Open a summary node into its two halves. |

The server also sends MCP `instructions` describing this protocol, so clients that surface them don't need a system-prompt change. `memo forget` isn't exposed. It only drops summaries, which the next compression rebuilds anyway.

What the wrapper changes in OptMem's output:
- An empty `MEMORY_DIR` is initialized on first use.
- OptMem ends its compression requests with `Run: memo nap 0-1 "<your line>"`. The server rewrites that line into a `summarize_memory_block` call, so the model reaches for the tool instead of a shell.
- When the CLI exits non-zero (bad regex, a line over 280 bytes, an unknown block), the tool returns an MCP error result carrying OptMem's message, so the model can correct itself.

## Configuration

| Variable | Default | |
|---|---|---|
| `MEMORY_DIR` | `~/.optmem/memory` | Where memories live. Same variable and default as the CLI, so the shell and MCP share one memory. |
| `OPTMEM_MEMO` | `~/.optmem/memo` | Path to the `memo` CLI. |

One server process serves one memory. To give several users or sessions their own memory, run one process per `MEMORY_DIR`. Alternatively, add a `session_id` argument that picks the directory, and have the host fill it in (for example with a `langchain-mcp-adapters` tool interceptor) rather than letting the model choose it.

## Development

```sh
uv venv && uv pip install -e ".[test]"
.venv/bin/pytest          # runs against the real OptMem CLI, downloaded from a pinned commit
npx @modelcontextprotocol/inspector .venv/bin/optmem-mcp   # poke at it by hand
```

## License

This wrapper is MIT-licensed. OptMem is Victor Taelin's work and is not included here. It is downloaded from its own repository, under its own terms.
