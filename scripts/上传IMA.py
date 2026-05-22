#!/usr/bin/env python3
"""
将选股报告上传到IMA笔记并添加到知识库
"""

import json
import os
import subprocess
import sys
from datetime import datetime

SKILL_DIR = os.path.expanduser("~/.hermes/skills/productivity/ima-skill")


def get_ima_credentials():
    """获取IMA凭证"""
    client_id = os.environ.get("IMA_OPENAPI_CLIENTID", "")
    api_key = os.environ.get("IMA_OPENAPI_APIKEY", "")
    
    if not client_id:
        config_path = os.path.expanduser("~/.config/ima/client_id")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                client_id = f.read().strip()
    
    if not api_key:
        config_path = os.path.expanduser("~/.config/ima/api_key")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                api_key = f.read().strip()
    
    return client_id, api_key


def call_ima_api(api_path, body, client_id, api_key):
    """调用IMA API"""
    opts = json.dumps({"clientId": client_id, "apiKey": api_key})
    body_str = json.dumps(body, ensure_ascii=False)
    
    cmd = [
        "node",
        os.path.join(SKILL_DIR, "ima_api.cjs"),
        api_path,
        body_str,
        opts
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"  API调用失败: {result.stderr[:200]}", file=sys.stderr)
            return None
        
        return json.loads(result.stdout)
    except Exception as e:
        print(f"  API调用异常: {e}", file=sys.stderr)
        return None


def create_note(title, content, client_id, api_key):
    """创建笔记"""
    print(f"📝 正在创建笔记: {title}", file=sys.stderr)
    
    body = {
        "content_format": 1,  # Markdown格式
        "content": f"# {title}\n\n{content}"
    }
    
    result = call_ima_api("openapi/note/v1/import_doc", body, client_id, api_key)
    
    if result and result.get("code") == 0:
        note_id = result.get("data", {}).get("note_id", "")
        print(f"  ✅ 笔记创建成功: {note_id}", file=sys.stderr)
        return note_id
    else:
        print(f"  ❌ 笔记创建失败: {result}", file=sys.stderr)
        return None


def search_knowledge_base(name, client_id, api_key):
    """搜索知识库"""
    print(f"🔍 正在搜索知识库: {name}", file=sys.stderr)
    
    body = {
        "query": name,
        "cursor": "",
        "limit": 20
    }
    
    result = call_ima_api("openapi/wiki/v1/search_knowledge_base", body, client_id, api_key)
    
    if result and result.get("code") == 0:
        # 注意：API返回的字段名是 info_list，不是 items
        items = result.get("data", {}).get("info_list", [])
        for item in items:
            kb_name = item.get("kb_name", "")
            if name in kb_name or kb_name in name:
                kb_id = item.get("kb_id", "")
                print(f"  ✅ 找到知识库: {kb_name} ({kb_id})", file=sys.stderr)
                return kb_id
        
        # 如果没有精确匹配，列出所有知识库
        print(f"  ⚠️ 未找到精确匹配的知识库，可用知识库:", file=sys.stderr)
        for item in items[:5]:
            print(f"    - {item.get('kb_name', '')}", file=sys.stderr)
    
    return None


def add_note_to_knowledge_base(kb_id, note_id, title, client_id, api_key):
    """将笔记添加到知识库"""
    print(f"📚 正在添加到知识库...", file=sys.stderr)
    
    body = {
        "media_type": 11,  # 笔记类型
        "note_info": {
            "content_id": note_id
        },
        "title": title,
        "knowledge_base_id": kb_id
    }
    
    result = call_ima_api("openapi/wiki/v1/add_knowledge", body, client_id, api_key)
    
    if result and result.get("code") == 0:
        print(f"  ✅ 已添加到知识库", file=sys.stderr)
        return True
    else:
        print(f"  ❌ 添加失败: {result}", file=sys.stderr)
        return False


def main():
    # 获取凭证
    client_id, api_key = get_ima_credentials()
    
    if not client_id or not api_key:
        print("❌ IMA凭证未配置", file=sys.stderr)
        sys.exit(1)
    
    # 读取报告
    today = datetime.now().strftime("%Y%m%d")
    report_path = os.path.expanduser(f"~/.hermes/scripts/stock-research/output/热榜低位选股_{today}.md")
    
    if not os.path.exists(report_path):
        print(f"❌ 报告文件不存在: {report_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 创建笔记
    title = f"A股热榜低位选股_{today}"
    note_id = create_note(title, content, client_id, api_key)
    
    if not note_id:
        sys.exit(1)
    
    # 搜索知识库
    kb_name = "选股"
    kb_id = search_knowledge_base(kb_name, client_id, api_key)
    
    if kb_id:
        # 添加到知识库
        success = add_note_to_knowledge_base(kb_id, note_id, title, client_id, api_key)
        if success:
            print(f"\n✅ 完成！笔记已添加到知识库「{kb_name}」", file=sys.stderr)
        else:
            print(f"\n⚠️ 笔记已创建但添加到知识库失败", file=sys.stderr)
    else:
        print(f"\n⚠️ 未找到知识库「{kb_name}」，笔记已创建但未添加到知识库", file=sys.stderr)
        print(f"   请在IMA中创建名为「{kb_name}」的知识库后重试", file=sys.stderr)
    
    print(f"\n📄 笔记ID: {note_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
