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
