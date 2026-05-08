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
    assert 'if (event.key !== "Enter")' in source
    assert ".card {" in source
    assert ".cand-chips" in source
    assert ".cand-free-row" in source


def test_automation_draft_card_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'if (payload?.type === "automation_draft")' in source
    assert "_renderDraftCard(payload)" in source
    assert "payload.missing_integrations" in source
    assert "payload.rationale" in source
    assert 'class="card draft"' in source
    assert "btoa(unescape(encodeURIComponent(JSON.stringify(payload))))" in source
    assert "_renderRationaleField" in source
    assert 'this._mode === "automation"' in source
    assert "btn-install-prompt" in source
    assert '.btn-approve[data-card]' in source
    assert "async _onApproveDraft(cardEl)" in source
    assert '"create_automation_draft"' in source
    assert '"approve_automation_draft"' in source
    assert "confirmed: Boolean(payload.requires_confirmation)" in source
    assert 'action === "discard"' in source
    assert 'action === "edit"' in source
    assert "_toast(text)" in source
    assert ".card.draft .draft-head" in source
    assert ".draft-actions" in source


def test_risk_and_tool_call_rendering_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'if (payload?.type === "risk_confirmation")' in source
    assert "_renderRiskCard(payload)" in source
    assert 'if (payload?.type === "tool_call")' in source
    assert "_renderToolCallLine(payload)" in source
    assert "payload.planned_action" in source
    assert 'class="card risk risk-' in source
    assert "高风险操作" in source
    assert "工具执行层 v1.x 启用,本期不真执行" in source
    assert "确认执行" in source
    assert "本阶段不执行" in source
    assert "tool-call-line" in source
    assert ".card.risk" in source
    assert ".tool-call-line" in source


def test_env_check_card_and_install_modal_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'if (m.kind === "env_check")' in source
    assert "_renderEnvCheckCard(m.payload)" in source
    assert "state.advanced" in source
    assert 'class="card env-check"' in source
    assert "首次设置" in source
    assert "env-dismiss" in source
    assert "env-recheck" in source
    assert "async _refreshState()" in source
    assert "_dismissEnv()" in source
    assert 'localStorage.setItem("haclaw.env_dismissed", "1")' in source
    assert "_openInstallModal(domain)" in source
    assert "_findDraftMissingPrompt(domain)" in source
    assert 'textarea class="modal-body" readonly' in source
    assert 'overlay.querySelector(".modal-body").value = prompt.body || "";' in source
    assert "navigator.clipboard.writeText(text)" in source
    assert "黄底字段是占位符" in source
    assert ".card.env-check .env-head" in source
    assert ".modal-overlay" in source
    assert ".modal-body" in source


def test_presence_binding_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'if (text === "认领我的存在实体")' in source
    assert "_maybeInjectPresenceCard()" in source
    assert 'text.startsWith("[BIND_PRESENCE]")' in source
    assert "queueMicrotask(() => this._maybeInjectPresenceCard())" in source
    assert '"list_presence_candidates"' in source
    assert '"bind_presence_entity"' in source
    assert 'm.kind === "presence_bind"' in source
    assert 'm.kind === "presence_bind_empty"' in source
    assert 'm.kind === "presence_bind_done"' in source
    assert "_renderPresenceCard(m.candidates)" in source
    assert "只存 entity_id" in source
    assert "不会读取 MAC、手机号、GPS 坐标" in source
    assert '.cand-chip[data-presence]' in source
    assert "_bindPresence(presence.dataset.presence)" in source
    assert "this._presenceBound = true" in source
    assert ".card.presence .presence-list" in source
    assert ".card.presence.done" in source


def test_execute_mode_warning_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert 'if (mode === "execute")' in source
    assert 'localStorage.getItem("haclaw.execute_warning_seen") === "1"' in source
    assert "window.confirm(" in source
    assert "工具执行层 v1.x 启用,本模式现在仅展示模型会怎么提议工具调用,不会真正控制设备。" in source
    assert "继续切换吗?" in source
    assert "if (!ok) return;" in source
    assert 'localStorage.setItem("haclaw.execute_warning_seen", "1")' in source
    assert 'localStorage.setItem("haclaw.last_mode", mode)' in source


def test_settings_modal_and_history_drawer_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert "this._onDelegatedClick = (event) => this._handlePanelClick(event);" in source
    assert "this.addEventListener(\"click\", this._onDelegatedClick);" in source
    assert "_handlePanelClick(event)" in source
    assert 'this._closestPanelTarget(event, ".chip[data-chip]")' in source
    assert 'this._closestPanelTarget(event, ".mode-chip[data-mode]")' in source
    assert 'this._closestPanelTarget(event, "#send-btn")' in source
    assert 'this._closestPanelTarget(event, "#open-settings")' in source
    assert 'this._closestPanelTarget(event, "#open-drawer")' in source
    assert 'this._closestPanelTarget(event, "#open-model-settings")' in source
    assert 'this._closestPanelTarget(event, "#open-presence-bind")' in source
    assert 'this._closestPanelTarget(event, "#open-env-status")' in source
    assert 'this._closestPanelTarget(event, "[data-action]")' in source
    assert 'id="open-model-settings"' in source
    assert 'id="open-presence-bind"' in source
    assert 'id="open-env-status"' in source
    assert "模型:" in source
    assert "绑定存在" in source
    assert "环境" in source
    assert ">⚙ 设置</button>" in source
    assert ">☰ 历史</button>" in source
    assert "_openEnvironmentStatus()" in source
    assert "_openPresenceBinding()" in source
    assert "_openSettingsModal()" in source
    assert "当前模型:" in source
    assert 'id="new-model"' in source
    assert 'id="apply-model"' in source
    assert '"switch_model"' in source
    assert "模型已切换" in source
    assert 'id="recheck-env"' in source
    assert 'id="rebind-presence"' in source
    assert 'id="clear-current"' in source
    assert 'id="clear-all"' in source
    assert '"haclaw/conversations/clear"' in source
    assert "async _openDrawer()" in source
    assert "对话历史" in source
    assert '"haclaw/conversations/list"' in source
    assert 'id="new-chat"' in source
    assert "暂无历史" in source
    assert ".modal-section" in source
    assert ".modal.drawer-panel" in source
    assert ".drawer-row" in source


def test_mobile_breakpoint_contract_is_present():
    source = PANEL_JS.read_text(encoding="utf-8")

    assert source.count("@media (max-width: 640px)") == 1
    mobile = source.split("@media (max-width: 640px)", maxsplit=1)[1]
    assert ".topbar .left" in mobile
    assert "font-size: 13px" in mobile
    assert ".topbar .right" in mobile
    assert ".top-action" in mobile
    assert "min-height: 36px" in mobile
    assert ".topbar .right .icon-btn:nth-child(3)" not in mobile
    assert ".empty h2" in mobile
    assert "font-size: 22px" in mobile
    assert ".empty .chips" in mobile
    assert "flex-direction: column" in mobile
    assert ".modes" in mobile
    assert "flex-wrap: wrap" in mobile
    assert ".draft-actions" in mobile
    assert ".bubble" in mobile
    assert "max-width: 90%" in mobile
    assert ".cand-chips" in mobile
    assert ".cand-chip" in mobile
    assert "width: 100%" in mobile
    assert ".modal.drawer-panel" in mobile
    assert "max-width: 100%" in mobile
