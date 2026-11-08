from mistral_desktop.main import main
from mistral_desktop.models import Agent, new_id


def test_list_agents_seeds_defaults(tmp_path, capsys):
    rc = main(["--data-dir", str(tmp_path / "d"), "--list-agents"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "mistral-large-latest" in out
    assert "mistral-small-latest" in out


def test_cli_chat_against_mock_server(tmp_path, capsys, mock_server, settings):
    from mistral_desktop.store import Store

    store = Store(tmp_path / "d")
    agent = Agent(id=new_id(), name="mock-agent", provider="openai_compatible",
                  model="m", base_url=mock_server, api_key="secret")
    store.save_agent(agent)
    rc = main(["--data-dir", str(tmp_path / "d"), "--cli", "hello there", "--agent", agent.id])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Hello, world" in out
    conv = store.load_conversation(agent.id)
    assert [m.role for m in conv.messages] == ["user", "assistant"]
    assert conv.messages[-1].content == "Hello, world"


def test_cli_unknown_agent_errors(tmp_path, capsys):
    rc = main(["--data-dir", str(tmp_path / "d"), "--cli", "hi", "--agent", "nope"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "No agent matching" in err
