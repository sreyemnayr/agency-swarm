import os
import platform
import signal
import subprocess
import sys
import time

import pytest
from dotenv import load_dotenv

from agency_swarm.agency import Agency
from agency_swarm.agents.agent import Agent
from agency_swarm.tools.mcp import MCPServerSse, MCPServerStdio, MCPServerStreamableHttp

load_dotenv()

samples_dir = os.path.join(os.path.dirname(__file__), "data", "files")
sse_server_file = os.path.join(os.path.dirname(__file__), "scripts", "sse_server.py")
http_server_file = os.path.join(os.path.dirname(__file__), "scripts", "http_server.py")


@pytest.fixture(scope="module", autouse=True)
def start_server_sse():
    # Start the server as a subprocess
    print(f"Starting server from {sse_server_file}")
    process = subprocess.Popen([sys.executable, sse_server_file])
    time.sleep(5)  # Give it time to start
    yield
    # Try sending SIGINT (Ctrl+C) for a cleaner shutdown
    if platform.system() == "Windows":
        process.terminate()
    else:
        process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=10)  # Wait up to 10 seconds
    except subprocess.TimeoutExpired:
        print("Server did not terminate gracefully, sending SIGTERM")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Server did not terminate after SIGTERM, sending SIGKILL")
            process.kill()
            process.wait()


@pytest.fixture(scope="module", autouse=True)
def start_server_http():
    # Start the server as a subprocess
    print(f"Starting server from {http_server_file}")
    process = subprocess.Popen([sys.executable, http_server_file])
    time.sleep(5)  # Give it time to start
    yield
    # Try sending SIGINT (Ctrl+C) for a cleaner shutdown
    if platform.system() == "Windows":
        process.terminate()
    else:
        process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=10)  # Wait up to 10 seconds
    except subprocess.TimeoutExpired:
        print("Server did not terminate gracefully, sending SIGTERM")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Server did not terminate after SIGTERM, sending SIGKILL")
            process.kill()
            process.wait()


@pytest.fixture(scope="module")
def agency():
    filesystem_server = MCPServerStdio(
        name="Filesystem Server",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
        },
    )

    git_server = MCPServerStdio(
        name="Git Server",
        params={
            "command": "mcp-server-git",
        },
    )

    sse_server = MCPServerSse(
        name="SSE Python Server",
        params={"url": "http://localhost:8080/sse"},
        strict=True,
        allowed_tools=["get_secret_word"],
    )

    http_server = MCPServerStreamableHttp(
        name="HTTP Python Server",
        params={"url": "http://localhost:7860/mcp"},
        strict=True,
    )

    # Serialize agent initialization
    agents = []
    for name, server in [
        ("test1", filesystem_server),
        ("test2", git_server),
        ("test3", sse_server),
        ("test4", http_server),
    ]:
        agent = Agent(
            name=name,
            description="test",
            instructions="test",
            mcp_servers=[server],
            temperature=0,
        )
        agents.append(agent)

    return Agency(agents)


# Might take a bit to process
def test_read_filesystem(agency):
    result = agency.get_completion(
        f"Use the list_directory tool to read the contents of {samples_dir} folder.", recipient_agent=agency.agents[0]
    )
    print(result)
    assert "csv-test.csv" in result


def test_read_git_commit(agency):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = agency.get_completion(
        f"Read the last commit of the {root_dir} folder. Provide result in the exact same format as you receive it.",
        recipient_agent=agency.agents[1],
    )
    print(result)
    assert "Author" in result


def test_get_secret_word(agency):
    result = agency.get_completion("Get secret word using get_secret_word tool.", recipient_agent=agency.agents[2])
    print(result)
    assert "strawberry" in result.lower()


def test_get_secret_password(agency):
    result = agency.get_completion(
        "Get secret password using get_secret_password tool.", recipient_agent=agency.agents[3]
    )
    print(result)
    assert "hc1291cb7123" in result.lower()


if __name__ == "__main__":
    import pytest

    pytest.main(["-v", __file__])
