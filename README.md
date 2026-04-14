# learn-eng-skill

一个面向中文学习者的英语学习 Skill 项目，支持在 Codex 中进行：
- 难词分析
- 长难句拆解
- 段落逻辑理解
- 错题驱动的迭代测试

项目核心目标：把“背单词 + 读句子 + 做测试 + 复盘”串成一条稳定、可积累的学习链路。

## 适合谁
- 考研英语 / IELTS / TOEFL 学习者
- 希望用结构化方式提升阅读与写作理解的人
- 需要可追踪错题库和复习闭环的用户

## 核心能力
- 自动路由三类输入：词汇 / 句子 / 段落
- 词汇卡片化输出（定义、发音、例句、助记、搭配、误用提醒等）
- 句子结构标注（主谓宾、修饰层级、连接词、引导语等）
- 段落逻辑拆解（主张、论证角色、连接信号、隐含前提）
- Test Mode 选择题训练（按错题优先）
- 学习数据自动沉淀到本地仓库（可持续迭代）

## 使用前准备（Codex）
1. 获取 Codex（官方入口）
- 产品页：[OpenAI Codex](https://openai.com/codex)
- 快速开始页：[Get started with Codex](https://openai.com/codex/get-started/)

2. 克隆仓库
```bash
git clone git@github.com:EmbraceAGI/Mr.G-Your-AI-English-all-language-Tutor.git
cd Mr.G-Your-AI-English-all-language-Tutor
```

3. Skill 目录
- Skill 主文件：`skills/codex/learn-eng/SKILL.md`
- 推荐在 Codex 中直接以该路径调用 `$learn-eng`

## 首次使用（5 项配置）
首次会采集以下配置（可缺省）：
1. 学习语言
2. 当前水平 / 考试体系（CEFR / IELTS / TOEFL / 考研）
3. 当前分数
4. 目标
5. 解释风格（全英文 / 中英结合）

示例：
```text
Language=English; Level=考研英语; Score=45; Goal=70; Style=中英结合
```

## 日常使用方式
- 发一个词：进入词汇分析
- 发一句话：进入句子分析
- 发一段话：进入段落分析
- 输入 `test-mode`：进入错题优先的选择题训练

## 学习数据文件（本地）
- `skills/codex/learn-eng/user.md`：用户档案（等级、目标、风格等）
- `skills/codex/learn-eng/vocab-repo.md`：难词库
- `skills/codex/learn-eng/stenc-repo.md`：长难句库
- `skills/codex/learn-eng/vocabs.csv`：词卡字段与错题计数（`TestErrors`）
- `skills/codex/learn-eng/references/vocab-template.md`：助记知识库模板

## 项目结构
```text
skills/codex/learn-eng/
├── SKILL.md
├── user.md
├── vocab-repo.md
├── stenc-repo.md
├── vocabs.csv
├── scripts/
└── references/
```

## 路线图
- 持续优化 test-mode 的题目质量与错因定位
- 强化词汇与句法的联动复习
- 逐步适配更多 agent 平台（保持 provider-neutral）

## 说明
- 本项目以中文用户体验为优先。
- 所有学习记录默认保存在本地仓库文件中，便于长期积累和复盘。
