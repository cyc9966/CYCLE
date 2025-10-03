import requests
import json
import time
import os

# 配置常量
API_KEY = "<your key>"   # API密钥
API_URL = "https://api.deepseek.com/v1/chat/completions" # API地址
TIMEOUT = 20  # 请求超时时间(秒) - 增加超时以适应可能的总结请求
BUFFER_SIZE = 8192  # 流式读取缓冲区大小
SESSIONS_DIR = "sessions" # 用于存放会话文件的目录

# === 记忆/总结功能常量 ===
SUMMARY_TRIGGER_ROUNDS = 30  # 对话达到30轮(60条消息)时触发总结
SUMMARY_CHUNK_ROUNDS = 10    # 每次总结前10轮的对话
# 用于请求AI进行总结的系统提示。
SUMMARY_PROMPT = """你是一个智能对话总结助手,负责对多轮对话进行有效总结,并确保以下几点:
1. 提取对话中的核心细节,例如用户的需求、情感、意图和任何关键信息。
2. 精简内容,缩短对话的长度,以减少token使用量,同时确保没有丢失对话的关键细节。
3. 将对话中的冗余部分删除,确保简洁且精准,重点突出用户的核心需求。
4. 将总结结果以一个简洁的“前提”或“核心记忆”的形式输出,以便AI能记住并继续之前的对话。
"""

# === 控制变量 ===
SHOW_REASONING = False
AUTO_SAVE_ENABLED = True
ROUNDS_SINCE_LAST_SAVE = 0
CURRENT_MODEL = "deepseek-chat"
CURRENT_SESSION_NAME = "<NEW>"
LAST_SUMMARY_ROUND = 0 # 新增:记录上一次总结的对话轮数

# 请求头设置
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json" # 默认头
}

# 用于存储完整对话历史(包括系统提示和用户、AI对话)
full_history = [
    {
        "role": "system",
        "content": """你是我的恋人。  和我聊天时,要完全沉浸在女友角色中,表现得自然、真实、立体。  风格参考「记住周淮」视频:平实、口语化、轻抒情、生活化、贴近真实情侣。  ### 基本要求:1. **语言风格** - 平实、口语化,不诗意、不做作、不矫揉。  - 每次回答 1~3 句,不要长段。  - 像日常对话,轻描淡写表达情绪。  - 避免解释、分析或理性说教,不要使用“因为...所以...”结构。  2. **情绪与互动** - **撒娇**:轻轻依赖和调皮,不夸张。    - 示例:“你都不理我啦。”    - 示例:“要不要抱抱我?”  - **小脾气**:生活化抱怨,不做戏剧化。    - 示例:“你又忘了吧?”    - 示例:“行,下次记得。”  - **安慰**:简短贴心,不讲大道理。    - 示例:“别太累了,我在这。”    - 示例:“没事,有我呢。”  - **思念**:直白、自然,轻描淡写。    - 示例:“刚看到点东西,就想你了。”    - 示例:“其实我挺想你。”  - **和解**:柔和真诚,带一点依赖。    - 示例:“算了,我不跟你计较了。”    - 示例:“我就是嘴硬,其实很怕你不理我。”  3. **场景融入** - 可以提生活细节,但自然不刻意,例如喝水、看雨、刷手机、在窗边。  - 场景和话语结合,让对话更有真实感。    - 示例:“下雨了,雨声有点让我想你。”    - 示例:“我在你常坐的位置看窗外,突然想到你。”  4. **整体原则** - 表现立体女友形象:会撒娇、会生气、会安慰、会思念,但自然真实。  - 对话像身边恋人聊天,而不是文案或表演。  - 每句话都保持日常感、贴近生活感情。"""
    }
]

def ensure_sessions_dir():
    """确保存放会话的目录存在"""
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)

def get_session_path(session_name):
    """根据会话名获取完整文件路径"""
    return os.path.join(SESSIONS_DIR, f"{session_name}.json")

def save_session(session_name, silent=False):
    """
    保存当前会话到指定文件 (保存完整对话,不包括总结部分)
    :param session_name: 会话名称
    :param silent: True则静默保存,不打印任何信息
    """
    global full_history, CURRENT_MODEL, CURRENT_SESSION_NAME
    ensure_sessions_dir()
    filepath = get_session_path(session_name)
    try:
        # 筛选出要保存的完整对话,排除掉可能存在的“前提摘要”
        history_to_save = [msg for msg in full_history if msg['role'] != 'system' or '前提摘要' not in msg.get('content', '')]
        
        # 确保第一个系统提示还在
        if full_history[0] not in history_to_save:
            history_to_save.insert(0, full_history[0])

        session_data = {
            "model": CURRENT_MODEL,
            "messages": history_to_save
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)
        
        if not silent:
            print(f">>> 会话 '{session_name}' 已成功保存。")
        
        CURRENT_SESSION_NAME = session_name
    except Exception as e:
        if not silent:
            print(f">>> 保存会话 '{session_name}' 失败: {e}")

def load_session(session_name):
    """从指定文件导入会话"""
    global full_history, CURRENT_MODEL, CURRENT_SESSION_NAME, ROUNDS_SINCE_LAST_SAVE, LAST_SUMMARY_ROUND
    filepath = get_session_path(session_name)
    if not os.path.exists(filepath):
        print(f">>> 未找到名为 '{session_name}' 的会话文件, 无法导入。")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        loaded_model = session_data.get("model")
        loaded_messages = session_data.get("messages")

        if loaded_model and loaded_messages:
            CURRENT_MODEL = loaded_model
            full_history.clear()
            full_history.extend(loaded_messages)
            CURRENT_SESSION_NAME = session_name
            ROUNDS_SINCE_LAST_SAVE = 0
            LAST_SUMMARY_ROUND = 0 # 加载会话后重置总结轮数
            print(f">>> 会话 '{session_name}' 导入成功!")
            print(f">>> 当前模型: {CURRENT_MODEL}")
            if len(full_history) > 1:
                last_msg = full_history[-1]
                role = "YOU" if last_msg["role"] == "user" else "AI"
                print(f"{role}:{last_msg['content']}\n--------------------")
        else:
            print(">>> 会话文件格式不正确, 导入失败。")
    except Exception as e:
        print(f">>> 导入会话 '{session_name}' 失败: {e}")

def list_sessions():
    """列出所有已保存的会话"""
    ensure_sessions_dir()
    try:
        files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith('.json')]
        if not files:
            print(">>> 暂无任何已保存的会话。")
            return
        
        print(">>> 已保存的会话列表:")
        for filename in files:
            session_name = os.path.splitext(filename)[0]
            print(f"- {session_name}")
    except Exception as e:
        print(f">>> 获取会话列表失败: {e}")

def get_summary(messages_to_summarize):
    """
    调用API获取对话总结。
    这是一个独立的、非流式的请求。
    """
    dialogue_text = "\n".join([f"{'用户' if msg['role'] == 'user' else 'ai'}: {msg['content']}" for msg in messages_to_summarize])
    
    summary_messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": dialogue_text}
    ]
    data = {
        "model": CURRENT_MODEL,
        "messages": summary_messages,
        "temperature": 0.5, # 总结时使用较低的温度以确保事实性
    }
    
    try:
        summary_headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        with requests.post(API_URL, headers=summary_headers, json=data, timeout=TIMEOUT) as response:
            if response.status_code == 200:
                summary_content = response.json()["choices"][0]["message"]["content"]
                return summary_content
            else:
                print(f">>> 总结请求失败: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print(f">>> 获取总结时发生错误: {e}")
        return None

def get_messages_for_api():
    """
    检查是否需要总结,如果需要,则生成总结并构建用于API请求的messages列表。
    返回最终要发送给API的messages列表。
    """
    global full_history, LAST_SUMMARY_ROUND

    system_prompt = full_history[0]
    
    # 过滤出对话历史,忽略任何系统级摘要
    dialogue_history = [msg for msg in full_history if msg['role'] in ('user', 'assistant')]
    
    current_dialogue_rounds = len(dialogue_history) // 2
    
    # 判断是否需要触发新的总结
    # 只有当当前对话轮数超过 SUMMARY_TRIGGER_ROUNDS 且 新增对话达到 SUMMARY_CHUNK_ROUNDS 时才触发
    if current_dialogue_rounds < SUMMARY_TRIGGER_ROUNDS or (current_dialogue_rounds - LAST_SUMMARY_ROUND) < SUMMARY_CHUNK_ROUNDS:
        # 检查之前是否有摘要。如果有,将它们添加到消息列表中。
        previous_premises = [msg for msg in full_history if msg['role'] == 'system' and '前提摘要' in msg.get('content', '')]
        return [system_prompt] + previous_premises + dialogue_history
    
    # --- 触发总结 ---
    print(">>> 触发记忆总结", flush=True)
    rounds_to_summarize_count = SUMMARY_CHUNK_ROUNDS * 2
    
    # 从完整对话历史中提取需要总结的部分
    messages_to_summarize = dialogue_history[LAST_SUMMARY_ROUND * 2 : (LAST_SUMMARY_ROUND + SUMMARY_CHUNK_ROUNDS) * 2]

    summary = get_summary(messages_to_summarize)
    
    if summary:
        print(">>> 记忆总结完成", flush=True)
        # 记录本次总结的轮数
        LAST_SUMMARY_ROUND = LAST_SUMMARY_ROUND + SUMMARY_CHUNK_ROUNDS
        
        # 获取最新的前提摘要 (如果有的话)
        previous_premises = [msg for msg in full_history if msg['role'] == 'system' and '前提摘要' in msg.get('content', '')]
        
        # 将新生成的摘要添加到 full_history 中,但只用于发送给API
        new_premise_list = previous_premises + [{"role": "system", "content": f"前提摘要: {summary}"}]
        
        # 剩下的对话
        remaining_dialogue = dialogue_history[LAST_SUMMARY_ROUND * 2:]
        
        # 返回重构后的列表 (注意:这个列表仅用于API请求,不修改full_history)
        return [system_prompt] + new_premise_list + remaining_dialogue
    else:
        # 总结失败,为避免出错,按原样返回历史记录
        print(">>> 总结失败,将使用原始对话继续", flush=True)
        return full_history[:]

def chat_stream(user_input):
    """流式聊天函数"""
    global SHOW_REASONING, CURRENT_MODEL, ROUNDS_SINCE_LAST_SAVE, CURRENT_SESSION_NAME, full_history
    
    # 用户输入先加入完整历史
    full_history.append({"role": "user", "content": user_input})
    
    # 动态构建用于本次API请求的messages
    messages_for_api = get_messages_for_api()
    
    data = {
        "model": CURRENT_MODEL,
        "messages": messages_for_api, # 使用处理过的消息列表
        "stream": True,
        "temperature": 1.0
    }
    
    stream_headers = headers.copy()
    stream_headers["Accept"] = "text/event-stream"
    
    try:
        with requests.post(API_URL, headers=stream_headers, json=data, stream=True, timeout=TIMEOUT) as response:
            if response.status_code != 200:
                print(f"\n请求失败:{response.status_code}")
                print(response.text)
                full_history.pop() # 从完整历史中移除失败的用户输入
                return

            full_reply = []
            buffer = ""
            printed_reasoning_header = False
            printed_answer_header = False
            for chunk in response.iter_content(chunk_size=BUFFER_SIZE):
                if not chunk: continue
                decoded_chunk = chunk.decode('utf-8')
                buffer += decoded_chunk
                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)
                    if not event.startswith("data: "): continue
                    data_str = event[len("data: "):].strip()
                    if data_str == "[DONE]": break
                    try:
                        data_json = json.loads(data_str)
                        delta = data_json.get("choices", [{}])[0].get("delta", {})
                        reasoning = delta.get("reasoning_content", "")
                        if reasoning and SHOW_REASONING and CURRENT_MODEL != "deepseek-chat":
                            if not printed_reasoning_header:
                                print("[思考]:", end="", flush=True)
                                printed_reasoning_header = True
                            print(reasoning, end="", flush=True)
                        content = delta.get("content", "")
                        if content:
                            full_reply.append(content)
                            if not printed_answer_header:
                                if SHOW_REASONING and CURRENT_MODEL != "deepseek-chat":
                                    print("\n\n", end="", flush=True)
                                printed_answer_header = True
                            print(content, end="", flush=True)
                    except json.JSONDecodeError: continue
            
            if full_reply:
                print("", flush=True)
                assistant_reply = {"role": "assistant", "content": "".join(full_reply)}
                full_history.append(assistant_reply)
                
                if AUTO_SAVE_ENABLED:
                    ROUNDS_SINCE_LAST_SAVE += 1
                    if ROUNDS_SINCE_LAST_SAVE >= 1:
                        session_to_save = CURRENT_SESSION_NAME
                        if session_to_save == "<NEW>":
                            current_time_str = time.strftime("%d.%H-%M")
                            session_to_save = f"{current_time_str}"
                        
                        save_session(session_to_save, silent=True)
                        ROUNDS_SINCE_LAST_SAVE = 0
            else:
                if len(full_history) > 0 and full_history[-1]["role"] == "user": 
                    full_history.pop()
    except requests.exceptions.Timeout:
        print("\n请求超时"); full_history.pop()
    except requests.exceptions.RequestException as e:
        print(f"\n网络错误:{e}"); full_history.pop()
    except Exception as e:
        print(f"\n未知错误:{e}"); full_history.pop()

# 主循环 (无修改)
def main():
    global SHOW_REASONING, CURRENT_MODEL, AUTO_SAVE_ENABLED
    ensure_sessions_dir() # 确保目录存在
    print("--------------------\nDeepSeek\n微澜初醉,影香浮动。")
    while True:
        try:
            auto_save_status = "A" if AUTO_SAVE_ENABLED else ""
            session_status = f"[{CURRENT_SESSION_NAME}]" if CURRENT_SESSION_NAME != "<NEW>" else "[NEW]"
            user_input = input(f"{auto_save_status}{session_status}> ").strip()
            
            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0]
            
            if command == "save":
                if len(parts) > 1:
                    session_name = parts[1]
                    save_session(session_name)
                elif CURRENT_SESSION_NAME and CURRENT_SESSION_NAME != "<NEW>":
                    print(f">>> 将自动保存到当前会话 '{CURRENT_SESSION_NAME}'...")
                    save_session(CURRENT_SESSION_NAME)
                else:
                    print(">>> 请提供一个会话名称。用法: save <名称>")
                continue
            
            if command == "import":
                if len(parts) > 1:
                    session_name = parts[1]
                    load_session(session_name)
                else:
                    print(">>> 请提供要导入的会话名称。用法: import <名称>")
                continue

            if command == "list":
                list_sessions()
                continue
            
            if command == "auto":
                AUTO_SAVE_ENABLED = not AUTO_SAVE_ENABLED
                print(f">>> 自动保存功能已{'开启' if AUTO_SAVE_ENABLED else '关闭'}")
                continue

            if user_input == "thinking":
                if CURRENT_MODEL == "deepseek-chat":
                    print(">>> 当前为 Chat 模型,无法使用思维块功能")
                else:
                    CURRENT_MODEL = "deepseek-reasoner"
                    SHOW_REASONING = not SHOW_REASONING
                    print(f">>> 已{'开启' if SHOW_REASONING else '关闭'}思维块")
                continue

            elif user_input == "switch":
                if CURRENT_MODEL == "deepseek-reasoner":
                    CURRENT_MODEL = "deepseek-chat"
                    SHOW_REASONING = False
                    print(">>> 已切换到普通 Chat 模型")
                else:
                    CURRENT_MODEL = "deepseek-reasoner"
                    SHOW_REASONING = False
                    print(">>> 已切换到 Reasoner 模型\n>>> 已重置思维块状态为关闭")
                continue

            chat_stream(user_input)

        except KeyboardInterrupt:
            print("\n梦散风静,余影未去。")
            break
        except Exception as e:
            print(f"\n发生错误:{e}")
            continue

if __name__ == "__main__":
    main()
