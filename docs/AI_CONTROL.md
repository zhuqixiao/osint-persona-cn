# AI 可控介入

## 配置文件

- 持久导向: `%USERPROFILE%\.osint\ai_directives.yaml`
- Prompt 覆盖: `%USERPROFILE%\.osint\prompts\*.md`

## 命令

```bash
osint ai directives show
osint ai directives edit
osint ai prompts list
osint ai prompts edit summarize
osint search "话题" --ai-instruct "只关注实操"
osint search "话题" --no-ai-step persona_simulate
```

## 原则

硬约束 > 用户 prompt > 软偏好 > Persona 推断。AI 不静默删除采集结果。

### 当前硬约束

1. 不替用户做最终有价值/无价值的裁决
2. 区分事实、作者主张、社区主观感受
3. 无字幕的B站视频须标注未分析画面
4. 不静默隐藏任何采集结果
5. 不得引入提供的内容中不存在的信息或观点

**第 5 条** 针对 AI 摘要/评论归纳的幻觉问题：模型只能基于提供的标题、正文、社区观点生成摘要，不得编造原文未提及的事件、人物、产品。
