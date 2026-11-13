# Supplementary Code for "十二音声乐作品表演中的声调参照与钢琴声学反馈"

本仓库包含论文《十二音声乐作品表演中的声调参照与钢琴声学反馈——以罗忠镕〈往事二三〉的量化分析为例》的全部数据分析代码与派生数据。旨在为音乐表演分析提供可复现、可迁移的量化工具。

## 仓库结构

```text
.
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── data/
│   ├── 往事二三_详细参数表_v3.csv
│   ├── 声调匹配与泛音匹配_逐音.csv
│   └── 声学参照差值_逐音.csv
├── figures/
│   ├── 往事二三_声调匹配与泛音匹配图.svg
│   └── 往事二三_声学参照差值图.svg
└── scripts/
    ├── 往事二三_声调匹配与泛音匹配模型.py
    ├── 往事二三_声学参照差值模型.py
    ├── 各段落声调匹配与声学参照统计.py
    ├── 五度映射的敏感性检验.py
    ├── 粗糙度权重敏感性检验.py
    └── 语言评分权重敏感性检验.py
```

## 如何运行

1. **安装依赖**：确保你的 Python 环境已安装所需库。
```bash
   pip install -r requirements.txt
```

2. **准备数据**：确保 `data/` 文件夹下存在 `往事二三_详细参数表_v3.csv`。

3. **生成图表与逐音数据**：依次运行 `scripts/` 目录下的两个主模型脚本。
```bash
   python scripts/往事二三_声调匹配与泛音匹配模型.py
   python scripts/往事二三_声学参照差值模型.py
```
4. **复现论文表格与敏感性检验
```bash
   python scripts/各段落声调匹配与声学参照统计.py
   python scripts/五度映射的敏感性检验.py
   python scripts/粗糙度权重敏感性检验.py
   python scripts/语言评分权重敏感性检验.py
```

## 可迁移性说明

本套代码采用了“配置驱动”架构。若需分析其他无调性声乐作品，仅需在 `scripts/` 各脚本顶部的“配置区”替换以下参数：

- 新的 `CSV_FILE_PATH`
- 新的 `MEASURE_LENGTHS`（小节时长表）
- 新的 `BASE_TONE_DICT`（歌词本调字典）
- 新的 `SECTIONS`（段落划分）

## 引用

如果您使用了本仓库的代码或数据，请引用以下论文（目前为预印本/在投状态）：

> 林彤昕. (2026). 十二音声乐作品表演中的声调参照与钢琴声学反馈——以罗忠镕《往事二三》的量化分析为例 [Manuscript submitted for publication].