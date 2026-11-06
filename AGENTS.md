# 仓库维护约定

## 技能规范（与 `tests/test_spec.py` 一致）

- 存放路径：`skills/<skill-name>/SKILL.md`，目录名为小写字母、数字及连字符（正则 `^[a-z0-9]+(-[a-z0-9]+)*$`），最多 64 字符。
- Frontmatter 字段限制：仅允许 `name`（与目录名一致）、`description`（1-1024 字符）、`license`、`compatibility`（最多 500 字符）、`metadata`（字符串映射）、`allowed-tools`（空格分隔列表）。严禁添加额外未定义字段。
- 篇幅限制：`SKILL.md` 全文严格控制在 500 行以内。较长材料按需放入 `references/` 并以相对路径链接。

## 维护与验证规则

- 语言约定：仓库文档（README、提交记录）使用中文；技能正文及描述可根据适用场景使用中文或英文；保留命令、代码、路径及工具名的原文。
- 相对路径：引用文件必须保持相对路径有效。
- 验证要求：新增或修改技能后，必须运行规范测试并通过：

  ```bash
  python3 -m unittest discover -s tests -v
  ```

  测试依赖：`python3 -m pip install -r requirements.txt`。
