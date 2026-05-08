# HAclaw 完整 Agent Loop / 工具执行 / 安全层 (Follow-up to v1.0 chat shell)

- **状态**: Placeholder, 延后实现
- **依赖**: `2026-05-08-haclaw-chat-ui-design.md`(范围 B)必须先落地
- **范围**: C(完整 Agent loop + 工具执行 + 安全层 + 风险确认 + 审计 trace UI)
- **作者**: HAclaw 项目
- **日期**: 2026-05-08

## 1. 目的

本文件占位记录 v1.0 范围 C 的设计意图,避免在 chat 壳交付后丢失。**详细设计在 chat 壳实现并真实使用一段时间后再展开**,因为:

- chat 壳上线后才能拿到真实对话样本,知道用户实际想触发哪些工具
- 工具白名单、风险等级表必须看实际样本调
- 安全层的开发必须有真实的"模型尝试越界"案例,不然容易设计过度

## 2. 范围概览

延后实现的能力:

### 2.1 工具执行层

- 实现 `tools/registry.py` 工具注册表
- 实现 `tools/entity.py`、`tools/service.py`、`tools/xiaomi.py` 等工具(README §"工具层设计")
- 模型 `tool_call` 类型不再只是灰行展示,而是真实路由到工具 → 执行 → 把结果作为新一轮 user 消息(或 system observation)灌回模型,推进多轮迭代
- 默认 `max_iterations = 5`

### 2.2 安全层

- 实现 `agent/safety.py`
- 服务白名单:`light.turn_on`、`switch.turn_on` 等可直接执行;`lock.unlock`、`shell_command.*` 等必须走 `risk_confirmation` 流程
- 风险等级计算:**由代码计算,不只信模型自评**(README §"风险分级")
- 拦截 token 类操作、`xiaomi_miot.get_token`、`shell_command.*`、`.storage` 修改等

### 2.3 风险确认完整闭环

- 范围 B 的 `risk_confirmation` 卡片"确认执行"按钮目前禁用
- 范围 C 后,确认按钮真实路由到工具执行;前端要在卡片上显示完整计划动作 diff(如开锁前给出"将解锁 lock.front_door,影响范围:门"等)
- 多轮确认:超过某风险阈值要求二次确认 / 双因素

### 2.4 审计 trace 页

- 设置 modal 里加"查看审计日志"
- 单独 view:按时间倒序列出最近审计事件,带筛选(类型、风险等级)
- 不能在审计 trace 里展示完整 API key、token 等;脱敏规则严格遵守 README

### 2.5 增强的对话能力

- 多会话(每个会话独立 conversation_id,可重命名,可删除)
- 对话内编辑用户消息后重发
- 支持 `automation_edit_request` 类型(用户对草稿提改进意见,模型生成 v2 草稿)

### 2.6 小米生态深度增强

- `tools/xiaomi.py` 实现 `get_xiaomi_entities`,基于厂商、型号、集成、区域、friendly_name 中文关键词
- 房间清扫的 segment ID 持久化映射(`/config/haclaw/xiaomi_room_map.json`)
- 多次确认后写入

### 2.7 Dashboard 草稿

- README §"Dashboard 生成"
- 类似自动化草稿,前端预览 + 手动安装说明

## 3. 实现先后建议(待详细设计时再排)

```
范围 C 子模块的可能顺序:
  ① 工具注册表(读取类工具,无副作用)
   ↓
  ② 多轮迭代 + observation 注回模型
   ↓
  ③ 安全层 + 服务白名单 + 风险等级表
   ↓
  ④ 风险确认完整闭环
   ↓
  ⑤ 小米生态工具
   ↓
  ⑥ 审计 trace UI
   ↓
  ⑦ 多会话管理
   ↓
  ⑧ Dashboard 草稿
```

## 4. 对范围 B 的兼容承诺

范围 C 实现时,以下 B 阶段的接口/契约**不应破坏**:

- `haclaw/chat` WS 命令的入参格式(可加新可选字段)
- `haclaw.bind_presence_entity` / `haclaw.get_environment_readiness` service 签名
- `validate_automation_draft` 的现有返回字段
- `/config/haclaw/conversations.json` 文件 schema(可向前兼容扩展)
- 前端消息组件 dispatch 机制(按 `type` 分发)— C 阶段只新增 type,不替换

## 5. 已知风险

- 工具执行层一旦上线,任何遗漏的安全检查都可能直接影响真实家居 — 必须有完整测试覆盖 + 灰度
- 模型可能学会绕过协议(在 `final_response.message` 里编造工具结果)— 前端必须明确区分"模型说的"和"工具实际返回的"
- Xiaomi 生态识别错误率高的情况下,误操作风险大 — 建议先 dry-run 模式

## 6. 何时启动详细设计

触发条件之一即可:

- 范围 B 上线 ≥ 2 周,有 ≥ 50 条真实对话样本
- 用户反馈强烈要求工具真正执行
- 出现明显被卡住的场景("我说打开灯但它只能给我建议")

启动时,在本文件同目录新建 `YYYY-MM-DD-haclaw-agent-loop-tools-detailed-design.md`,本文件升级为"已被 superseded"。
