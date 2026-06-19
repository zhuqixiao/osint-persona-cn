# 贡献指南

感谢参与 **OSINT Toolkit（个人情报台 / osint-persona-cn）** 开源协作。本文面向人类贡献者与使用 AI 辅助开发的维护者。

## 开始之前

1. 阅读 [README.md](../README.md) 与 [CAPABILITIES.md](CAPABILITIES.md) 了解产品边界  
2. AI 维护者请阅读根目录 [AGENTS.md](../AGENTS.md)  
3. 架构细节见 [ARCHITECTURE.md](ARCHITECTURE.md)  

## 环境搭建

```bash
git clone https://github.com/GuoEdge/osint-persona-cn.git
cd osint-persona-cn
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -e ".[dev,web,bilibili]"
pytest
```

可选：`pip install -e ".[browser]"` 以启用 Playwright 补洞同步。

## 分支与提交

- 从 `master` 拉 feature 分支，例如 `feat/bilibili-subtitle-fallback`  
- 提交信息建议 [Conventional Commits](https://www.conventionalcommits.org/)：  
  - `feat:` 新功能  
  - `fix:` 缺陷修复  
  - `docs:` 文档  
  - `test:` 测试  
  - `refactor:` 重构（无行为变化）  

## 代码规范

```bash
ruff check src tests
ruff format src tests
pytest
```

- 新模块放在 `src/osint_toolkit/` 对应子包  
- 搜罗源：`collectors/` + 在 `registry.py` 注册  
- 行为导入：`ingest/` + 必要时更新 `ingest_capabilities.py`  
- Web API：`web/routes/api.py` + `web/schemas.py`  
- 前端：`web/static/app.js`、`web/templates/`  

## 测试要求

| 改动类型 | 期望 |
|----------|------|
| 纯逻辑 | 单元测试于 `tests/` |
| HTTP API | `TestClient` 集成测试 |
| 需真实浏览器 | `@pytest.mark.integration`，CI 可跳过 |
| 配置项 | 更新 `config/config.example.yaml` 与文档 |

运行：`pytest` 或 `pytest tests/test_xxx.py -q`

## Pull Request 清单

- [ ] `pytest` 通过  
- [ ] `ruff check` 无新增问题  
- [ ] 用户可见行为已更新 `docs/CAPABILITIES.md` 或 README  
- [ ] 未包含密钥、Cookie、`.osint` 个人数据  
- [ ] 破坏性 API/配置变更在 PR 描述中说明  

## 安全与隐私

- 不要提交 `.env`、`config.yaml`（含真实 Key）、Cookie JSON  
- 见 [PRIVACY.md](PRIVACY.md)  
- 漏洞请通过 GitHub Security Advisory 或私信维护者，勿在公开 Issue 贴 exploit  

## 文档贡献

欢迎改进：

- `README.md` — 入门与功能索引  
- `docs/CAPABILITIES.md` — 能力矩阵  
- `AGENTS.md` — AI 维护入口  
- `extension/README.md` — 扩展说明  

中文 UI 文案与面向用户文档以中文为主；代码注释与 API 命名保持项目既有风格（中英混用处与周边一致即可）。

## 行为与期望

- Issue：描述复现步骤、期望与实际、`osint doctor` 摘要  
- PR：小而聚焦比巨型重构更易 review  
- 尊重各平台服务条款；本项目仅供合法 OSINT 与个人研究  

## 联系

- GitHub Issues / Discussions（若已开启）  
- 仓库：https://github.com/GuoEdge/osint-persona-cn  
