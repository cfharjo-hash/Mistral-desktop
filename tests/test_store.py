import os
import stat

from mistral_desktop.config import Settings
from mistral_desktop.models import Agent, Conversation, Message, new_id


def _agent(**kw):
    base = dict(id=new_id(), name="Test", provider="mistral", model="mistral-large-latest")
    base.update(kw)
    return Agent(**base)


def test_agent_crud_roundtrip(store):
    a = _agent(system_prompt="be nice", color="#fff")
    store.save_agent(a)
    assert [x.id for x in store.list_agents()] == [a.id]
    loaded = store.get_agent(a.id)
    assert loaded.name == "Test"
    assert loaded.system_prompt == "be nice"
    assert loaded.color == "#fff"


def test_save_agent_upserts(store):
    a = _agent(name="v1")
    store.save_agent(a)
    a.name = "v2"
    store.save_agent(a)
    agents = store.list_agents()
    assert len(agents) == 1
    assert agents[0].name == "v2"


def test_find_agent_by_name(store):
    a = _agent(name="My Qwen Agent")
    store.save_agent(a)
    assert store.find_agent(a.id).id == a.id
    assert store.find_agent("qwen").id == a.id
    assert store.find_agent("nope") is None


def test_delete_agent_removes_conversation(store):
    a = _agent()
    store.save_agent(a)
    conv = Conversation(agent_id=a.id, messages=[Message(role="user", content="hi")])
    store.save_conversation(conv)
    assert (store.conv_dir / f"{a.id}.json").exists()
    assert store.delete_agent(a.id) is True
    assert store.list_agents() == []
    assert not (store.conv_dir / f"{a.id}.json").exists()
    assert store.delete_agent(a.id) is False


def test_conversation_roundtrip(store):
    conv = Conversation(agent_id="x", messages=[Message(role="user", content="hello"),
                                               Message(role="assistant", content="hi there")])
    store.save_conversation(conv)
    loaded = store.load_conversation("x")
    assert [m.role for m in loaded.messages] == ["user", "assistant"]
    assert loaded.messages[1].content == "hi there"


def test_load_empty_conversation(store):
    conv = store.load_conversation("missing")
    assert conv.agent_id == "missing"
    assert conv.messages == []


def test_settings_roundtrip_and_permissions(store):
    s = Settings(mistral_api_key="k", hf_token="h", appearance="Dark", last_agent_id="abc")
    store.save_settings(s)
    loaded = store.load_settings()
    assert loaded.mistral_api_key == "k"
    assert loaded.appearance == "Dark"
    mode = stat.S_IMODE((store.data_dir / "settings.json").stat().st_mode)
    assert mode == 0o600


def test_agents_file_is_private(store):
    store.save_agent(_agent())
    mode = stat.S_IMODE((store.data_dir / "agents.json").stat().st_mode)
    assert mode == 0o600


def test_settings_from_dict_ignores_unknown_keys():
    s = Settings.from_dict({"appearance": "Light", "bogus": 1})
    assert s.appearance == "Light"
