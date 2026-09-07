# 用户自定义工具开发手册（Skill 格式）

## 概述

用户可以在 `core/tools/custom/` 目录下创建自定义技能（Skill），系统会自动发现并热加载，无需重启服务。

每个 Skill 是一个独立的文件夹，包含说明书、脚本和可选的参考资源。所有 Skill 统一通过 `invoke_skill` 工具按 name + description 动态决策调用，Agent 根据 Skill 描述自主判断是否需要使用。所有 Skill 统一通过 `invoke_skill` 工具按 name + description 动态决策调用，Agent 根据 Skill 描述自主判断是否需要使用。

## Skill 目录结构

```
my-skill/                    # 技能文件夹（必须使用小写字母+连字符命名）
├── SKILL.md                 # 【必需】技能说明书与操作指令
├── scripts/                 # 【可选】可执行脚本
│   └── tool.py             # 工具实现（使用 @tool 装饰器）
├── references/              # 【可选】参考文档
│   └── api-docs.md
└── assets/                  # 【可选】静态资源
    └── template.json
```

## 快速开始

### 1. 创建 Skill 目录

在 `core/tools/custom/` 下创建新的文件夹，使用小写字母+连字符命名：

```bash
mkdir core/tools/custom/my-custom-tool
```

### 2. 创建 SKILL.md（必需）

在 Skill 目录下创建 `SKILL.md` 文件，说明技能的用途、使用方法和参数定义。

### 3. 实现工具脚本（可选）

在 `scripts/` 子目录下创建 Python 文件，使用 `@tool` 装饰器定义工具函数。

### 4. 自动加载

保存后系统会自动加载新 Skill，可通过 `list_tool_names()` 查看。

## SKILL.md 格式说明

`SKILL.md` 是 Skill 的核心文档，必须包含 YAML frontmatter 和正文内容：

```markdown
---
name: my-skill
description: 清晰说明这个技能的用途和功能，Agent 会根据此描述决定是否调用
---

# 技能名称

## 描述
详细说明这个技能的功能和使用场景。

## 工具列表（如果有 scripts/）

### 工具1名称
- **功能**: 工具功能描述
- **参数**:
  - `param1` (str, 必填): 参数描述
  - `param2` (int, 可选): 参数描述，默认值为 0
- **返回**: 返回值描述

## 使用示例

```python
# 示例代码
result = tool_name(param1="value", param2=10)
```

## 注意事项
- 使用限制或特殊说明
```

### Frontmatter 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | Skill 名称，用于 `invoke_skill` 调用 |
| `description` | ✅ | Skill 描述，Agent 根据此描述动态决策是否调用 |

**注意**：`description` 字段非常重要，它决定了 Agent 是否会在合适的场景下调用此 Skill。请清晰、准确地描述 Skill 的功能和适用场景。ult = tool_name(param1="value", param2=10)
```

## 注意事项
- 使用限制或特殊说明
```

### Frontmatter 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | Skill 名称，用于 `invoke_skill` 调用 |
| `description` | ✅ | Skill 描述，Agent 根据此描述动态决策是否调用 |

**注意**：`description` 字段非常重要，它决定了 Agent 是否会在合适的场景下调用此 Skill。请清晰、准确地描述 Skill 的功能和适用场景。

## 工具脚本规范

### 必须遵循的规则

1. **使用 `@tool` 装饰器**：所有工具函数必须使用 `langchain_core.tools.tool` 装饰器
2. **提供 docstring**：工具函数的 docstring 会作为工具描述，必须清晰说明工具用途
3. **参数类型注解**：所有参数必须有类型注解（如 `str`, `int`, `bool`）
4. **返回字符串**：工具函数必须返回 `str` 类型的结果

### 参数类型支持

- `str`: 字符串
- `int`: 整数
- `float`: 浮点数
- `bool`: 布尔值
- `List[str]`: 字符串列表（需要在 docstring 中说明格式）

### 错误处理
Skill 调用机制

所有 Skill 统一通过内置工具 `invoke_skill` 调用：

```python
invoke_skill(skill_name: str, args: str = "{}")
```

### 调用行为

- **纯 Markdown Skill**（无 scripts/）：返回 SKILL.md 正文内容，Agent 读取后按指令行事
- **带 scripts/ 的 Skill**：懒加载脚本并执行对应工具函数，返回执行结果

### 调用示例

```python
# 调用纯 Markdown Skill
invoke_skill("sumeru-write", "{}")

# 调用带 scripts/ 的 Skill
invoke_skill("word_count", '{"path": "chapter1.md"}')
```

### 动态决策

所有 Agent 的 system_prompt 中会注入可用 Skill 列表（name + description），Agent 根据描述自主判断是否需要调用某个 Skill。这种机制确保了：

1. **灵活性**：Agent 可以根据上下文动态选择最合适的 Skill
2. **效率**：只在需要时调用 Skill，避免不必要的开销
3. **统一性**：所有 Skill 使用相同的调用接口，简化了 Agent 的工具使用逻辑

## 
工具内部应捕获异常并返回错误信息字符串，而不是抛出异常。

## 完整示例

参考 `example-word-count/` 目录了解完整的 Skill 结构：

```
example-word-count/
├── SKILL.md                 # 技能说明书
└── scripts/
    └── word_count.py        # 工具实现
```

## Skill 调用机制

所有 Skill 统一通过内置工具 `invoke_skill` 调用：

```python
invoke_skill(skill_name: str, args: str = "{}")
```

### 调用行为

- **纯 Markdown Skill**（无 scripts/）：返回 SKILL.md 正文内容，Agent 读取后按指令行事
- **带 scripts/ 的 Skill**：懒加载脚本并执行对应工具函数，返回执行结果

### 调用示例

```python
# 调用纯 Markdown Skill
invoke_skill("sumeru-write", "{}")

# 调用带 scripts/ 的 Skill
invoke_skill("word_count", '{"path": "chapter1.md"}')
```

### 动态决策

所有 Agent 的 system_prompt 中会注入可用 Skill 列表（name + description），Agent 根据描述自主判断是否需要调用某个 Skill。这种机制确保了：

1. **灵活性**：Agent 可以根据上下文动态选择最合适的 Skill
2. **效率**：只在需要时调用 Skill，避免不必要的开销
3. **统一性**：所有 Skill 使用相同的调用接口，简化了 Agent 的工具使用逻辑

## 热加载

修改自定义 Skill 后，调用 `reload_custom_tools()` 即可重新加载，无需重启服务。

## 调试

加载失败的错误信息会记录在日志中，查看 `log/` 目录下的日志文件。
