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


def test_clarification_card_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'if (payload?.type === "clarification")' in source
    assert "_renderClarificationCard(payload)" in source
    assert "payload.allow_free_text" in source
    assert 'payload.free_text_placeholder || "或者直接输入..."' in source
    assert 'class="card clarification"' in source
    assert 'class="cand-chip"' in source
    assert 'class="cand-free-input"' in source
    assert 'class="cand-free-send"' in source
    assert '.cand-chip[data-label]' in source
    assert "this._appendUserMessage(label);" in source
    assert "this._sendChat(label);" in source
    assert '.cand-free-send[data-card]' in source
    assert "this._sendChat(text);" in source
    assert 'if (event.key === "Enter")' in source
    assert ".card {" in source
    assert ".cand-chips" in source
    assert ".cand-free-row" in source
