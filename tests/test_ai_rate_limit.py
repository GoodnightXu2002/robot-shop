import pytest

import blueprints.ai as ai_blueprint


@pytest.fixture(autouse=True)
def reset_ai_rate_limiter(app):
    ai_blueprint.ai_rate_limiter._requests.clear()
    app.config.update(
        AI_RATE_LIMIT_WINDOW_SECONDS=60,
        AI_RATE_LIMIT_ANON_MAX=2,
        AI_RATE_LIMIT_USER_MAX=2,
    )
    yield
    ai_blueprint.ai_rate_limiter._requests.clear()


def login_regular_user(client):
    return client.post(
        "/login",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )


def login_admin(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "test-admin-password"},
        follow_redirects=False,
    )


def stub_ai_handler(monkeypatch):
    calls = {"count": 0}

    def fake_handle_ai_assistant_chat(payload):
        calls["count"] += 1
        return {"reply": "ok", "source": "test"}, 200

    monkeypatch.setattr(ai_blueprint, "handle_ai_assistant_chat", fake_handle_ai_assistant_chat)
    return calls


def post_ai(client, path="/api/ai-assistant/chat", remote_addr="127.0.0.1"):
    return client.post(
        path,
        json={"message": "推荐一款餐饮服务机器人"},
        environ_base={"REMOTE_ADDR": remote_addr},
    )


def test_ai_assistant_chat_allows_requests_within_limit(client, monkeypatch):
    calls = stub_ai_handler(monkeypatch)

    response = post_ai(client)

    assert response.status_code == 200
    assert response.get_json() == {"reply": "ok", "source": "test"}
    assert calls["count"] == 1


def test_ai_rate_limit_uses_test_config_override(app):
    assert app.config["AI_RATE_LIMIT_WINDOW_SECONDS"] == 60
    assert app.config["AI_RATE_LIMIT_ANON_MAX"] == 2
    assert app.config["AI_RATE_LIMIT_USER_MAX"] == 2


def test_ai_assistant_chat_returns_429_over_limit(client, monkeypatch):
    calls = stub_ai_handler(monkeypatch)

    assert post_ai(client).status_code == 200
    assert post_ai(client).status_code == 200
    response = post_ai(client)

    assert response.status_code == 429
    assert response.get_json() == {"error": "请求过于频繁，请稍后再试。"}
    assert calls["count"] == 2


def test_ai_rate_limit_follows_custom_config(client, app, monkeypatch):
    calls = stub_ai_handler(monkeypatch)
    app.config["AI_RATE_LIMIT_ANON_MAX"] = 1

    assert post_ai(client).status_code == 200
    response = post_ai(client)

    assert response.status_code == 429
    assert calls["count"] == 1


def test_ai_chat_alias_uses_same_rate_limit_rule(client, monkeypatch):
    calls = stub_ai_handler(monkeypatch)

    assert post_ai(client, "/api/ai-chat").status_code == 200
    assert post_ai(client, "/api/ai-chat").status_code == 200
    response = post_ai(client, "/api/ai-chat")

    assert response.status_code == 429
    assert response.get_json() == {"error": "请求过于频繁，请稍后再试。"}
    assert calls["count"] == 2


def test_ai_rate_limit_keys_are_independent_for_different_ips(client, monkeypatch):
    calls = stub_ai_handler(monkeypatch)

    assert post_ai(client, remote_addr="127.0.0.1").status_code == 200
    assert post_ai(client, remote_addr="127.0.0.1").status_code == 200
    assert post_ai(client, remote_addr="127.0.0.1").status_code == 429

    response = post_ai(client, remote_addr="10.0.0.2")

    assert response.status_code == 200
    assert calls["count"] == 3


def test_ai_rate_limit_keys_are_independent_for_different_users(client, monkeypatch):
    calls = stub_ai_handler(monkeypatch)

    login_regular_user(client)
    assert post_ai(client).status_code == 200
    assert post_ai(client).status_code == 200
    assert post_ai(client).status_code == 429

    client.get("/logout")
    login_admin(client)
    response = post_ai(client)

    assert response.status_code == 200
    assert calls["count"] == 3


def test_ai_rate_limit_does_not_call_handler_when_rejected(client, monkeypatch):
    calls = stub_ai_handler(monkeypatch)

    post_ai(client)
    post_ai(client)
    post_ai(client)

    assert calls["count"] == 2
