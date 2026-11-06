# skills

个人 Agent Skills 仓库，用于保存、维护及规范化测试可复用的任务指令。

## 目录结构

```text
skills/
├── README.md                 # 仓库介绍与使用指引
├── AGENTS.md                 # Agent 规范与维护约定
├── requirements.txt          # 测试依赖（strictyaml）
├── tests/                    # 规范检查测试集
│   └── test_spec.py
└── skills/                   # 技能目录
    └── <skill-name>/
        ├── SKILL.md          # 技能入口：元信息与执行指令
        ├── references/       # [可选] 参考资料
        ├── scripts/          # [可选] 辅助脚本
        └── assets/           # [可选] 静态资源
```

## 新建技能

1. **命名目录**：使用小写英文、数字与连字符，例如 `release-check`。
2. **编写入口**：创建 `skills/<skill-name>/SKILL.md`，以 YAML frontmatter 开头：

   ```yaml
   ---
   name: <skill-name>
   description: 简明说明用途与触发场景（1-1024 字符）。
   ---
   ```

   正文编写执行步骤与可判断的完成条件，全文保持在 500 行以内。

3. **本地测试**：提交前确保规范测试全部通过：

   ```bash
   pip install -r requirements.txt
   python3 -m unittest discover -s tests -v
   ```

## 使用方式

将所需技能软链接或复制到目标 Agent 工具的技能目录即可。例如：

```bash
# 软链接技能到 Pi 的全局技能目录
ln -s "$(pwd)/skills/git" ~/.pi/agent/skills/git
```
