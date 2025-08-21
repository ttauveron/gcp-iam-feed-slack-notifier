from config import Config
from tests.conftest import load_fixture, import_main_with_stubs, FakeEvent


def test_routes_asset(monkeypatch, load_fixture):
    m = import_main_with_stubs(monkeypatch)

    called = {"feeds": 0, "audits": 0}
    monkeypatch.setattr(
        m, "process_feeds",
        lambda msg, token, channel: called.__setitem__("feeds", 1)
    )
    monkeypatch.setattr(
        m, "process_audit_logs",
        lambda msg, token, channel: called.__setitem__("audits", 1)
    )

    # Replace the whole cfg with a dummy one
    monkeypatch.setattr(m, "cfg", Config(slack_token="dummy", slack_channel="#chan", log_level=20))

    payload = load_fixture("asset_project.json")

    m.hello_pubsub(FakeEvent(payload))
    assert called["feeds"] == 1
    assert called["audits"] == 0


def test_routes_audit(monkeypatch, load_fixture):
    m = import_main_with_stubs(monkeypatch)

    called = {"feeds": 0, "audits": 0}
    monkeypatch.setattr(
        m, "process_feeds",
        lambda msg, token, channel: called.__setitem__("feeds", 1)
    )
    monkeypatch.setattr(
        m, "process_audit_logs",
        lambda msg, token, channel: called.__setitem__("audits", 1)
    )

    # Replace the whole cfg with a dummy one
    monkeypatch.setattr(m, "cfg", Config(slack_token="dummy", slack_channel="#chan", log_level=20))

    payload = load_fixture("audit_bucket_iam_add.json")

    m.hello_pubsub(FakeEvent(payload))
    assert called["feeds"] == 0
    assert called["audits"] == 1
