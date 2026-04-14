# Mr.G - AI 语言学习助手（精简版）

[English](./README.md) | 中文

这是 Mr.G 学习体系的清理版仓库，保留核心能力，移除噪音内容，便于持续迭代。

## 项目能力
- 生成单词记忆卡（词源/联想记忆法）。
- 对长难句进行结构化拆解。
- 分析段落逻辑并给出适配用户水平的改写。
- 基于个人错题库进行迭代测试（test-mode）。

## 当前重点：Codex Skill
- Skill 目录：[`skills/codex/learn-eng/`](./skills/codex/learn-eng/)
- Skill 名称：`$learn-eng`

核心文件：
- [`skills/codex/learn-eng/SKILL.md`](./skills/codex/learn-eng/SKILL.md)
- [`skills/codex/learn-eng/agents/openai.yaml`](./skills/codex/learn-eng/agents/openai.yaml)
- [`skills/codex/learn-eng/references/output-contracts.md`](./skills/codex/learn-eng/references/output-contracts.md)

学习循环数据文件：
- [`skills/codex/learn-eng/user.md`](./skills/codex/learn-eng/user.md)
- [`skills/codex/learn-eng/vocab-repo.md`](./skills/codex/learn-eng/vocab-repo.md)
- [`skills/codex/learn-eng/stenc-repo.md`](./skills/codex/learn-eng/stenc-repo.md)

脚本：
- [`skills/codex/learn-eng/scripts/learn_eng_repo.py`](./skills/codex/learn-eng/scripts/learn_eng_repo.py)
- [`skills/codex/learn-eng/scripts/find_template_entry.py`](./skills/codex/learn-eng/scripts/find_template_entry.py)

## 快速命令
在 `skills/codex/learn-eng/` 目录执行：

```bash
python3 scripts/learn_eng_repo.py init
python3 scripts/learn_eng_repo.py set-profile --tier intermediate --goal "Exam Prep"
python3 scripts/learn_eng_repo.py ingest --input "abstruse, obdurate, <长难句>"
python3 scripts/learn_eng_repo.py test-mode --vocab-count 5 --sentence-count 3
python3 scripts/learn_eng_repo.py mark-missed --word abstruse
```

## Prompt 资产
- [`Prompts/GPT4-browser-version.md`](./Prompts/GPT4-browser-version.md)
- [`Prompts/2024-mnemonics-only.md`](./Prompts/2024-mnemonics-only.md)

## 历史归档
历史版本和旧素材已迁移到 [`old-assets/`](./old-assets/)，主目录保持干净。

## 许可证
MIT License，见 [`LICENSE`](./LICENSE)。
