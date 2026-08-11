# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM API

编辑 `config.ini`，配置你的 LLM API 信息：

```ini
[llm_api_aliyun]
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
api_key = your-api-key-here
model = qwen3.7-plus
```

### 3. 运行写作系统

```bash
python main.py \
  --output ./output/novel \
  --genre "科幻" \
  --words 150000 \
  --style "硬核科幻，注重科学细节，节奏紧凑" \
  --premise "2150年，人类在火星建立了第一个永久殖民地，但发现了一种神秘的外星遗迹" \
  --reference "《三体》《火星救援》" \
  --extra "主角是一位植物学家，需要在火星上解决生存危机"
```

### 4. 查看输出

写作完成后，输出目录结构如下：

```
output/novel/
├── blueprint.json          # 故事蓝图
├── outlines/               # 章节大纲
│   ├── chapter_001.json
│   ├── chapter_002.json
│   └── ...
├── chapters/               # 章节正文
│   ├── chapter_001.txt
│   ├── chapter_002.txt
│   └── ...
├── reviews/                # 审校报告
│   ├── review_chapter_001_round_0.json
│   └── ...
├── memory/                 # 记忆系统数据
│   ├── story_memory.json
│   ├── character_sheets.json
│   ├── plot_tracker.json
│   └── summary_chain.json
├── logs/                   # 运行日志
│   └── writer_20240101.log
└── 小说标题.txt            # 最终合并的小说文件
```

## 参数说明

| 参数 | 简写 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `--output` | `-o` | ✓ | 项目输出目录 | `./output/novel` |
| `--genre` | `-g` | ✓ | 题材类型 | `科幻`、`悬疑`、`言情` |
| `--words` | `-w` | ✓ | 目标总字数 | `150000` |
| `--style` | `-s` | ✓ | 风格要求 | `硬核科幻，注重科学细节` |
| `--premise` | `-p` | ✓ | 核心设定/前提 | `2150年火星殖民地的故事` |
| `--reference` | `-r` | ✗ | 参考作品 | `《三体》《火星救援》` |
| `--extra` | `-e` | ✗ | 其他要求 | `主角是植物学家` |
| `--max-revisions` | - | ✗ | 最大修改轮次（默认3） | `5` |

## 示例场景

### 悬疑推理小说

```bash
python main.py \
  -o ./output/mystery \
  -g "悬疑推理" \
  -w 120000 \
  -s "本格推理，逻辑严密，注重诡计设计" \
  -p "一座与世隔绝的雪山别墅中发生了连环杀人案" \
  -r "《无人生还》《嫌疑人X的献身》" \
  -e "侦探是一位退休的刑警，凶手在7位嫌疑人中"
```

### 都市言情小说

```bash
python main.py \
  -o ./output/romance \
  -g "都市言情" \
  -w 100000 \
  -s "温馨治愈，细腻的情感描写，轻喜剧风格" \
  -p "两个性格迥异的职场新人在同一家公司相遇" \
  -r "《何以笙箫默》《微微一笑很倾城》" \
  -e "男主是冷面总裁，女主是乐观的实习生"
```

### 奇幻冒险小说

```bash
python main.py \
  -o ./output/fantasy \
  -g "奇幻冒险" \
  -w 200000 \
  -s "史诗奇幻，宏大的世界观，丰富的魔法体系" \
  -p "一个普通少年意外获得了远古神器的力量，踏上拯救世界的旅程" \
  -r "《指环王》《冰与火之歌》" \
  -e "需要设计完整的魔法体系和种族设定"
```

## 自定义配置

### 调整 LLM 参数

编辑 `config.ini`：

```ini
[llm_config]
temperature = 0.7      # 创造性（0.0-1.0，越高越有创意）
max_tokens = 8000      # 单次生成最大 token 数
top_p = 0.9           # 核采样参数
timeout = 60          # API 超时时间（秒）
```

### 调整项目配置

```ini
[project_config]
default_max_revisions = 3           # 默认最大修改轮次
default_word_count_per_chapter = 5000  # 每章默认字数
summary_window_size = 3             # 摘要滑动窗口大小
enable_checkpoint = true            # 是否启用检查点
```

### 调整日志配置

```ini
[logging]
log_level = INFO        # 日志级别：DEBUG/INFO/WARNING/ERROR
console_output = true   # 是否输出到控制台
```

## 进阶用法

### 使用 Python API

```python
from main import NovelWriterOrchestrator

# 创建编排器
orchestrator = NovelWriterOrchestrator(
    project_dir="./output/novel",
    max_revisions=3,
)

# 运行写作流程
success = orchestrator.run(
    genre="科幻",
    target_word_count=150000,
    style="硬核科幻，注重科学细节",
    premise="2150年火星殖民地的故事",
    reference="《三体》",
    extra_requirements="主角是植物学家",
)

if success:
    print("写作完成！")
else:
    print("写作失败")
```

### 单独使用某个 Agent

```python
from core.agents.master_planner import MasterPlannerAgent

# 创建总规划师
planner = MasterPlannerAgent(project_dir="./output")

# 生成故事蓝图
blueprint = planner.generate_blueprint(
    genre="科幻",
    target_word_count=150000,
    style="硬核科幻",
    premise="火星殖民地故事",
)

print(f"标题：{blueprint.title}")
print(f"角色数：{len(blueprint.characters)}")
print(f"章节数：{sum(a.chapters[1] - a.chapters[0] + 1 for a in blueprint.acts)}")
```

## 故障排查

### API 调用失败

检查 `config.ini` 中的 API 配置是否正确：
- `base_url` 是否可访问
- `api_key` 是否有效
- `model` 名称是否正确

### 生成内容质量不佳

尝试调整以下参数：
- 提高 `temperature`（如 0.8-0.9）增加创造性
- 增加 `max_revisions` 让系统多次修改
- 在 `--extra` 中添加更详细的要求

### 内存不足

如果生成过程中遇到内存问题：
- 减小 `default_word_count_per_chapter`
- 减小 `summary_window_size`
- 使用更小的模型

## 性能优化建议

1. **使用更快的模型**：如果 API 支持，选择更快的模型
2. **调整并发**：当前系统为串行执行，可根据需要改造为并行
3. **缓存策略**：对于重复使用的上下文，可以添加缓存
4. **分批生成**：对于超长篇小说，可以分批次生成

## 常见问题

**Q: 生成的小说质量如何？**  
A: 取决于 LLM 的能力和提示词的质量。建议多次迭代优化提示词。

**Q: 可以生成多长的小说？**  
A: 理论上无限制，但建议单次生成不超过 30 万字，过长的小说建议分卷生成。

**Q: 如何保证前后一致性？**  
A: 系统通过记忆系统（角色卡片、情节追踪、摘要链）来维护一致性，但仍建议人工审校。

**Q: 可以中途停止并恢复吗？**  
A: 当前版本不支持断点续传，但所有中间结果都会保存，可以基于已有内容继续。
