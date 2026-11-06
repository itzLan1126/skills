# skills

[English](README.md) | [简体中文](README.zh-CN.md)

本仓库收录个人使用的 skills，遵循 [Agent Skills](https://agentskills.io/specification) 格式。

## 安装

安装所有技能:

```bash
npx skills add itzLan1126/skills
```

### 技能列表

| Skill                                  | 说明                                                   | 安装命令                                            |
| -------------------------------------- | ------------------------------------------------------ | --------------------------------------------------- |
| [`close-pr`](skills/close-pr/SKILL.md) | PR 合并或关闭后，清理其本地及远程分支并切回默认分支    | `npx skills add itzLan1126/skills --skill close-pr` |
| [`git`](skills/git/SKILL.md)           | 检查 Git 改动、组织逻辑提交并编写 Conventional Commits | `npx skills add itzLan1126/skills --skill git`      |

## 许可证

[MIT](LICENSE)
