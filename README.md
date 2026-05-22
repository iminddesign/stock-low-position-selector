# A股热榜低位选股工具

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/iminddesign/stock-low-position-selector)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

从A股热度人气榜前300名中，筛选技术面处于低位、适合建仓/加仓的股票。

## ✨ 功能特点

- 📊 **热榜前300**：分3批获取热度最高的300只股票
- 📈 **技术分析**：MACD、KDJ、RSI、布林带、均线等指标综合评分
- 💰 **财务筛选**：净利润连续三年+一季度为正
- 🔍 **风险筛查**：自动剔除ST、财务造假等高风险公司
- 🔄 **双数据源**：问财API优先，妙想API备选
- 📝 **IMA集成**：自动上传报告到IMA笔记和知识库

## 🚀 快速开始

### 安装依赖

```bash
pip3 install pandas openpyxl --user
```

### 配置API密钥

```bash
# 问财API
export IWENCAI_API_KEY="your_api_key"

# IMA API（可选）
mkdir -p ~/.config/ima
echo "your_client_id" > ~/.config/ima/client_id
echo "your_api_key" > ~/.config/ima/api_key
```

### 运行选股

```bash
python3 scripts/热榜低位选股.py --top 20 --output report --save
```

## 📊 选股标准

| 指标 | 低位条件 | 得分 |
|------|----------|------|
| KDJ | <20超卖 | 25分 |
| RSI | <30超卖 | 25分 |
| MACD | <0底部 | 15分 |
| 均线 | 低于60日均线 | 12-20分 |
| 布林带 | 接近下轨 | 15分 |
| 量比 | <0.7缩量 | 10分 |

## 📁 输出示例

```
📊 正在获取A股热度榜前300...
  ✅ 第1批获取 100 只
  ✅ 第2批获取 100 只
  ✅ 第3批获取 100 只
💰 正在查询财务数据...
🔍 正在分析技术低位...
✅ 筛选出 20 只技术低位股票

1. 紫金矿业(601899.SH) 得分:93 形态:KDJ超卖反弹
2. 金风科技(002202.SZ) 得分:85 形态:KDJ超卖反弹
3. 金螳螂(002081.SZ) 得分:78 形态:KDJ超卖反弹
...
```

## ⏰ 定时任务

```bash
# 使用Hermes Cron设置每日自动执行
hermes cron create --name "热榜低位选股" --schedule "0 16 * * 1-5" --deliver qqbot
```

## 📖 详细文档

详见 [SKILL.md](SKILL.md)

## ⚠️ 风险提示

**本工具仅供学习研究使用，不构成任何投资建议。**

- 技术分析仅供参考，不保证收益
- 投资有风险，入市需谨慎
- 请根据自身风险承受能力做出投资决策

## 📄 许可证

[MIT License](LICENSE)

## 👤 作者

**imeiming** - [GitHub](https://github.com/iminddesign)

## 🔗 相关项目

- [Hermes Agent](https://github.com/nousresearch/hermes-agent) - AI助手框架
- [同花顺问财](https://www.iwencai.com) - 金融数据API
- [东方财富妙想](https://miaoxiang.eastmoney.com) - 金融数据API
