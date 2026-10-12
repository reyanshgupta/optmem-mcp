"""optmem-mcp: an MCP server for OptMem (https://github.com/VictorTaelin/OptMem).

OptMem is an append-only memory for AI agents: one line per memory, plus a binary tree of one-line
summaries that the agent itself writes when OptMem asks for them. This server exposes the `memo` CLI as
MCP tools, so any MCP client can use it without shell access.

The CLI is not bundled. Install it with OptMem's own installer (it lands in ~/.optmem/memo), or point
OPTMEM_MEMO at a copy. Memories live in $MEMORY_DIR, else ~/.optmem/memory, exactly as with the CLI.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

MEMO = Path(os.getenv("OPTMEM_MEMO") or Path.home() / ".optmem" / "memo")
MEMORY_DIR = Path(os.getenv("MEMORY_DIR") or Path.home() / ".optmem" / "memory")
INSTALL = "curl -fsSL https://raw.githubusercontent.com/VictorTaelin/OptMem/main/install.sh | sh"

# The CLI's output tells the agent which shell command to run next; point it at the tools instead.
NAP_COMMAND = re.compile(r'^Run: .* nap (\S+) "<your line>"$', re.MULTILINE)
NOTE_HINT = re.compile(r"Record the first with: .*")
AWAKE = re.compile(r"^You are awake\.\n?", re.MULTILINE)  # CLI ritual line; models mistake it for a memory

mcp = FastMCP(
    "optmem",
    instructions=(
        "OptMem is your long-term memory. Call read_memory_context at the start of a session. "
        "Call remember_fact whenever you learn something worth keeping: a preference, a decision, a fact about "
        "the user, the outcome of real work. Do not store duplicates. When a tool reply asks you to compress "
        "memories, call summarize_memory_block before doing anything else. Use search_memories for exact "
        "lookups and expand_memory_block to open a summary into its two halves."
    ),
)


def _memo(*args: str) -> str:
    """Run `memo <args>` and return its output; raise (an MCP isError result) when the CLI fails."""
    if not MEMO.is_file():
        raise RuntimeError(f"OptMem CLI not found at {MEMO}. Install it with: {INSTALL}  (or set OPTMEM_MEMO)")
    env = {**os.environ, "MEMORY_DIR": str(MEMORY_DIR)}

    def run(*cli_args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(MEMO), *cli_args], env=env, capture_output=True, text=True, timeout=30)

    if not (MEMORY_DIR / "LOG.txt").exists():
        run("init")
    result = run(*args)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(output)
    output = AWAKE.sub("", output).strip()
    output = NOTE_HINT.sub("Store one with remember_fact.", output)
    return NAP_COMMAND.sub(r'Do it now: call summarize_memory_block(block_id="\1", summary="<your line>").', output)


@mcp.tool()
def read_memory_context() -> str:
    """Read the memory: recent memories verbatim plus summaries of older ones. Call it first, every session."""
    return _memo("wake")


@mcp.tool()
def remember_fact(text: str) -> str:
    """Record one memory: a single line, at most 280 bytes. If the reply asks for a compression, do it now."""
    return _memo("note", text)


@mcp.tool()
def search_memories(pattern: str) -> str:
    """Search every memory ever recorded, word for word, with a Python regex (prefix (?i) to ignore case)."""
    return _memo("recall", pattern)


@mcp.tool()
def expand_memory_block(block_id: str) -> str:
    """Open a summary node such as "0-3" into its two halves, down to the raw memories."""
    return _memo("zoom", block_id)


@mcp.tool()
def summarize_memory_block(block_id: str, summary: str) -> str:
    """Answer a compression request: one line (max 280 bytes) summarizing block_id. Keep what has lasting
    effect, drop what does not, invent nothing."""
    return _memo("nap", block_id, summary)


def main() -> None:
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
