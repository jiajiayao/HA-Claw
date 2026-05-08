from pathlib import Path


PANEL_JS = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "haclaw"
    / "frontend"
    / "haclaw-panel.js"
)


def test_chat_skeleton_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "this._messages = [];" in source
    assert "this._mode = this._restoreMode();" in source
    assert 'localStorage.getItem("haclaw.last_mode")' in source
    assert "this._conversationId = `conv_${Date.now()}_" in source
    assert 'id="chat-input"' in source
    assert 'id="send-btn"' in source
    assert "data-mode=" in source
    assert "HAclaw,你想让我做什么?" in source
    assert 'this._html`<div class="bubble user">${m.text}</div>`' in source


def test_chat_skeleton_has_expected_suggestion_chips():
    source = PANEL_JS.read_text(encoding="utf-8")

    for text in (
        "打开客厅灯",
        "生成晚 7 点开净化器的自动化",
        "当前模型连得通吗",
        "认领我的存在实体",
        "检查我的 HA 环境",
        "解释一下 automations.yaml 是什么",
    ):
        assert text in source


def test_chat_ws_final_response_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "async _sendChat(text)" in source
    assert 'type: "haclaw/chat"' in source
    assert "conversation_id: this._conversationId" in source
    assert "user_message: text" in source
    assert "mode: this._mode" in source
    assert 'this._messages.push({ kind: "thinking" });' in source
    assert (
        'this._messages.push({ kind: "assistant_msg", payload: result.assistant_message });'
        in source
    )
    assert 'this._messages.push({ kind: "error", text: err?.message || "请求失败" });' in source
    assert 'return `<div class="bubble assistant thinking">思考中...</div>`;' in source
    assert 'return this._html`<div class="bubble error">⚠️ ${m.text}</div>`;' in source
    assert 'if (payload?.type === "final_response")' in source
    assert 'text.replace(/^\\[BIND_PRESENCE\\]\\s*/, "")' in source
    assert ".bubble.thinking" in source
    assert ".bubble.error" in source
