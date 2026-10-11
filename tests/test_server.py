"""Runs the tools against the real OptMem CLI (downloaded once from a pinned commit)."""

import importlib
import urllib.request

import pytest

MEMO_URL = "https://raw.githubusercontent.com/VictorTaelin/OptMem/1fb164cf39028047781f72ac3bb1e5a691c1dcb0/memo"


@pytest.fixture(scope="session")
def memo_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("cli") / "memo"
    urllib.request.urlretrieve(MEMO_URL, path)
    return path


@pytest.fixture
def server(memo_path, tmp_path, monkeypatch):
    monkeypatch.setenv("OPTMEM_MEMO", str(memo_path))
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / "memory"))
    import optmem_mcp
    return importlib.reload(optmem_mcp)


def test_fresh_memory_is_initialised_and_points_at_tools(server):
    out = server.read_memory_context()
    assert "remember_fact" in out and "Record the first" not in out


def test_remember_search_compress_expand(server):
    server.remember_fact("User prefers Python")
    reply = server.remember_fact("User prefers free tools")
    assert 'summarize_memory_block(block_id="0-1"' in reply and "Run:" not in reply
    assert "saved" in server.summarize_memory_block("0-1", "Prefers Python and free tools")
    assert "free tools" in server.search_memories("(?i)FREE")
    assert "#0" in server.expand_memory_block("0-1")


@pytest.mark.parametrize("call", [
    lambda s: s.remember_fact("x" * 300),
    lambda s: s.search_memories("("),
    lambda s: s.expand_memory_block("5-9"),
])
def test_cli_errors_become_tool_errors(server, call):
    with pytest.raises(RuntimeError):
        call(server)


def test_missing_cli_explains_how_to_install(server, monkeypatch, tmp_path):
    monkeypatch.setattr(server, "MEMO", tmp_path / "nope")
    with pytest.raises(RuntimeError, match="install.sh"):
        server.read_memory_context()
