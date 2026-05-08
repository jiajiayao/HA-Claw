class HAclawPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = undefined;
    this._messages = [];
    this._mode = this._restoreMode();
    this._modelName = "";
    this._providerOk = false;
    this._envFailingCount = 0;
    this._presenceBound = false;
    this._envCardShown = false;
    this._envState = null;
    this._busy = false;
    this._conversationId = `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    this._suggestionChips = [
      "打开客厅灯",
      "生成晚 7 点开净化器的自动化",
      "当前模型连得通吗",
      "认领我的存在实体",
      "检查我的 HA 环境",
      "解释一下 automations.yaml 是什么",
    ];
  }

  set hass(hass) {
    this._hass = hass;
    this._readModelFromHass();
    this._render();
  }

  connectedCallback() {
    this._render();
    this._refreshState();
  }

  _restoreMode() {
    try {
      const value = localStorage.getItem("haclaw.last_mode");
      if (["plan", "automation", "execute"].includes(value)) {
        return value;
      }
    } catch (_err) {
      // Ignore storage failures in embedded HA contexts.
    }
    return "automation";
  }

  _readModelFromHass() {
    if (!this._hass) {
      return;
    }
    const entries = Object.values(this._hass.config?.entries || {}).filter(
      (entry) => entry.domain === "haclaw",
    );
    const options = entries[0]?.options || entries[0]?.data || {};
    this._modelName = options.model || "";
  }

  async _refreshState() {
    if (!this._hass) {
      return;
    }
    const dismissedLocal = (() => {
      try {
        return localStorage.getItem("haclaw.env_dismissed") === "1";
      } catch (_err) {
        return false;
      }
    })();

    try {
      const result = await this._callService("get_environment_readiness", {});
      if (result) {
        this._envState = result;
        if (dismissedLocal) {
          result.dismissed = true;
        }
        this._providerOk = result.items?.[0]?.ok ?? false;
        this._envFailingCount = result.failing_required_count ?? 0;
        if (!result.dismissed && this._envFailingCount > 0 && !this._envCardShown) {
          this._messages.unshift({ kind: "env_check", payload: result });
          this._envCardShown = true;
        }
      }
    } catch (_err) {
      // Environment status is advisory; keep the panel usable if it fails.
    }

    try {
      const presence = await this._callService("get_presence_binding", {});
      this._presenceBound = Boolean(presence?.me_person_entity_id);
    } catch (_err) {
      this._presenceBound = false;
    }

    this._render();
  }

  async _callService(service, data) {
    const result = await this._hass.connection.sendMessagePromise({
      type: "call_service",
      domain: "haclaw",
      service,
      service_data: data,
      return_response: true,
    });
    return result?.response;
  }

  _onSend() {
    const input = this.querySelector("#chat-input");
    if (!input) {
      return;
    }
    const text = input.value.trim();
    if (!text || this._busy) {
      return;
    }
    input.value = "";
    this._appendUserMessage(text);
    this._sendChat(text);
  }

  _appendUserMessage(text) {
    this._messages.push({ kind: "user_text", text });
    this._render();
  }

  async _sendChat(text) {
    this._busy = true;
    this._messages.push({ kind: "thinking" });
    this._render();
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "haclaw/chat",
        conversation_id: this._conversationId,
        user_message: text,
        mode: this._mode,
      });
      this._messages.pop();
      this._messages.push({ kind: "assistant_msg", payload: result.assistant_message });
    } catch (err) {
      this._messages.pop();
      this._messages.push({ kind: "error", text: err?.message || "请求失败" });
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _onChipClick(text) {
    this._appendUserMessage(text);
  }

  _switchMode(mode) {
    this._mode = mode;
    try {
      localStorage.setItem("haclaw.last_mode", mode);
    } catch (_err) {
      // Ignore storage failures in embedded HA contexts.
    }
    this._render();
  }

  _html(strings, ...values) {
    let out = strings[0];
    for (let i = 0; i < values.length; i += 1) {
      out += this._escape(values[i]) + strings[i + 1];
    }
    return out;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  _modeLabel(mode) {
    return (
      {
        plan: "📋 计划",
        automation: "⚡ 自动化",
        execute: "🛠 执行 ⚠️",
      }[mode] || mode
    );
  }

  _renderMessage(m) {
    if (m.kind === "user_text") {
      return this._html`<div class="bubble user">${m.text}</div>`;
    }
    if (m.kind === "env_check") {
      return this._renderEnvCheckCard(m.payload);
    }
    if (m.kind === "thinking") {
      return `<div class="bubble assistant thinking">思考中...</div>`;
    }
    if (m.kind === "error") {
      return this._html`<div class="bubble error">⚠️ ${m.text}</div>`;
    }
    if (m.kind === "assistant_msg") {
      return this._renderAssistant(m.payload);
    }
    return "";
  }

  _renderAssistant(payload) {
    if (payload?.type === "final_response") {
      return this._renderFinalResponseBubble(payload);
    }
    if (payload?.type === "automation_draft") {
      return this._renderDraftCard(payload);
    }
    if (payload?.type === "risk_confirmation") {
      return this._renderRiskCard(payload);
    }
    if (payload?.type === "tool_call") {
      return this._renderToolCallLine(payload);
    }
    if (payload?.type === "clarification") {
      return this._renderClarificationCard(payload);
    }
    return this._html`<div class="bubble assistant">${JSON.stringify(payload)}</div>`;
  }

  _renderFinalResponseBubble(payload) {
    const text = payload.message || "";
    const display = text.replace(/^\[BIND_PRESENCE\]\s*/, "");
    return this._html`<div class="bubble assistant">${display}</div>`;
  }

  _renderClarificationCard(payload) {
    const cands = Array.isArray(payload.candidates) ? payload.candidates : [];
    const allowFree = Boolean(payload.allow_free_text);
    const placeholder = payload.free_text_placeholder || "或者直接输入...";
    const cardId = `clar_${this._messages.length}`;

    const chipsHTML = cands
      .map((candidate) =>
        this._html`<button class="cand-chip" data-card="${cardId}" data-label="${candidate.label || ""}">
          <span class="cand-label">${candidate.label || ""}</span>
          ${
            candidate.subtitle
              ? this._html`<span class="cand-sub">${candidate.subtitle}</span>`
              : ""
          }
        </button>`,
      )
      .join("");

    const freeHTML = allowFree
      ? this._html`
        <div class="cand-free">
          <span class="cand-free-hint">或者自定义:</span>
          <div class="cand-free-row">
            <input type="text" class="cand-free-input" data-card="${cardId}" placeholder="${placeholder}" />
            <button class="cand-free-send" data-card="${cardId}">发送</button>
          </div>
        </div>
      `
      : "";

    return `<div class="card clarification" data-card-id="${this._escape(cardId)}">
      <div class="card-msg">${this._escape(payload.message || "")}</div>
      <div class="cand-chips">${chipsHTML}</div>
      ${freeHTML}
    </div>`;
  }

  _renderRiskCard(payload) {
    const planned = payload.planned_action
      ? JSON.stringify(payload.planned_action, null, 2)
      : "";
    const risk = payload.risk_level || "high";
    const detailsHTML = planned
      ? `<details><summary>计划动作</summary><pre>${this._escape(planned)}</pre></details>`
      : "";
    return `<div class="card risk risk-${this._escape(risk)}">
      <div class="risk-head">⚠️ 高风险操作 · ${this._escape(risk)}</div>
      <div class="risk-msg">${this._escape(payload.message || "")}</div>
      ${detailsHTML}
      <div class="draft-actions">
        <button class="btn-primary" disabled title="工具执行层 v1.x 启用,本期不真执行">确认执行</button>
        <button class="btn-secondary">取消</button>
      </div>
    </div>`;
  }

  _renderToolCallLine(payload) {
    const tool = payload.tool || "?";
    return this._html`<div class="tool-call-line">↪ 模型尝试调用 <code>${tool}</code>(本阶段不执行)</div>`;
  }

  _renderEnvCheckCard(state) {
    const items = [...(state.items || []), ...(state.advanced || [])];
    const rowsHTML = items
      .map((item) => {
        const linksHTML = (item.links || [])
          .map((link) => this._html`<a href="${link.url}" target="_blank">${link.text}</a>`)
          .join(" · ");
        const installBtn = item.install_prompt
          ? this._html`<button class="btn-install-prompt" data-domain="${item.id}">📋 安装指令</button>`
          : "";
        const hint =
          !item.ok && item.hint
            ? this._html`<span class="env-hint">${item.hint}</span>`
            : "";
        return `<div class="env-row ${item.ok ? "ok" : "fail"}">
          <span class="env-status">${item.ok ? "✅" : "⚠️"}</span>
          <span class="env-label">${this._escape(item.label || "")}</span>
          ${hint}
          <span class="env-actions">${linksHTML} ${installBtn}</span>
        </div>`;
      })
      .join("");

    return `<div class="card env-check">
      <div class="env-head">🛠 首次设置 · 我建议先检查这些</div>
      ${rowsHTML}
      <div class="env-foot">
        <button class="btn-secondary" data-action="env-dismiss">全部跳过,以后再说</button>
        <button class="btn-secondary" data-action="env-recheck">重新检查</button>
      </div>
    </div>`;
  }

  _renderDraftCard(payload) {
    const cardId = `draft_${this._messages.length}`;
    const requires = Boolean(payload.requires_confirmation);
    const missing = Array.isArray(payload.missing_integrations)
      ? payload.missing_integrations
      : [];
    const hasRationale = payload.rationale && typeof payload.rationale === "object";
    const yaml = JSON.stringify(payload.automation || {}, null, 2);
    const title = payload.title || payload.automation?.alias || "未命名草稿";
    const risk = payload.risk_level || "low";
    const approveLabel = requires ? "审批并确认风险" : "审批写入";
    const cached = btoa(unescape(encodeURIComponent(JSON.stringify(payload))));

    const missingHTML = missing
      .map(
        (item) => `
          <div class="warn-row">
            ⚠️ 草稿用到 <code>${this._escape(item.service || "")}</code>,但 ${this._escape(item.integration_name || "")} 未检测到。
            ${
              item.install_link
                ? this._html`<a href="${item.install_link}" target="_blank">官方指引</a>`
                : ""
            }
            ${
              item.install_prompt
                ? this._html`<button class="btn-install-prompt" data-card="${cardId}" data-domain="${item.domain || ""}">📋 安装指令</button>`
                : ""
            }
          </div>
        `,
      )
      .join("");

    const rationaleHTML = !hasRationale
      ? `
        <div class="warn-box small">⚠️ 模型未提供设计依据(rationale),无法审计这个草稿是怎么推演出来的;建议丢弃后再试一次。</div>
      `
      : `
        <div class="rationale">
          <div class="rationale-title">设计依据(从对话推演)</div>
          <div class="rationale-row"><b>实体:</b> ${this._renderRationaleField(payload.rationale.entities)}</div>
          <div class="rationale-row"><b>触发:</b> ${this._renderRationaleField(payload.rationale.trigger)}</div>
          <div class="rationale-row"><b>条件:</b> ${this._renderRationaleField(payload.rationale.conditions)}</div>
          <div class="rationale-row"><b>动作:</b> ${this._renderRationaleField(payload.rationale.actions)}</div>
          <div class="rationale-row"><b>边缘情况:</b> ${this._renderRationaleField(payload.rationale.edge_cases)}</div>
        </div>
      `;

    const approveDisabled = !hasRationale || missing.length > 0 ? "disabled" : "";
    const approveTitle = approveDisabled ? "先解决警告(rationale 或缺集成)再审批" : "";
    const inAutomationMode = this._mode === "automation";
    const planHint = !inAutomationMode ? "(切到自动化模式后才能审批写入)" : "";

    return `<div class="card draft" data-card-id="${this._escape(cardId)}" data-payload="${this._escape(cached)}">
      <div class="draft-head">
        <span class="draft-title">${this._escape(title)}</span>
        <span class="draft-risk risk-${this._escape(risk)}">${this._escape(risk)}</span>
      </div>
      ${missing.length > 0 ? `<div class="warn-box">${missingHTML}</div>` : ""}
      ${rationaleHTML}
      <details class="draft-yaml"><summary>查看 YAML</summary><pre>${this._escape(yaml)}</pre></details>
      <div class="draft-actions">
        <button class="btn-primary btn-approve" data-card="${this._escape(cardId)}" ${approveDisabled} ${
          approveTitle ? `title="${this._escape(approveTitle)}"` : ""
        } ${!inAutomationMode ? "disabled" : ""}>
          ${this._escape(approveLabel)} ${this._escape(planHint)}
        </button>
        <button class="btn-secondary" data-card="${this._escape(cardId)}" data-action="discard">丢弃</button>
        <button class="btn-secondary" data-card="${this._escape(cardId)}" data-action="edit">修改后再说</button>
      </div>
    </div>`;
  }

  _renderRationaleField(value) {
    if (Array.isArray(value)) {
      return value.length === 0
        ? '<span class="muted">无</span>'
        : value.map((item) => this._escape(String(item))).join("、");
    }
    return this._escape(String(value ?? "无"));
  }

  async _onApproveDraft(cardEl) {
    if (!cardEl) {
      return;
    }

    let payload;
    try {
      payload = JSON.parse(decodeURIComponent(escape(atob(cardEl.dataset.payload))));
    } catch (_err) {
      this._toast("草稿数据无效");
      return;
    }

    let draftId;
    try {
      const created = await this._callService("create_automation_draft", {
        title: payload.title || payload.automation?.alias || "草稿",
        description: payload.description || "",
        automation: payload.automation,
        source: "panel",
      });
      if (!created?.success) {
        this._toast(created?.message || "创建草稿失败");
        return;
      }
      draftId = created.draft.id;
    } catch (err) {
      this._toast(err?.message || "创建草稿失败");
      return;
    }

    try {
      const approved = await this._callService("approve_automation_draft", {
        draft_id: draftId,
        confirmed: Boolean(payload.requires_confirmation),
      });
      if (!approved?.success) {
        this._toast(approved?.message || "审批失败");
        return;
      }
      this._toast(approved.message || "已写入");
      const actions = cardEl.querySelector(".draft-actions");
      if (actions) {
        actions.innerHTML = '<span class="muted">已审批写入</span>';
      }
    } catch (err) {
      this._toast(err?.message || "审批失败");
    }
  }

  _toast(text) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = text;
    this.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
  }

  _dismissEnv() {
    try {
      localStorage.setItem("haclaw.env_dismissed", "1");
    } catch (_err) {
      // Ignore storage failures in embedded HA contexts.
    }
    this._messages = this._messages.filter((message) => message.kind !== "env_check");
    this._render();
  }

  _openInstallModal(domain) {
    const items = [
      ...(this._envState?.items || []),
      ...(this._envState?.advanced || []),
    ];
    let prompt = items.find((item) => item.id === domain)?.install_prompt || null;
    if (!prompt) {
      prompt = this._findDraftMissingPrompt(domain);
    }
    if (!prompt) {
      return;
    }

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-head">
          <span>${this._escape(`安装指令 — ${prompt.title || ""}`)}</span>
          <button class="modal-close">✕</button>
        </div>
        <div class="modal-info">粘贴到 Claude Code / Codex / 其他 AI agent。⚠️ 黄底字段是占位符,在你的 AI agent 那边亲自填,不要在这里改。</div>
        <textarea class="modal-body" readonly></textarea>
        <div class="modal-foot">
          <button class="btn-primary modal-copy">📋 复制</button>
          <button class="btn-secondary modal-close">关闭</button>
        </div>
      </div>
    `;
    overlay.querySelector(".modal-body").value = prompt.body || "";
    document.body.appendChild(overlay);

    overlay.querySelectorAll(".modal-close").forEach((button) => {
      button.addEventListener("click", () => overlay.remove());
    });
    overlay.querySelector(".modal-copy")?.addEventListener("click", async () => {
      const text = overlay.querySelector(".modal-body").value;
      try {
        await navigator.clipboard.writeText(text);
        this._toast("已复制 · 粘贴到你的 AI agent · 黄底占位符在那边亲自填");
      } catch (_err) {
        this._toast("复制失败,请手动复制");
      }
    });
  }

  _findDraftMissingPrompt(domain) {
    for (const message of this._messages) {
      if (message.kind !== "assistant_msg") {
        continue;
      }
      const missing = message.payload?.missing_integrations || [];
      const found = missing.find((item) => item.domain === domain);
      if (found?.install_prompt) {
        return found.install_prompt;
      }
    }
    return null;
  }

  _render() {
    if (!this.isConnected) {
      return;
    }

    const status = `${this._modelName || "未配置"} · ${
      this._providerOk ? "✅" : "❌"
    }`;
    const failingBadge =
      this._envFailingCount > 0
        ? this._html`<span class="badge warn">⚠️${String(this._envFailingCount)}</span>`
        : "";
    const presenceHint = this._presenceBound
      ? ""
      : '<span class="badge hint">💡未绑存在</span>';

    const isEmpty = this._messages.length === 0;
    const greetingHTML = isEmpty
      ? `
      <div class="empty">
        <h2>HAclaw,你想让我做什么?</h2>
        <div class="chips">
          ${this._suggestionChips
            .map((chip) => this._html`<button class="chip" data-chip="${chip}">${chip}</button>`)
            .join("")}
        </div>
      </div>
    `
      : "";

    const messagesHTML = this._messages
      .map((message) => this._renderMessage(message))
      .join("");
    const modesHTML = ["plan", "automation", "execute"]
      .map(
        (mode) =>
          `<button class="mode-chip ${
            mode === this._mode ? "active" : ""
          }" data-mode="${mode}">${this._escape(this._modeLabel(mode))}</button>`,
      )
      .join("");

    this.innerHTML = `
      <main class="page">
        <header class="topbar">
          <div class="left">${this._html`HAclaw · ${status}`}</div>
          <div class="right">
            ${presenceHint}
            ${failingBadge}
            <button class="icon-btn" id="open-settings">⚙</button>
            <button class="icon-btn" id="open-drawer">☰</button>
          </div>
        </header>
        <section class="conversation">${greetingHTML}${messagesHTML}</section>
        <footer class="composer">
          <div class="modes">${modesHTML}</div>
          ${
            this._mode === "execute"
              ? '<div class="execute-warn">⚠️ 执行模式实验中,本期不会真正控制设备</div>'
              : ""
          }
          <div class="input-row">
            <input id="chat-input" type="text" placeholder="输入消息..." />
            <button id="send-btn">发送</button>
          </div>
        </footer>
      </main>
      <style>${this._styles()}</style>
    `;

    this._wireEvents();
  }

  _wireEvents() {
    this.querySelectorAll(".chip[data-chip]").forEach((el) => {
      el.addEventListener("click", () => this._onChipClick(el.dataset.chip));
    });
    this.querySelectorAll(".mode-chip[data-mode]").forEach((el) => {
      el.addEventListener("click", () => this._switchMode(el.dataset.mode));
    });
    this.querySelectorAll(".cand-chip[data-label]").forEach((el) => {
      el.addEventListener("click", () => {
        const label = el.dataset.label;
        this._appendUserMessage(label);
        this._sendChat(label);
      });
    });
    this.querySelectorAll(".cand-free-send[data-card]").forEach((el) => {
      el.addEventListener("click", () => {
        const card = el.dataset.card;
        const input = this.querySelector(`.cand-free-input[data-card="${card}"]`);
        const text = input?.value.trim();
        if (!text) {
          return;
        }
        input.value = "";
        this._appendUserMessage(text);
        this._sendChat(text);
      });
    });
    this.querySelectorAll(".cand-free-input[data-card]").forEach((el) => {
      el.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          this.querySelector(`.cand-free-send[data-card="${el.dataset.card}"]`)?.click();
        }
      });
    });
    this.querySelectorAll(".btn-approve[data-card]").forEach((el) => {
      el.addEventListener("click", () => this._onApproveDraft(el.closest(".card.draft")));
    });
    this.querySelectorAll(".card.draft [data-action='discard']").forEach((el) => {
      el.addEventListener("click", () => {
        const card = el.closest(".card.draft");
        card?.classList.add("discarded");
        const actions = card?.querySelector(".draft-actions");
        if (actions) {
          actions.innerHTML = '<span class="muted">已丢弃</span>';
        }
      });
    });
    this.querySelectorAll(".card.draft [data-action='edit']").forEach((el) => {
      el.addEventListener("click", () => {
        const card = el.closest(".card.draft");
        const yaml = card?.querySelector(".draft-yaml pre")?.textContent || "";
        const input = this.querySelector("#chat-input");
        if (input) {
          input.value = yaml;
          input.focus();
        }
      });
    });
    this.querySelectorAll(".btn-install-prompt[data-domain]").forEach((el) => {
      el.addEventListener("click", () => this._openInstallModal(el.dataset.domain));
    });
    this.querySelectorAll("[data-action='env-dismiss']").forEach((el) => {
      el.addEventListener("click", () => this._dismissEnv());
    });
    this.querySelectorAll("[data-action='env-recheck']").forEach((el) => {
      el.addEventListener("click", () => {
        this._envCardShown = false;
        this._messages = this._messages.filter((message) => message.kind !== "env_check");
        try {
          localStorage.removeItem("haclaw.env_dismissed");
        } catch (_err) {
          // Ignore storage failures in embedded HA contexts.
        }
        this._refreshState();
      });
    });
    this.querySelector("#send-btn")?.addEventListener("click", () => this._onSend());
    this.querySelector("#chat-input")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        this._onSend();
      }
    });
  }

  _styles() {
    return `
      .page {
        color: var(--primary-text-color);
        display: flex;
        flex-direction: column;
        height: 100vh;
      }

      .topbar {
        align-items: center;
        border-bottom: 1px solid var(--divider-color);
        display: flex;
        justify-content: space-between;
        padding: 8px 16px;
      }

      .topbar .right {
        align-items: center;
        display: flex;
        gap: 8px;
      }

      .badge {
        border-radius: 12px;
        font-size: 12px;
        padding: 2px 8px;
      }

      .badge.warn {
        background: rgba(219, 68, 55, 0.15);
        color: #db4437;
      }

      .badge.hint {
        background: rgba(255, 193, 7, 0.15);
        color: #b88d00;
      }

      .icon-btn {
        background: transparent;
        border: 0;
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 18px;
      }

      .conversation {
        display: flex;
        flex: 1;
        flex-direction: column;
        gap: 12px;
        overflow-y: auto;
        padding: 16px;
      }

      .empty {
        margin-top: 60px;
        text-align: center;
      }

      .empty h2 {
        font-size: 28px;
        font-weight: 650;
        margin: 0 0 24px;
      }

      .empty .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        justify-content: center;
      }

      .chip {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 24px;
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 14px;
        min-height: 44px;
        padding: 12px 20px;
      }

      .chip:hover {
        background: var(--secondary-background-color);
      }

      .composer {
        border-top: 1px solid var(--divider-color);
        padding: 12px 16px;
      }

      .modes {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
      }

      .mode-chip {
        background: transparent;
        border: 1px solid var(--divider-color);
        border-radius: 16px;
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 13px;
        padding: 6px 14px;
      }

      .mode-chip.active {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: var(--text-primary-color);
      }

      .execute-warn {
        color: #db4437;
        font-size: 12px;
        padding: 4px 8px;
      }

      .input-row {
        display: flex;
        gap: 8px;
      }

      .input-row input {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        color: var(--primary-text-color);
        flex: 1;
        padding: 10px 12px;
      }

      .input-row button {
        background: var(--primary-color);
        border: 0;
        border-radius: 6px;
        color: var(--text-primary-color);
        cursor: pointer;
        min-height: 44px;
        padding: 10px 20px;
      }

      .bubble {
        border-radius: 12px;
        max-width: 75%;
        padding: 12px 16px;
        word-wrap: break-word;
      }

      .bubble.user {
        align-self: flex-end;
        background: var(--primary-color);
        color: var(--text-primary-color);
      }

      .bubble.assistant {
        align-self: flex-start;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
      }

      .bubble.thinking {
        font-style: italic;
        opacity: 0.6;
      }

      .bubble.error {
        align-self: flex-start;
        background: rgba(255, 193, 7, 0.15);
        border: 1px solid #b88d00;
      }

      .card {
        align-self: flex-start;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 12px;
        max-width: 90%;
        padding: 12px;
      }

      .card-msg {
        font-weight: 600;
        margin-bottom: 12px;
      }

      .cand-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .cand-chip {
        align-items: flex-start;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 10px;
        color: var(--primary-text-color);
        cursor: pointer;
        display: flex;
        flex-direction: column;
        min-height: 44px;
        min-width: 120px;
        padding: 10px 14px;
      }

      .cand-chip:hover {
        background: var(--secondary-background-color);
      }

      .cand-label {
        font-size: 14px;
        font-weight: 600;
      }

      .cand-sub {
        color: var(--secondary-text-color);
        font-size: 11px;
        margin-top: 2px;
      }

      .cand-free {
        margin-top: 12px;
      }

      .cand-free-hint {
        color: var(--secondary-text-color);
        font-size: 12px;
      }

      .cand-free-row {
        display: flex;
        gap: 8px;
        margin-top: 6px;
      }

      .cand-free-input {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        color: var(--primary-text-color);
        flex: 1;
        min-height: 40px;
        padding: 10px;
      }

      .cand-free-send {
        background: var(--primary-color);
        border: 0;
        border-radius: 6px;
        color: var(--text-primary-color);
        cursor: pointer;
        min-height: 40px;
        padding: 10px 16px;
      }

      .card.draft .draft-head {
        align-items: center;
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
      }

      .card.draft .draft-title {
        font-weight: 700;
      }

      .draft-risk {
        border-radius: 10px;
        font-size: 11px;
        padding: 2px 8px;
        text-transform: uppercase;
      }

      .risk-low {
        background: rgba(27, 143, 77, 0.15);
        color: #1b8f4d;
      }

      .risk-medium {
        background: rgba(255, 193, 7, 0.15);
        color: #b88d00;
      }

      .risk-high,
      .risk-critical {
        background: rgba(219, 68, 55, 0.15);
        color: #db4437;
      }

      .warn-box {
        background: rgba(255, 193, 7, 0.1);
        border: 1px solid #b88d00;
        border-radius: 8px;
        font-size: 13px;
        margin: 8px 0;
        padding: 8px 12px;
      }

      .warn-box.small {
        font-size: 12px;
      }

      .warn-row {
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 4px 0;
      }

      .warn-row code {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 4px;
        padding: 1px 4px;
      }

      .btn-install-prompt {
        background: var(--primary-color);
        border: 0;
        border-radius: 6px;
        color: var(--text-primary-color);
        cursor: pointer;
        font-size: 12px;
        padding: 4px 10px;
      }

      .rationale {
        background: rgba(0, 0, 0, 0.04);
        border-radius: 8px;
        font-size: 13px;
        margin: 8px 0;
        padding: 8px 12px;
      }

      .rationale-title {
        font-weight: 700;
        margin-bottom: 6px;
      }

      .rationale-row {
        margin: 2px 0;
      }

      .rationale-row .muted {
        color: var(--secondary-text-color);
      }

      .draft-yaml {
        margin: 8px 0;
      }

      .draft-yaml pre {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 6px;
        font-family: ui-monospace, monospace;
        font-size: 12px;
        max-height: 240px;
        overflow: auto;
        padding: 8px;
      }

      .draft-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 8px;
      }

      .btn-primary {
        background: var(--primary-color);
        border: 0;
        border-radius: 6px;
        color: var(--text-primary-color);
        cursor: pointer;
        min-height: 40px;
        padding: 8px 14px;
      }

      .btn-primary:disabled {
        cursor: not-allowed;
        opacity: 0.5;
      }

      .btn-secondary {
        background: transparent;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        color: var(--primary-text-color);
        cursor: pointer;
        min-height: 40px;
        padding: 8px 14px;
      }

      .toast {
        background: rgba(0, 0, 0, 0.85);
        border-radius: 8px;
        bottom: 80px;
        color: white;
        font-size: 13px;
        left: 50%;
        max-width: 80%;
        padding: 10px 16px;
        position: fixed;
        transform: translateX(-50%);
        z-index: 1000;
      }

      .discarded {
        opacity: 0.5;
      }

      .muted {
        color: var(--secondary-text-color);
      }

      .card.risk {
        background: rgba(219, 68, 55, 0.05);
        border-color: #db4437;
      }

      .card.risk .risk-head {
        color: #db4437;
        font-weight: 700;
        margin-bottom: 8px;
      }

      .card.risk .risk-msg {
        margin-bottom: 8px;
      }

      .card.risk pre {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 6px;
        font-size: 12px;
        padding: 6px;
      }

      .tool-call-line {
        align-self: flex-start;
        color: var(--secondary-text-color);
        font-size: 12px;
        font-style: italic;
        padding: 6px 12px;
      }

      .tool-call-line code {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 4px;
        padding: 1px 4px;
      }

      .card.env-check .env-head {
        font-weight: 700;
        margin-bottom: 8px;
      }

      .env-row {
        align-items: center;
        border-bottom: 1px solid var(--divider-color);
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 6px 0;
      }

      .env-row:last-child {
        border-bottom: 0;
      }

      .env-row .env-label {
        font-weight: 600;
      }

      .env-row .env-hint {
        color: var(--secondary-text-color);
        font-size: 12px;
      }

      .env-row .env-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-left: auto;
      }

      .env-foot {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
        margin-top: 12px;
      }

      .modal-overlay {
        align-items: center;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        inset: 0;
        justify-content: center;
        position: fixed;
        z-index: 2000;
      }

      .modal {
        background: var(--card-background-color);
        border-radius: 12px;
        color: var(--primary-text-color);
        display: flex;
        flex-direction: column;
        max-height: 86vh;
        max-width: 700px;
        width: 92%;
      }

      .modal-head {
        align-items: center;
        border-bottom: 1px solid var(--divider-color);
        display: flex;
        font-weight: 700;
        justify-content: space-between;
        padding: 12px 16px;
      }

      .modal-close {
        background: transparent;
        border: 0;
        color: var(--primary-text-color);
        cursor: pointer;
        font-size: 18px;
      }

      .modal-info {
        background: rgba(33, 150, 243, 0.1);
        color: #1976d2;
        font-size: 12px;
        padding: 8px 16px;
      }

      .modal-body {
        background: rgba(0, 0, 0, 0.03);
        border: 0;
        color: var(--primary-text-color);
        flex: 1;
        font-family: ui-monospace, monospace;
        font-size: 12px;
        min-height: 240px;
        padding: 12px;
        resize: vertical;
      }

      .modal-foot {
        border-top: 1px solid var(--divider-color);
        display: flex;
        gap: 8px;
        justify-content: flex-end;
        padding: 12px 16px;
      }

      @media (max-width: 640px) {
        .modal {
          max-height: 92vh;
          width: 96%;
        }

        .topbar .right .icon-btn:nth-child(3) {
          display: none;
        }

        .empty .chips {
          flex-direction: column;
        }

        .modes {
          flex-wrap: wrap;
        }

        .mode-chip {
          flex: 1;
          min-width: 80px;
        }
      }
    `;
  }
}

customElements.define("haclaw-panel", HAclawPanel);
