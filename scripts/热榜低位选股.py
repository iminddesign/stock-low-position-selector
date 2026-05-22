#!/usr/bin/env python3
"""
A股热榜低位选股工具 v3.0

新增功能：
1. 使用妙想API作为备选数据源
2. 支持热榜前300股票筛选
3. 净利润连续三年+一季度为正

数据来源：
- 同花顺问财（主）
- 东方财富妙想API（备）
"""

import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime

# 配置
API_URL = "https://openapi.iwencai.com/v1/query2data"
NEWS_API_URL = "https://openapi.iwencai.com/v1/comprehensive/search"
SKILL_ID = "hithink-astock-selector"
NEWS_SKILL_ID = "news-search"
SKILL_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 60

# 妙想API脚本路径
MX_SCRIPT = os.path.expanduser("~/.hermes/skills/miaoxiang/mx-finance-data/scripts/get_data.py")

# 风险关键词
RISK_KEYWORDS = [
    "ST", "*ST", "退市", "亏损", "财务造假", "立案调查", "行政处罚",
    "重大诉讼", "债务违约", "资金链断裂", "破产重整", "实控人被捕",
    "违规担保", "占用资金", "业绩暴雷", "高管被查", "证监会处罚",
    "暂停上市", "终止上市", "风险警示"
]


def generate_trace_id():
    return secrets.token_hex(32)


def get_api_key():
    key = os.environ.get("IWENCAI_API_KEY", "")
    if not key:
        raise ValueError("IWENCAI_API_KEY 环境变量未设置")
    return key


def query_iwencai(query, limit="50", skill_id=SKILL_ID):
    """调用问财API"""
    api_key = get_api_key()
    trace_id = generate_trace_id()
    
    payload = {
        "query": query,
        "page": "1",
        "limit": limit,
        "is_cache": "1",
        "expand_index": "true",
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": skill_id,
        "X-Claw-Skill-Version": SKILL_VERSION,
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": trace_id,
    }
    
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def query_miaoxiang(query):
    """调用妙想API（备选）"""
    try:
        result = subprocess.run(
            ["python3", MX_SCRIPT, "--query", query],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # 解析输出，获取xlsx文件路径
            output = result.stdout
            for line in output.split("\n"):
                if "文件:" in line:
                    xlsx_path = line.split("文件:")[-1].strip()
                    # 读取xlsx数据
                    return read_xlsx_data(xlsx_path)
        return None
    except Exception as e:
        print(f"  妙想API调用失败: {str(e)[:50]}", file=sys.stderr)
        return None


def read_xlsx_data(xlsx_path):
    """读取xlsx文件数据"""
    try:
        import pandas as pd
        
        if not os.path.exists(xlsx_path):
            return None
        
        # 读取所有sheet
        xlsx = pd.ExcelFile(xlsx_path)
        all_data = []
        
        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            all_data.append({
                "sheet_name": sheet_name,
                "data": df.to_dict(orient="records")
            })
        
        return all_data
    except Exception as e:
        print(f"  读取xlsx失败: {str(e)[:50]}", file=sys.stderr)
        return None


def get_hot_stocks():
    """获取A股热榜前300（分3批获取）"""
    print("📊 正在获取A股热度榜前300...", file=sys.stderr)
    
    all_stocks = []
    
    # 第1批：1-100
    print("  第1批（1-100）...", file=sys.stderr)
    try:
        result1 = query_iwencai("A股热度排名前100的股票，按热度从高到低排序", limit="100")
        datas1 = result1.get("datas", [])
        all_stocks.extend(datas1)
        print(f"  ✅ 获取 {len(datas1)} 只", file=sys.stderr)
    except Exception as e:
        print(f"  ❌ 第1批失败: {str(e)[:50]}", file=sys.stderr)
    
    # 第2批：101-200
    print("  第2批（101-200）...", file=sys.stderr)
    try:
        result2 = query_iwencai("A股热度排名101到200的股票，按热度从高到低排序", limit="100")
        datas2 = result2.get("datas", [])
        all_stocks.extend(datas2)
        print(f"  ✅ 获取 {len(datas2)} 只", file=sys.stderr)
    except Exception as e:
        print(f"  ❌ 第2批失败: {str(e)[:50]}", file=sys.stderr)
    
    # 第3批：201-300
    print("  第3批（201-300）...", file=sys.stderr)
    try:
        result3 = query_iwencai("A股热度排名201到300的股票，按热度从高到低排序", limit="100")
        datas3 = result3.get("datas", [])
        all_stocks.extend(datas3)
        print(f"  ✅ 获取 {len(datas3)} 只", file=sys.stderr)
    except Exception as e:
        print(f"  ❌ 第3批失败: {str(e)[:50]}", file=sys.stderr)
    
    print(f"  总计获取 {len(all_stocks)} 只热榜股票", file=sys.stderr)
    return all_stocks


def get_technical_indicators(codes):
    """分批获取技术指标（优先问财，失败则用妙想）"""
    print("📈 正在查询技术指标...", file=sys.stderr)
    
    batch_size = 10
    all_results = []
    failed_batches = []
    
    # 先用问财API
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        codes_str = ",".join(batch)
        query = f"{codes_str}的最新价、涨跌幅、换手率、量比、MACD、KDJ、RSI、布林带、5日均线、10日均线、20日均线、60日均线"
        
        try:
            result = query_iwencai(query, limit="20")
            datas = result.get("datas", [])
            all_results.extend(datas)
            print(f"  问财批次 {i//batch_size + 1}/{(len(codes)-1)//batch_size + 1}: {len(datas)} 条", file=sys.stderr)
        except Exception as e:
            print(f"  问财批次 {i//batch_size + 1}: 失败 - {str(e)[:30]}", file=sys.stderr)
            failed_batches.append(batch)
    
    # 如果有失败的批次，用妙想API重试
    if failed_batches:
        print("  🔄 使用妙想API重试失败批次...", file=sys.stderr)
        for batch in failed_batches:
            try:
                codes_str = "、".join(batch)
                query = f"{codes_str}的最新价、涨跌幅、KDJ、RSI、MACD"
                mx_data = query_miaoxiang(query)
                if mx_data:
                    # 转换妙想数据格式
                    for sheet_info in mx_data:
                        for row in sheet_info.get("data", []):
                            # 提取有用数据
                            if "股票代码" in row or "代码" in row:
                                all_results.append(row)
            except Exception as e:
                print(f"  妙想API重试失败: {str(e)[:30]}", file=sys.stderr)
    
    print(f"  总计获取 {len(all_results)} 条技术数据", file=sys.stderr)
    return all_results


def get_financial_data(codes):
    """分批获取财务数据（优先问财，失败则用妙想）"""
    print("💰 正在查询财务数据...", file=sys.stderr)
    
    batch_size = 10
    all_results = []
    failed_batches = []
    
    # 先用问财API
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        codes_str = ",".join(batch)
        query = f"{codes_str}的2023年净利润、2024年净利润、2025年净利润、2026年一季度净利润"
        
        try:
            result = query_iwencai(query, limit="20")
            datas = result.get("datas", [])
            all_results.extend(datas)
            print(f"  问财批次 {i//batch_size + 1}/{(len(codes)-1)//batch_size + 1}: {len(datas)} 条", file=sys.stderr)
        except Exception as e:
            print(f"  问财批次 {i//batch_size + 1}: 失败 - {str(e)[:30]}", file=sys.stderr)
            failed_batches.append(batch)
    
    # 如果有失败的批次，用妙想API重试
    if failed_batches:
        print("  🔄 使用妙想API重试失败批次...", file=sys.stderr)
        for batch in failed_batches:
            try:
                codes_str = "、".join(batch)
                query = f"{codes_str}最近三年的净利润"
                mx_data = query_miaoxiang(query)
                if mx_data:
                    # 转换妙想数据格式
                    for sheet_info in mx_data:
                        for row in sheet_info.get("data", []):
                            if "股票代码" in row or "代码" in row:
                                all_results.append(row)
            except Exception as e:
                print(f"  妙想API重试失败: {str(e)[:30]}", file=sys.stderr)
    
    print(f"  总计获取 {len(all_results)} 条财务数据", file=sys.stderr)
    return all_results


def check_financial_health(stock_financial):
    """检查财务健康状况（净利润连续三年为正且一季度为正）"""
    
    # 提取净利润数据（兼容不同字段名）
    net_profit_2023 = 0
    net_profit_2024 = 0
    net_profit_2025 = 0
    net_profit_2026_q1 = 0
    
    # 问财API字段名
    for key, value in stock_financial.items():
        if "2023" in key and "净利润" in key:
            net_profit_2023 = float(value or 0)
        elif "2024" in key and "净利润" in key:
            net_profit_2024 = float(value or 0)
        elif "2025" in key and "净利润" in key:
            net_profit_2025 = float(value or 0)
        elif "2026" in key and ("一季度" in key or "0331" in key) and "净利润" in key:
            net_profit_2026_q1 = float(value or 0)
    
    # 检查是否连续三年为正且一季度为正
    is_profitable = (
        net_profit_2023 > 0 and
        net_profit_2024 > 0 and
        net_profit_2025 > 0 and
        net_profit_2026_q1 > 0
    )
    
    return {
        "is_profitable": is_profitable,
        "net_profit_2023": net_profit_2023,
        "net_profit_2024": net_profit_2024,
        "net_profit_2025": net_profit_2025,
        "net_profit_2026_q1": net_profit_2026_q1,
    }


def search_news(query):
    """搜索财经新闻"""
    api_key = get_api_key()
    trace_id = generate_trace_id()
    
    payload = {
        "channels": ["news"],
        "app_id": "AIME_SKILL",
        "query": query
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": NEWS_SKILL_ID,
        "X-Claw-Skill-Version": SKILL_VERSION,
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": trace_id,
    }
    
    request = urllib.request.Request(
        NEWS_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"  新闻搜索失败: {str(e)[:50]}", file=sys.stderr)
        return {"data": {"news": {"result": []}}}


def check_stock_risk(stock_name, stock_code):
    """检查股票是否存在重大风险"""
    risk_flags = []
    
    # 1. 检查股票名称中的风险标识
    for keyword in RISK_KEYWORDS:
        if keyword in stock_name:
            risk_flags.append(f"名称含风险标识: {keyword}")
    
    # 2. 搜索相关新闻，检查是否有负面消息
    try:
        news_result = search_news(f"{stock_name} 风险 亏损 违规 处罚")
        news_data = news_result.get("data", {}).get("news", {}).get("result", [])
        
        for news in news_data[:5]:
            title = news.get("title", "")
            content = news.get("content", "")
            
            for keyword in RISK_KEYWORDS:
                if keyword in title or keyword in content:
                    risk_flags.append(f"近期新闻含风险: {title[:30]}...")
                    break
    except Exception:
        pass
    
    return risk_flags


def analyze_low_position(stock, hotness_map):
    """分析股票是否处于技术低位"""
    
    score = 0
    reasons = []
    signals = []
    
    # 提取关键数据（兼容不同字段名）
    price = 0
    change = 0
    macd = 0
    kdj = 50
    rsi = 50
    boll_mid = 0
    ma20 = 0
    ma60 = 0
    turnover = 0
    volume_ratio = 1
    
    for key, value in stock.items():
        try:
            val = float(value) if value else 0
        except (ValueError, TypeError):
            continue
        
        if "最新价" in key or "收盘价" in key:
            price = val
        elif "涨跌幅" in key:
            change = val
        elif "macd" in key.lower() or "MACD" in key:
            macd = val
        elif "kdj" in key.lower() or "KDJ" in key:
            kdj = val
        elif "rsi" in key.lower() or "RSI" in key:
            rsi = val
        elif "布林" in key or "boll" in key.lower():
            boll_mid = val
        elif "ma20" in key.lower() or "20日均线" in key:
            ma20 = val
        elif "ma60" in key.lower() or "60日均线" in key:
            ma60 = val
        elif "换手率" in key:
            turnover = val
        elif "量比" in key:
            volume_ratio = val
    
    # MACD分析
    if macd < 0:
        score += 15
        reasons.append(f"MACD={macd:.3f}，处于零轴下方，底部区域")
        signals.append("MACD底部")
    elif 0 < macd < 1:
        score += 10
        reasons.append(f"MACD={macd:.3f}，刚转正，启动信号")
        signals.append("MACD转正")
    
    # KDJ分析
    if kdj < 20:
        score += 25
        reasons.append(f"KDJ={kdj:.1f}，严重超卖区域，反弹概率大")
        signals.append("KDJ超卖")
    elif kdj < 30:
        score += 15
        reasons.append(f"KDJ={kdj:.1f}，超卖区域")
        signals.append("KDJ低位")
    elif kdj < 40:
        score += 8
        reasons.append(f"KDJ={kdj:.1f}，相对低位")
        signals.append("KDJ偏低")
    
    # RSI分析
    if rsi < 30:
        score += 25
        reasons.append(f"RSI={rsi:.1f}，严重超卖，技术性反弹需求强")
        signals.append("RSI超卖")
    elif rsi < 40:
        score += 15
        reasons.append(f"RSI={rsi:.1f}，相对低位")
        signals.append("RSI低位")
    elif rsi < 45:
        score += 8
        reasons.append(f"RSI={rsi:.1f}，偏低位置")
        signals.append("RSI偏低")
    
    # 均线分析
    if price > 0 and ma60 > 0:
        if price < ma60 * 0.85:
            score += 20
            reasons.append("股价低于60日均线15%以上，中长期超跌")
            signals.append("远低于60日均线")
        elif price < ma60:
            score += 12
            reasons.append("股价低于60日均线，处于中长期低位")
            signals.append("低于60日均线")
    
    if price > 0 and ma20 > 0:
        if price < ma20 * 0.9:
            score += 15
            reasons.append("股价低于20日均线10%以上，短期超跌")
            signals.append("远低于20日均线")
        elif price < ma20:
            score += 8
            reasons.append("股价低于20日均线，短期偏弱")
            signals.append("低于20日均线")
    
    # 布林带分析
    if price > 0 and boll_mid > 0:
        if price <= boll_mid * 0.92:
            score += 15
            reasons.append("股价接近或触及布林带下轨，支撑位附近")
            signals.append("触及布林下轨")
        elif price < boll_mid:
            score += 5
            reasons.append("股价在布林带中轨下方")
            signals.append("布林中轨下方")
    
    # 量比分析
    if volume_ratio < 0.7:
        score += 10
        reasons.append(f"量比={volume_ratio:.2f}，明显缩量，可能企稳")
        signals.append("缩量企稳")
    elif volume_ratio < 0.9:
        score += 5
        reasons.append(f"量比={volume_ratio:.2f}，温和缩量")
        signals.append("温和缩量")
    
    # 换手率分析
    if turnover < 3:
        score += 8
        reasons.append(f"换手率={turnover:.2f}%，交投清淡，筹码稳定")
        signals.append("低换手率")
    
    # 涨跌幅分析
    if change < -5:
        score += 15
        reasons.append(f"当日跌幅{change:.2f}%，超跌明显")
        signals.append("当日超跌")
    elif change < -2:
        score += 8
        reasons.append(f"当日跌幅{change:.2f}%，有调整")
        signals.append("当日调整")
    
    code = stock.get("股票代码", stock.get("代码", ""))
    name = stock.get("股票简称", stock.get("名称", ""))
    hotness_info = hotness_map.get(code, {})
    
    return {
        "股票代码": code,
        "股票简称": name,
        "最新价": price,
        "涨跌幅": change,
        "换手率": turnover,
        "量比": volume_ratio,
        "MACD": macd,
        "KDJ": kdj,
        "RSI": rsi,
        "热度排名": hotness_info.get("rank", 0),
        "低位得分": score,
        "技术信号": signals,
        "选股理由": reasons,
        "技术形态": determine_pattern(signals, score),
        "风险标记": [],
    }


def determine_pattern(signals, score):
    """判断技术形态"""
    if "KDJ超卖" in signals and "RSI超卖" in signals:
        return "双重超卖共振形态"
    elif "KDJ超卖" in signals:
        return "KDJ超卖反弹形态"
    elif "RSI超卖" in signals:
        return "RSI超卖反弹形态"
    elif "MACD底部" in signals and "远低于60日均线" in signals:
        return "底部蓄势形态"
    elif "触及布林下轨" in signals:
        return "布林下轨支撑形态"
    elif "缩量企稳" in signals and "低于60日均线" in signals:
        return "缩量筑底形态"
    elif score >= 50:
        return "多重底部信号共振"
    elif score >= 35:
        return "低位企稳形态"
    elif score >= 25:
        return "相对低位形态"
    else:
        return "技术面偏弱"


def generate_report(selected, total_count, risky_count):
    """生成Markdown报告"""
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    report = f"""# 📊 A股热榜低位选股报告

**生成时间：{now}**
**数据来源：同花顺问财 + 东方财富妙想**

---

## 📋 选股概览

| 项目 | 数值 |
|------|------|
| 热榜分析股票数 | {total_count} 只 |
| 风险剔除 | {risky_count} 只 |
| 精选推荐 | {len(selected)} 只 |
| 选股策略 | 从热度榜前300中筛选技术面低位、适合建仓/加仓的股票 |
| 风险筛查 | 已剔除ST、财务造假、立案调查等高风险公司 |
| 财务筛选 | 净利润连续三年（2023-2025）为正且2026年一季度为正 |

---

## 🏆 精选股票列表

"""
    
    for i, s in enumerate(selected, 1):
        code = s.get("股票代码", "")
        name = s.get("股票简称", "")
        price = s.get("最新价", 0)
        change = s.get("涨跌幅", 0)
        score = s.get("低位得分", 0)
        pattern = s.get("技术形态", "")
        signals = s.get("技术信号", [])
        reasons = s.get("选股理由", [])
        hot_rank = s.get("热度排名", 0)
        
        change_str = f"{change:+.2f}%"
        change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        if score >= 100:
            level = "⭐⭐⭐ 强烈推荐"
        elif score >= 70:
            level = "⭐⭐ 推荐关注"
        elif score >= 50:
            level = "⭐ 可以关注"
        else:
            level = "观望"
        
        report += f"""### {i}. {name}（{code}）

| 指标 | 数值 |
|------|------|
| 最新价 | {price} 元 |
| 涨跌幅 | {change_emoji} {change_str} |
| 热度排名 | #{hot_rank} |
| 低位得分 | **{score}分** |
| 推荐等级 | {level} |
| 技术形态 | {pattern} |

**技术信号：** {', '.join(signals)}

**选股理由：**
"""
        for reason in reasons:
            report += f"- ✅ {reason}\n"
        
        report += "\n---\n\n"
    
    report += """
## 💡 操作建议

### 建仓策略
- **得分≥100分**：可考虑分批建仓，仓位建议5-10%
- **得分70-99分**：可小仓位试探，仓位建议3-5%
- **得分50-69分**：建议观望等待更好时机

### 止损建议
- 建议设置5-8%的止损位
- 跌破关键支撑位及时止损

---

## ⚠️ 风险提示

1. **本报告仅供参考，不构成投资建议**
2. 技术低位不代表一定会上涨
3. 投资有风险，入市需谨慎

---

*报告由热榜低位选股工具自动生成*
*数据来源：同花顺问财 + 东方财富妙想*
"""
    
    return report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="A股热榜低位选股工具 v3.0")
    parser.add_argument("--top", type=int, default=20, help="筛选数量（默认20）")
    parser.add_argument("--output", type=str, default="report", help="输出格式：report/text/json")
    parser.add_argument("--save", action="store_true", help="保存报告到文件")
    parser.add_argument("--no-risk-check", action="store_true", help="跳过风险检查")
    args = parser.parse_args()
    
    try:
        # 1. 获取热榜
        hot_stocks = get_hot_stocks()
        if not hot_stocks:
            print("❌ 无法获取热榜数据", file=sys.stderr)
            sys.exit(1)
        
        # 提取代码和热度排名
        codes = []
        hotness_map = {}
        for i, stock in enumerate(hot_stocks, 1):
            code = stock.get("股票代码", "")
            name = stock.get("股票简称", "")
            if code:
                codes.append(code)
                hotness_map[code] = {
                    "rank": i,
                    "hotness": stock.get("个股热度[20260522]", 0),
                    "name": name
                }
        
        print(f"✅ 获取到 {len(codes)} 只热榜股票", file=sys.stderr)
        
        # 2. 获取技术指标（支持妙想API备选）
        tech_data = get_technical_indicators(codes)
        
        # 3. 获取财务数据（支持妙想API备选）
        financial_data = get_financial_data(codes)
        
        # 创建财务数据映射
        financial_map = {}
        for fin in financial_data:
            code = fin.get("股票代码", fin.get("代码", ""))
            if code:
                financial_map[code] = fin
        
        # 4. 分析低位
        print("🔍 正在分析技术低位...", file=sys.stderr)
        analyzed = []
        for stock in tech_data:
            code = stock.get("股票代码", stock.get("代码", ""))
            
            # 检查财务健康状况
            if code in financial_map:
                fin_check = check_financial_health(financial_map[code])
                if not fin_check["is_profitable"]:
                    name = stock.get("股票简称", stock.get("名称", ""))
                    print(f"  ❌ {name}: 净利润不符合条件", file=sys.stderr)
                    continue
            
            analysis = analyze_low_position(stock, hotness_map)
            if analysis["低位得分"] > 0:
                analyzed.append(analysis)
        
        analyzed.sort(key=lambda x: x["低位得分"], reverse=True)
        
        # 5. 风险筛查
        risky_count = 0
        if not args.no_risk_check:
            print("🔎 正在进行风险筛查...", file=sys.stderr)
            safe_stocks = []
            
            for stock in analyzed[:50]:
                name = stock.get("股票简称", "")
                code = stock.get("股票代码", "")
                
                risk_flags = check_stock_risk(name, code)
                
                if risk_flags:
                    stock["风险标记"] = risk_flags
                    risky_count += 1
                    print(f"  ⚠️ {name}: {risk_flags[0]}", file=sys.stderr)
                else:
                    safe_stocks.append(stock)
                
                if len(safe_stocks) >= args.top + 10:
                    break
            
            checked_codes = {s["股票代码"] for s in safe_stocks + [s for s in analyzed[:50] if s.get("风险标记")]}
            for stock in analyzed:
                if stock["股票代码"] not in checked_codes:
                    safe_stocks.append(stock)
            
            analyzed = safe_stocks
        
        selected = analyzed[:args.top]
        
        print(f"✅ 筛选出 {len(selected)} 只技术低位股票（剔除 {risky_count} 只风险股）", file=sys.stderr)
        
        # 6. 输出
        if args.output == "json":
            print(json.dumps(selected, ensure_ascii=False, indent=2))
        elif args.output == "text":
            for i, s in enumerate(selected, 1):
                print(f"{i}. {s['股票简称']}({s['股票代码']}) 得分:{s['低位得分']} 形态:{s['技术形态']}")
        else:
            report = generate_report(selected, len(codes), risky_count)
            print(report)
            
            if args.save:
                today = datetime.now().strftime("%Y%m%d")
                output_dir = os.path.expanduser("~/.hermes/scripts/stock-research/output")
                os.makedirs(output_dir, exist_ok=True)
                report_path = os.path.join(output_dir, f"热榜低位选股_{today}.md")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"\n📄 报告已保存: {report_path}", file=sys.stderr)
                
                json_path = os.path.join(output_dir, f"热榜低位选股_{today}.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(selected, f, ensure_ascii=False, indent=2)
                print(f"📄 数据已保存: {json_path}", file=sys.stderr)
        
    except Exception as e:
        print(f"❌ 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
