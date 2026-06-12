# Windows 本机验收清单

1. 设置 `DEEPSEEK_API_KEY` 用户环境变量
2. `pip install -e ".[dev]"`
3. `osint auth sync-cookies --browser edge`
4. `osint auth test --target all`
5. `osint search "测试话题" --trace`
6. `osint search "测试话题" --digest --no-ai`（无 API 时）
7. `osint save <知乎或B站URL> --with-comments`
8. `osint recall "测试"`
9. `osint ingest browser --since 30`
10. `osint persona build --review`
11. `osint run list` / `osint run show <run_id>`

## Web 控制台验收

1. `pip install -e ".[dev,web]"`
2. `osint web` → 打开 http://127.0.0.1:8787
3. **设置**：API + Cookie 状态正常，`同步 Cookie` 成功
4. **搜罗**：多源搜索 → 步骤条 → 结果卡片 → 勾选 digest → 报告与追问
5. **搜罗**：对结果提交 feedback（有用/噪音等）
6. **收录**：粘贴 URL 收录（含评论选项）
7. **知识库**：recall 到刚收录内容
8. **简报**：今日简报 + 历史报告列表
9. **导入**：browser / bilibili / zhihu
10. **画像**：build → show → rollback
11. **运行记录**：list → 详情 → artifact 链接
12. **AI 控制**：directives / prompts 编辑保存
