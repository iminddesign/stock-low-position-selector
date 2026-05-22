---
name: stock-low-position-selector
description: |
  A股热榜低位选股工具 - 从热度榜前300中筛选技术面低位、适合建仓/加仓的股票。
  支持问财API和妙想API双数据源，包含净利润筛选、风险筛查、技术形态分析等功能。
  当用户询问"低位选股"、"热榜选股"、"技术面选股"、"建仓股票推荐"时使用此技能。
version: 3.0.0
author: imeiming
license: MIT
tags:
  - finance
  - stock
  - technical-analysis
  - A股
  - 选股
homepage: https://github.com/iminddesign/stock-low-position-selector
repository: https://github.com/iminddesign/stock-low-position-selector
---

# A股热榜低位选股工具

## 功能概述

从A股热度人气榜前300名中，筛选技术面处于低位、适合建仓/加仓的股票。

### 核心功能

1. **热榜获取**：分3批获取热度榜前300只股票
2. **技术分析**：MACD、KDJ、RSI、布林带、均线等指标分析
3. **财务筛选**：净利润连续三年（2023-2025）为正且2026年一季度为正
4. **风险筛查**：剔除ST、财务造假、立案调查等高风险公司
5. **双数据源**：问财API优先，妙想API备选
6. **IMA集成**：自动上传报告到IMA笔记和知识库

### 选股标准

| 指标 | 低位条件 | 得分权重 |
|------|----------|----------|
| KDJ | <20超卖，<30低位 | 15-25分 |
| RSI | <30超卖，<40低位 | 15-25分 |
| MACD | <0底部区域 | 15分 |
| 均线 | 低于60日/20日均线 | 8-20分 |
| 布林带 | 接近下轨 | 15分 |
| 量比 | <0.7缩量企稳 | 10分 |

## 安装

### 依赖

```bash
pip3 install pandas openpyxl --user
```

### 环境变量

```bash
export IWENCAI_API_KEY="your_api_key"
export IMA_OPENAPI_CLIENTID="your_client_id"
export IMA_OPENAPI_APIKEY="your_api_key"
```

### 配置文件（IMA凭证）

```bash
mkdir -p ~/.config/ima
echo "your_client_id" > ~/.config/ima/client_id
echo "your_api_key" > ~/.config/ima/api_key
```

## 使用方法

### 命令行调用

```bash
# 基本用法（生成报告）
python3 scripts/热榜低位选股.py --top 20 --output report --save

# 文本格式输出
python3 scripts/热榜低位选股.py --top 20 --output text

# JSON格式输出
python3 scripts/热榜低位选股.py --top 20 --output json

# 跳过风险检查
python3 scripts/热榜低位选股.py --top 20 --no-risk-check

# 上传到IMA
python3 scripts/上传IMA.py
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --top | 20 | 筛选股票数量 |
| --output | report | 输出格式：report/text/json |
| --save | false | 保存报告到文件 |
| --no-risk-check | false | 跳过风险检查 |

### 输出文件

- `~/.hermes/scripts/stock-research/output/热榜低位选股_YYYYMMDD.md` - Markdown报告
- `~/.hermes/scripts/stock-research/output/热榜低位选股_YYYYMMDD.json` - JSON数据

## 定时任务

使用Hermes Cron设置每日自动执行：

```bash
# 创建定时任务（每个交易日16:00执行）
hermes cron create --name "热榜低位选股" --schedule "0 16 * * 1-5" --deliver qqbot
```

## 技术形态说明

| 形态 | 说明 | 推荐等级 |
|------|------|----------|
| 双重超卖共振 | KDJ+RSI同时超卖 | ⭐⭐⭐ 强烈推荐 |
| KDJ超卖反弹 | KDJ处于超卖区域 | ⭐⭐ 推荐关注 |
| RSI超卖反弹 | RSI处于超卖区域 | ⭐⭐ 推荐关注 |
| 底部蓄势 | MACD底部+远低于60日均线 | ⭐⭐ 推荐关注 |
| 布林下轨支撑 | 股价触及布林带下轨 | ⭐ 可以关注 |
| 缩量筑底 | 缩量+低于60日均线 | ⭐ 可以关注 |

## 操作建议

### 建仓策略

- **得分≥100分**：可考虑分批建仓，仓位建议5-10%
- **得分70-99分**：可小仓位试探，仓位建议3-5%
- **得分50-69分**：建议观望等待更好时机

### 止损建议

- 建议设置5-8%的止损位
- 跌破关键支撑位（如60日均线）及时止损

## 数据来源

- **同花顺问财**（主）：https://www.iwencai.com
- **东方财富妙想**（备）：妙想API

## 风险提示

1. 本报告仅供参考，不构成投资建议
2. 技术低位不代表一定会上涨，需结合基本面综合判断
3. 热度榜股票波动较大，注意控制仓位和风险
4. 投资有风险，入市需谨慎

## 文件结构

```
stock-low-position-selector/
├── SKILL.md                    # 技能说明文档
├── README.md                   # GitHub仓库说明
├── LICENSE                     # MIT许可证
├── scripts/
│   ├── 热榜低位选股.py         # 主选股脚本
│   └── 上传IMA.py              # IMA上传脚本
└── references/
    └── 选股标准.md             # 选股标准详细说明
```

## 更新日志

### v3.0.0 (2026-05-22)
- 新增妙想API作为备选数据源
- 选股范围扩大到热榜前300
- 新增净利润连续三年+一季度为正的筛选条件
- 优化风险筛查逻辑

### v2.0.0 (2026-05-22)
- 新增风险筛查功能
- 集成IMA笔记上传
- 支持添加到知识库

### v1.0.0 (2026-05-22)
- 初始版本
- 基础技术分析功能
- 热榜前100选股

## 许可证

MIT License

## 联系方式

- GitHub: https://github.com/iminddesign
