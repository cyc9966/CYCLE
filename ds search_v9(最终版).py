import requests
import json
import concurrent.futures
from typing import List, Dict, Optional, Tuple
import time
from datetime import datetime, timedelta
import hashlib

# 配置项
API_KEY = "<your key>"
API_URL = "https://api.deepseek.com/v1/chat/completions"

SEARCH_ENGINES = {
    "serpapi": {
        "url": "https://serpapi.com/search",
        "params": {
            "api_key": "<your key>",
            "engine": "google",
            "hl": "en",
            "gl": "us",
            "filter": "0"
        }
    }
}

SEARCH_CACHE = {}
CACHE_EXPIRY = timedelta(hours=1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

messages = [
    {"role": "system", "content": "你是一个有用的AI助手,可以根据用户输入自动生成搜索关键词,并对搜索结果进行总结。现在是2025年。注意不许输出表格,最好分条分析"}
]

def should_trigger_search(user_input: str) -> bool:
    return any(user_input.startswith(trigger) for trigger in ["搜索"])

def get_cache_key(query: str, engine: str) -> str:
    return hashlib.md5(f"{engine}_{query}".encode()).hexdigest()

def check_cache(query: str, engine: str) -> Optional[str]:
    key = get_cache_key(query, engine)
    if key in SEARCH_CACHE:
        cached_time, result = SEARCH_CACHE[key]
        if datetime.now() - cached_time < CACHE_EXPIRY:
            return result
    return None

def add_to_cache(query: str, engine: str, result: str) -> None:
    key = get_cache_key(query, engine)
    SEARCH_CACHE[key] = (datetime.now(), result)

def make_api_request(url: str, headers: dict, data: dict, max_retries: int = 3, timeout: int = 20, stream: bool = False) -> requests.Response:
    last_exception = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=timeout, stream=stream)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(min(2 ** attempt, 5))
    raise last_exception if last_exception else Exception("API请求失败")

def generate_search_keywords(user_input: str) -> List[str]:
    search_content = user_input[2:].strip()
    current_date = datetime.now().strftime('%Y-%m-%d')
    user_prompt = (
        f"当前日期是 {current_date}。请基于这个日期,将以下中文问题转化为3个最相关的搜索关键词,生成最相关的中英文关键词。"
        f"关键词应该是名词短语或专业术语,确保关键词能准确表达原问题的核心内容,只输出关键词列表,不要解释或编号:\n"
        f"{search_content}"
    )
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的搜索关键词生成助手,请将中文问题转化为最适合搜索的三个中文或英文关键词"},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    try:
        resp = make_api_request(API_URL, HEADERS, data)
        content = resp.json()["choices"][0]["message"]["content"]
        keywords = []
        for line in content.splitlines():
            kw = line.strip().strip('"\' ')
            if kw and not kw[0].isdigit():
                keywords.append(kw)
        return keywords[:3] or [search_content]
    except Exception as e:
        print(f"生成关键词失败: {e}")
        return [search_content]

def search_with_engine(query: str, engine: str = "serpapi") -> Tuple[str, str]:
    cached = check_cache(query, engine)
    if cached:
        return engine, cached
    cfg = SEARCH_ENGINES.get(engine)
    if not cfg:
        return engine, f"不支持的搜索引擎: {engine}"
    params = cfg["params"].copy()
    params["q"] = query
    try:
        resp = requests.get(cfg["url"], params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        parsed = parse_serpapi(data)
        if parsed:
            add_to_cache(query, engine, parsed)
        return engine, parsed
    except Exception as e:
        return engine, f"{engine}搜索失败: {e}"

def parse_serpapi(data: Dict) -> str:
    results = {"knowledge_graph": None, "organic_results": [], "related_questions": []}
    if kg := data.get("knowledge_graph"):
        results["knowledge_graph"] = {
            "title": kg.get("title", ""),
            "description": kg.get("description", ""),
            "source": kg.get("source", {}).get("link", "")
        }
    for org in data.get("organic_results", [])[:3]:
        results["organic_results"].append({
            "title": org.get("title", ""),
            "snippet": org.get("snippet", ""),
            "link": org.get("link", "")
        })
    for qa in data.get("related_questions", [])[:2]:
        results["related_questions"].append({
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "link": qa.get("link", "")
        })
    return json.dumps(results, ensure_ascii=False)

def summarize_results(search_terms: List[str], results_list: List[str]) -> None:
    if not results_list:
        print("未找到相关信息")
        return
    prompt = (
        "你是一个专业的信息总结助手,请根据以下搜索关键词和对应的搜索结果,"
        "生成一个简洁、准确的中文总结回答。要求:\n"
        "1. 直接回答问题核心,不要冗余信息\n"
        "2. 包含关键事实和数据\n"
        "3. 注明信息来源\n"
        "4. 如果信息冲突,注明不同观点\n"
        "5. 注意分条分段排列保证可读性\n"
        "6. 格式为:\n"
        "【总结】...\n"
        "【来源】...\n"
        f"搜索关键词: {', '.join(search_terms)}\n\n"
        "搜索结果:\n"
    )
    for i, res in enumerate(results_list, 1):
        try:
            d = json.loads(res)
            prompt += f"\n结果 {i}:\n"
            if kg := d.get("knowledge_graph"):
                prompt += f"知识图谱: {kg['title']} - {kg['description']}\n来源: {kg['source']}\n"
            for org in d.get("organic_results", []):
                prompt += f"网页结果: {org['title']} - {org['snippet']}\n链接: {org['link']}\n"
            for qa in d.get("related_questions", []):
                prompt += f"问答: {qa['question']}\n答案: {qa['answer']}\n链接: {qa['link']}\n"
        except json.JSONDecodeError:
            prompt += f"原始结果: {res[:200]}...\n"

    prompt += f"\n当前日期: {datetime.now().strftime('%Y-%m-%d')}"
    data = {
        "model": "deepseek-chat",
        "messages": messages + [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 2000,
        "stream": True
    }

    try:
        print("")
        reply = ""
        resp = make_api_request(API_URL, HEADERS, data, timeout=30, stream=True)
        for line in resp.iter_lines():
            if not line:
                continue
            d = line.decode("utf-8")
            if d.startswith("data: "):
                js = d[6:].strip()
                if js == "[DONE]":
                    break
                try:
                    chunk = json.loads(js).get("choices", [{}])[0].get("delta", {}).get("content", "")
                    chunk = chunk.replace("*", "").replace("#", "")
                    print(chunk, end="", flush=True)
                    reply += chunk
                except json.JSONDecodeError:
                    continue
        print()
        messages.append({"role": "assistant", "content": reply})
    except Exception as e:
        print(f"总结失败: {e}")
        print("\n无法生成总结,以下是原始搜索结果:")
        for i, res in enumerate(results_list, 1):
            print(f"\n结果 {i}:")
            try:
                d = json.loads(res)
                if kg := d.get("knowledge_graph"):
                    print(f"知识图谱: {kg['title']} - {kg['description']}\n来源: {kg['source']}")
                for org in d.get("organic_results", []):
                    print(f"网页结果: {org['title']}\n摘要: {org['snippet']}\n链接: {org['link']}")
                for qa in d.get("related_questions", []):
                    print(f"问答: {qa['question']}\n答案: {qa['answer']}\n链接: {qa['link']}")
            except json.JSONDecodeError:
                print(res[:500])

def chat_stream(user_input: str) -> None:
    messages.append({"role": "user", "content": user_input})
    if should_trigger_search(user_input):
        print("正在搜索相关信息...")
        terms = generate_search_keywords(user_input)
        print(f"关键词: {', '.join(terms)}")
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as exec:
            futures = [exec.submit(search_with_engine, term) for term in terms]
            for fut in concurrent.futures.as_completed(futures):
                engine, res = fut.result()
                results.append(res)
        summarize_results(terms, results)
    else:
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        try:
            resp = make_api_request(API_URL, HEADERS, data, timeout=30, stream=True)
            print("", end="", flush=True)
            reply = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                d = line.decode("utf-8")
                if d.startswith("data: "):
                    js = d[6:].strip()
                    if js == "[DONE]":
                        break
                    try:
                        chunk = json.loads(js).get("choices", [{}])[0].get("delta", {}).get("content", "")
                        chunk = chunk.replace("#", "").replace("*", "")
                        print(chunk, end="", flush=True)
                        reply += chunk
                    except json.JSONDecodeError:
                        continue
            print()
            messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"聊天失败: {e}")

def main() -> None:
    print("--------------------\nDeepSeek Search")
    while True:
        try:
            inp = input(">>> ").strip()
            if not inp:
                continue
            if inp.lower() in ["再见", "结束", "退出"]:
                print("OVER")
                break
            chat_stream(inp)
        except KeyboardInterrupt:
            print("\n我思故我在")
            break
        except Exception as e:
            print(f"程序异常: {e}")

if __name__ == "__main__":
    main()
