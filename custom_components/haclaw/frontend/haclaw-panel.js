class HAclawPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = undefined;
    this._busy = "";
    this._result = undefined;
    this._draftId = "";
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  async _testConnection() {
    await this._call("test", "test_connection", {});
  }

  async _createDraft() {
    const title = this.querySelector("#draft-title")?.value?.trim();
    const description = this.querySelector("#draft-description")?.value?.trim() || "";
    const triggerText = this.querySelector("#draft-trigger")?.value || "[]";
    const actionText = this.querySelector("#draft-action")?.value || "[]";

    if (!title) {
      this._result = { success: false, message: "请填写草稿标题。" };
      this._render();
      return;
    }

    let trigger;
    let action;
    try {
      trigger = JSON.parse(triggerText);
      action = JSON.parse(actionText);
    } catch (err) {
      this._result = { success: false, message: `JSON 解析失败：${err.message}` };
      this._render();
      return;
    }

    const response = await this._call("draft", "create_automation_draft", {
      title,
      description,
      source: "panel",
      automation: {
        alias: title,
        trigger,
        condition: [],
        action,
        mode: "single",
      },
    });

    if (response?.draft?.id) {
      this._draftId = response.draft.id;
      this._render();
    }
  }

  async _approveDraft() {
    const draftId =
      this.querySelector("#draft-id")?.value?.trim() || this._draftId || "";
    const confirmed = Boolean(this.querySelector("#risk-confirmed")?.checked);

    if (!draftId) {
      this._result = { success: false, message: "请先创建或填写草稿 ID。" };
      this._render();
      return;
    }

    await this._call("approve", "approve_automation_draft", {
      draft_id: draftId,
      confirmed,
    });
  }

  async _call(kind, service, serviceData) {
    if (!this._hass) {
      this._result = { success: false, message: "Home Assistant 尚未连接。" };
      this._render();
      return undefined;
    }

    this._busy = kind;
    this._result = undefined;
    this._render();

    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: "haclaw",
        service,
        service_data: serviceData,
        return_response: true,
      });
      const response = result?.response || result || {};
      this._result = response;
      this._busy = "";
      this._render();
      return response;
    } catch (err) {
      this._result = {
        success: false,
        message: err?.message || "服务调用失败。",
      };
      this._busy = "";
      this._render();
      return undefined;
    }
  }

  _render() {
    if (!this.isConnected) {
      return;
    }

    const result = this._result;
    const resultClass = result?.success ? "ok" : result ? "error" : "";
    const triggerValue = JSON.stringify(
      [{ platform: "time", at: "19:00:00" }],
      null,
      2,
    );
    const actionValue = JSON.stringify(
      [
        {
          service: "light.turn_on",
          target: { entity_id: "light.living_room" },
        },
      ],
      null,
      2,
    );

    this.innerHTML = `
      <main class="page">
        <header class="topbar">
          <div>
            <h1>HAclaw</h1>
            <p>中文智能家居助手</p>
          </div>
          <button class="icon-button" id="test-connection" title="测试连接">
            <ha-icon icon="mdi:connection"></ha-icon>
            <span>${this._busy === "test" ? "测试中" : "测试连接"}</span>
          </button>
        </header>

        <section class="grid">
          <div class="panel">
            <h2>自动化草稿</h2>
            <label>
              <span>标题</span>
              <input id="draft-title" value="晚上打开客厅灯" />
            </label>
            <label>
              <span>说明</span>
              <input id="draft-description" value="每天晚上 7 点打开客厅灯，审批前不会启用。" />
            </label>
            <label>
              <span>触发</span>
              <textarea id="draft-trigger" spellcheck="false">${triggerValue}</textarea>
            </label>
            <label>
              <span>动作</span>
              <textarea id="draft-action" spellcheck="false">${actionValue}</textarea>
            </label>
            <button class="primary" id="create-draft">
              <ha-icon icon="mdi:file-document-edit-outline"></ha-icon>
              <span>${this._busy === "draft" ? "保存中" : "保存草稿"}</span>
            </button>
          </div>

          <div class="panel">
            <h2>审批写入</h2>
            <label>
              <span>草稿 ID</span>
              <input id="draft-id" value="${this._escape(this._draftId)}" />
            </label>
            <label class="check">
              <input id="risk-confirmed" type="checkbox" />
              <span>确认风险操作</span>
            </label>
            <button class="primary" id="approve-draft">
              <ha-icon icon="mdi:check-decagram-outline"></ha-icon>
              <span>${this._busy === "approve" ? "写入中" : "审批写入"}</span>
            </button>
            <div class="risk">
              <strong>写入目标</strong>
              <code>/config/haclaw/automations.yaml</code>
            </div>
          </div>
        </section>

        <section class="result ${resultClass}">
          ${
            result
              ? `<strong>${this._escape(result.message || "执行完成")}</strong>
                 <pre>${this._escape(JSON.stringify(result, null, 2))}</pre>`
              : "<strong>等待操作</strong>"
          }
        </section>
      </main>

      <style>
        .page {
          color: var(--primary-text-color);
          display: flex;
          flex-direction: column;
          gap: 16px;
          padding: 20px;
        }

        .topbar {
          align-items: center;
          border-bottom: 1px solid var(--divider-color);
          display: flex;
          justify-content: space-between;
          gap: 16px;
          padding-bottom: 16px;
        }

        h1,
        h2,
        p {
          margin: 0;
        }

        h1 {
          font-size: 28px;
          font-weight: 650;
        }

        h2 {
          font-size: 18px;
          font-weight: 650;
        }

        p {
          color: var(--secondary-text-color);
          font-size: 14px;
          margin-top: 4px;
        }

        .grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        }

        .panel {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          display: flex;
          flex-direction: column;
          gap: 14px;
          padding: 16px;
        }

        label {
          display: flex;
          flex-direction: column;
          gap: 6px;
          font-size: 13px;
          font-weight: 600;
        }

        input,
        textarea {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          box-sizing: border-box;
          color: var(--primary-text-color);
          font: inherit;
          min-width: 0;
          padding: 10px;
          width: 100%;
        }

        textarea {
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          min-height: 150px;
          resize: vertical;
        }

        button {
          align-items: center;
          border: 0;
          border-radius: 6px;
          cursor: pointer;
          display: inline-flex;
          font: inherit;
          font-weight: 650;
          gap: 8px;
          min-height: 40px;
          justify-content: center;
          padding: 0 14px;
        }

        .primary,
        .icon-button {
          background: var(--primary-color);
          color: var(--text-primary-color);
        }

        .check {
          align-items: center;
          flex-direction: row;
          font-weight: 600;
        }

        .check input {
          width: auto;
        }

        .risk,
        .result {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 14px;
        }

        .risk {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        code,
        pre {
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          overflow-wrap: anywhere;
          white-space: pre-wrap;
        }

        .result.ok {
          border-color: var(--success-color, #1b8f4d);
        }

        .result.error {
          border-color: var(--error-color, #db4437);
        }

        pre {
          margin: 10px 0 0;
          max-height: 360px;
          overflow: auto;
        }

        @media (max-width: 640px) {
          .page {
            padding: 12px;
          }

          .topbar {
            align-items: stretch;
            flex-direction: column;
          }
        }
      </style>
    `;

    this.querySelector("#test-connection")?.addEventListener("click", () =>
      this._testConnection(),
    );
    this.querySelector("#create-draft")?.addEventListener("click", () =>
      this._createDraft(),
    );
    this.querySelector("#approve-draft")?.addEventListener("click", () =>
      this._approveDraft(),
    );
  }

  _escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }
}

customElements.define("haclaw-panel", HAclawPanel);
