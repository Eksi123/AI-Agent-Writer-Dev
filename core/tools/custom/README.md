# 用户自定义工具开发手册（Skill 格式）

## 概述

用户可以在 `core/tools/custom/` 目录下创建自定义工具（Skill），系统会自动发现并热加载，无需重启服务。

每个 Skill 是一个独立的文件夹，包含说明书、脚本和可选的参考资源。

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

`SKILL.md` 是 Skill 的核心文档，应包含：

```markdown
# 技能名称

## 描述
清晰说明这个技能的用途和功能。

## 工具列表

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

工具内部应捕获异常并返回错误信息字符串，而不是抛出异常。

## 完整示例

参考 `example-word-count/` 目录了解完整的 Skill 结构：

```
example-word-count/
├── SKILL.md                 # 技能说明书
└── scripts/
    └── word_count.py        # 工具实现
```

## 热加载

修改自定义 Skill 后，调用 `reload_custom_tools()` 即可重新加载，无需重启服务。

## 调试

加载失败的错误信息会记录在日志中，查看 `log/` 目录下的日志文件。
