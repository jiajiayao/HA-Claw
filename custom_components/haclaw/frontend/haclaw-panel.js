class HAclawPanel extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <ha-card>
        <div class="haclaw-panel">
          <h2>HAclaw</h2>
          <p>中文优先、安全优先的 Home Assistant AI 助手正在初始化。</p>
        </div>
      </ha-card>
      <style>
        .haclaw-panel {
          padding: 16px;
        }
        h2 {
          margin: 0 0 8px;
        }
        p {
          margin: 0;
        }
      </style>
    `;
  }
}

customElements.define("haclaw-panel", HAclawPanel);
