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
  }

  _appendUserMessage(text) {
    this._messages.push({ kind: "user_text", text });
    this._render();
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
    return "";
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

      @media (max-width: 640px) {
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
