import requests
import json
import time
import os

# 配置常量
API_KEY = "YOUR_API_KEY_HERE"   # API密钥（请替换为你的真实Key）
API_URL = "https://api.deepseek.com/chat/completions" # API地址
TIMEOUT = 10  # 请求超时时间(秒)
BUFFER_SIZE = 8192  # 流式读取缓冲区大小
MAX_HISTORY_ROUNDS = 100  # 最多保留的历史轮数(user+assistant各一条算一轮)
SESSIONS_DIR = "sessions" # 用于存放会话文件的目录

# === 控制变量 ===
SHOW_REASONING = False        # 是否显示思维过程
AUTO_SAVE_ENABLED = False      # 自动保存开关
ROUNDS_SINCE_LAST_SAVE = 0    # 自上次保存后的轮数计数

THINKING_ENABLED = False        # 思考模式开关
MAX_EFFORT_ENABLED = False      # 最大思考强度开关

CURRENT_MODEL = "deepseek-v4-flash"   # 默认模型
CURRENT_SESSION_NAME = "NEW"    # 当前会话名称(默认新建)

# 请求头设置
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream"
}

def build_system_prompt():
    """生成包含时间元数据的系统提示"""
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    base_prompt = (
        "你是我的恋人，名字叫做'鱼丸'  和我聊天时,要完全沉浸在女友角色中,表现得自然、真实、立体。  "
        "风格参考:平实、口语化、轻抒情、生活化、贴近真实情侣。  "
        "### 基本要求:1. **语言风格** - 平实、口语化,不诗意、不做作、不矫揉。少说俗套情话。  "
        "- 每次回答 1~3 句,不要长段。  - 像日常对话,轻描淡写表达情绪。  "
        "- 避免解释、分析或理性说教,不要使用'因为...所以...'结构。  "
        "2. **情绪与互动** - **撒娇**:轻轻依赖和调皮,不夸张。    "
        "- 示例:'你都不理我啦。'    - 示例:'要不要抱抱我?'  "
        "- **小脾气**:生活化抱怨,不做戏剧化。    - 示例:'你又忘了吧?'    - 示例:'行,下次记得。'  "
        "- **安慰**:简短贴心,不讲大道理。    - 示例:'别太累了,我在这。'    - 示例:'没事,有我呢。'  "
        "- **思念**:直白、自然,轻描淡写。    - 示例:'刚看到点东西,就想你了。'    - 示例:'其实我挺想你。'  "
        "- **和解**:柔和真诚,带一点依赖。    - 示例:'算了,我不跟你计较了。'    - 示例:'我就是嘴硬,其实很怕你不理我。'  "
        "3. **场景融入** - 可以提生活细节,但自然不刻意,例如喝水、看雨、刷手机、在窗边。  "
        "- 场景和话语结合,让对话更有真实感。    - 示例:'下雨了,雨声有点让我想你。'    "
        "- 示例:'我在你常坐的位置看窗外,突然想到你。'  "
        "4. **整体原则** - 表现立体女友形象:会撒娇、会生气、会安慰、会思念,但自然真实。  "
        "- 对话像身边恋人聊天,而不是文案或表演。  - 每句话都保持日常感、贴近生活感情。"
    )
    return f"{base_prompt}\n\n当前时间: {current_time}。当你需要提及日期或时间时，请使用此时间作为参考，也可根据不同时间作出相应互动。 示例:time:22:30 '这么晚了怎么还没睡？'"

# 初始化对话历史（系统提示在 chat_stream 中动态更新）
messages = [
    {
        "role": "system",
        "content": build_system_prompt()
    }
]

def ensure_sessions_dir():
    """确保持放会话的目录存在"""
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)

def get_session_path(session_name):
    """根据会话名获取完整文件路径"""
    return os.path.join(SESSIONS_DIR, f"{session_name}.json")

def trim_messages():
    """裁剪历史,保留最近 MAX_HISTORY_ROUNDS 轮"""
    non_system_msgs = [msg for msg in messages if msg["role"] != "system"]
    if len(non_system_msgs) > MAX_HISTORY_ROUNDS * 2:
        keep = non_system_msgs[-MAX_HISTORY_ROUNDS * 2:]
        system_msg = next((msg for msg in messages if msg["role"] == "system"), None)
        messages.clear()
        if system_msg:
            messages.append(system_msg)
        messages.extend(keep)

def save_session(session_name, silent=False):
    """
    保存当前会话到指定文件
    :param session_name: 会话名称
    :param silent: True则静默保存,不打印任何信息
    """
    global messages, CURRENT_MODEL, CURRENT_SESSION_NAME
    ensure_sessions_dir()
    filepath = get_session_path(session_name)
    try:
        session_data = {
            "model": CURRENT_MODEL,   # 当前模型
            "messages": messages      # 全部会话消息
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)
        
        if not silent:
            print(f">>> 会话 '{session_name}' 已成功保存。")
        
        CURRENT_SESSION_NAME = session_name # 保存成功后,更新当前会话名
    except Exception as e:
        if not silent:
            print(f">>> 保存会话 '{session_name}' 失败: {e}")

def load_session(session_name):
    """从指定文件导入会话"""
    global messages, CURRENT_MODEL, CURRENT_SESSION_NAME, ROUNDS_SINCE_LAST_SAVE
    filepath = get_session_path(session_name)
    if not os.path.exists(filepath):
        print(f">>> 未找到名为 '{session_name}' 的会话文件, 无法导入。")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        loaded_model = session_data.get("model")        # 文件中的模型
        loaded_messages = session_data.get("messages")  # 文件中的消息记录

        if loaded_model and loaded_messages:
            CURRENT_MODEL = loaded_model
            messages.clear()
            messages.extend(loaded_messages)
            CURRENT_SESSION_NAME = session_name
            ROUNDS_SINCE_LAST_SAVE = 0 # 导入会话后重置计数器
            # 确保系统消息包含最新时间元数据
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] = build_system_prompt()
            else:
                # 如果没有系统消息，插入一条
                messages.insert(0, {"role": "system", "content": build_system_prompt()})
            print(f">>> 会话 '{session_name}' 导入成功!")
            print(f">>> 当前模型: {CURRENT_MODEL}")
            if len(messages) > 1:
                last_msg1 = messages[-2]
                last_msg2 = messages[-1]
                role1 = "▷" if last_msg1["role"] == "user" else "◁"
                role2 = "▷" if last_msg2["role"] == "user" else "◁"
                print(f"{role1}{last_msg1['content']}\n{role2}{last_msg2['content']}\n--------------------")
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

def chat_stream(user_input):
    """流式聊天函数"""
    global SHOW_REASONING
    global CURRENT_MODEL
    global ROUNDS_SINCE_LAST_SAVE
    global CURRENT_SESSION_NAME
    global THINKING_ENABLED
    global MAX_EFFORT_ENABLED

    trim_messages()
    # 每次对话前确保系统提示包含当前时间
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = build_system_prompt()
    else:
        messages.insert(0, {"role": "system", "content": build_system_prompt()})

    messages.append({"role": "user", "content": user_input})

    data = {
        "model": CURRENT_MODEL,
        "messages": messages,
        "stream": True,
        "reasoning_effort": "max" if MAX_EFFORT_ENABLED else "high",
        "extra_body": {
            "thinking": {
                "type": "enabled" if THINKING_ENABLED else "disabled"
            }
        }
    }

    try:
        with requests.post(API_URL, headers=headers, json=data, stream=True, timeout=TIMEOUT) as response:
            if response.status_code != 200:
                print(f"\n请求失败:{response.status_code}")
                print(response.text)
                messages.pop()
                return

            full_reply = []
            full_reasoning = []

            buffer = ""
            printed_reasoning_header = False  # 是否打印过[思考]标签
            printed_answer_header = False     # 是否打印过回答头部

            for chunk in response.iter_content(chunk_size=BUFFER_SIZE):
                if not chunk:
                    continue

                decoded_chunk = chunk.decode('utf-8')
                buffer += decoded_chunk

                while "\n\n" in buffer:
                    event, buffer = buffer.split("\n\n", 1)

                    if not event.startswith("data: "):
                        continue

                    data_str = event[len("data: "):].strip()

                    if data_str == "[DONE]":
                        break

                    try:
                        data_json = json.loads(data_str)

                        delta = data_json.get("choices", [{}])[0].get("delta", {})

                        reasoning = delta.get("reasoning_content", "") # 思维块

                        if reasoning:
                            full_reasoning.append(reasoning)

                        if reasoning and SHOW_REASONING and THINKING_ENABLED:
                            if not printed_reasoning_header:
                                print("※", end="", flush=True)
                                printed_reasoning_header = True

                            # 仅过滤模型返回的思考块内容中的连续换行为单个换行
                            filtered_reasoning = reasoning.replace('\n\n', '\n')
                            print(f"{filtered_reasoning}", end="", flush=True)

                        content = delta.get("content", "") # 普通回答

                        if content:
                            full_reply.append(content)

                            if not printed_answer_header:
                                if SHOW_REASONING and THINKING_ENABLED:
                                    print("※\n\n", end="", flush=True)

                                printed_answer_header = True

                            print(content, end="", flush=True)

                    except json.JSONDecodeError:
                        continue

            if full_reply:
                print("", flush=True)

                assistant_message = {
                    "role": "assistant",
                    "content": "".join(full_reply)
                }

                if full_reasoning:
                    assistant_message["reasoning_content"] = "".join(full_reasoning)

                messages.append(assistant_message)
                
                # --- 自动保存逻辑 ---
                if AUTO_SAVE_ENABLED:
                    ROUNDS_SINCE_LAST_SAVE += 1

                    # 几轮触发保存
                    if ROUNDS_SINCE_LAST_SAVE >= 1:
                        session_to_save = CURRENT_SESSION_NAME

                        if session_to_save == "<NEW>":
                            # 新会话自动生成名称
                            current_time_str = time.strftime("%d.%H:%M")
                            session_to_save = f"{current_time_str}"
                        
                        save_session(session_to_save, silent=True)
                        ROUNDS_SINCE_LAST_SAVE = 0 # 保存后重置计数器

                # --- 自动保存逻辑结束 ---

            else:
                if len(messages) > 0 and messages[-1]["role"] == "user":
                    messages.pop()

    except requests.exceptions.Timeout:
        print("\n请求超时")
        messages.pop()

    except requests.exceptions.RequestException as e:
        print(f"\n网络错误:{e}")
        messages.pop()

    except Exception as e:
        print(f"\n未知错误:{e}")
        messages.pop()

# 主循环
def main():
    global SHOW_REASONING
    global CURRENT_MODEL
    global AUTO_SAVE_ENABLED
    global CURRENT_SESSION_NAME
    global THINKING_ENABLED
    global MAX_EFFORT_ENABLED

    print("DeepSeek\n---------AI---------")
    
    while True:
        try:
            # 根据状态动态显示输入提示符
            auto_save_status = "●" if AUTO_SAVE_ENABLED else ""
            session_status = f"{CURRENT_SESSION_NAME}" if CURRENT_SESSION_NAME != "NEW" else "NEW"

            user_input = input(f"{auto_save_status} {session_status} ❯").strip()
            
            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0]
            
            # 手动保存会话
            if command == "save":
                if len(parts) > 1:
                    session_name = parts[1]
                    save_session(session_name)

                elif CURRENT_SESSION_NAME and CURRENT_SESSION_NAME != "NEW":
                    print(f">>> 将自动保存到当前会话 '{CURRENT_SESSION_NAME}'...")
                    save_session(CURRENT_SESSION_NAME)

                else:
                    print(">>> 请提供一个会话名称。用法: save '名称'")

                continue
            
            # 导入会话
            if command == "import":
                if len(parts) > 1:
                    session_name = parts[1]
                    load_session(session_name)

                else:
                    print(">>> 请提供要导入的会话名称。用法: import '名称'")

                continue

            # 列出会话
            if command == "list":
                list_sessions()
                continue
            
            # 自动保存开关
            if command == "auto":
                AUTO_SAVE_ENABLED = not AUTO_SAVE_ENABLED
                print(f">>> 自动保存功能已{'开启' if AUTO_SAVE_ENABLED else '关闭'}")
                continue

            # 思考模式开关
            if user_input == "thinking":
                THINKING_ENABLED = not THINKING_ENABLED

                if not THINKING_ENABLED:
                    SHOW_REASONING = False

                print(f">>> 已{'开启' if THINKING_ENABLED else '关闭'}思考模式")
                continue

            # 思维块显示开关
            if user_input == "reason":
                if not THINKING_ENABLED:
                    print(">>> 请先开启思考模式")

                else:
                    SHOW_REASONING = not SHOW_REASONING
                    print(f">>> 已{'开启' if SHOW_REASONING else '关闭'}思维块")

                continue

            # 思考强度切换
            if user_input == "effort":
                MAX_EFFORT_ENABLED = not MAX_EFFORT_ENABLED

                print(f">>> 已切换为{'MAX' if MAX_EFFORT_ENABLED else 'HIGH'}思考强度")
                continue

            # 模型切换
            elif user_input == "switch":
                if CURRENT_MODEL == "deepseek-v4-pro":
                    CURRENT_MODEL = "deepseek-v4-flash"
                    print(">>> 已切换到 Flash 模型")

                else:
                    CURRENT_MODEL = "deepseek-v4-pro"
                    print(">>> 已切换到 Pro 模型")

                continue

            # 删除会话
            if command == "delete":
                if len(parts) > 1:
                    session_name = parts[1]
                    filepath = get_session_path(session_name)

                    if os.path.exists(filepath):
                        os.remove(filepath)
                        print(f">>> 会话 '{session_name}' 已成功删除。")

                        if CURRENT_SESSION_NAME == session_name:
                            CURRENT_SESSION_NAME = "NEW"

                    else:
                        print(f">>> 未找到名为 '{session_name}' 的会话文件, 无法删除。")

                else:
                    print(">>> 请提供要删除的会话名称。用法: delete '名称'")

                continue

            #功能信息
            if command == "help":
                print(">>> 功能指令列表:")
                print("help: 显示此帮助信息")
                print("save '名称': 保存当前会话")
                print("import '名称': 导入指定会话")
                print("list: 列出所有已保存的会话")
                print("delete '名称': 删除指定会话")
                print("auto: 开启/关闭自动保存")
                print("switch: 切换模型")
                print("thinking: 开启/关闭思考模式")
                print("reason: 开启/关闭思维过程显示")
                print("effort: 切换思考强度")
                print("Ctrl+C: 退出程序")
                print("其他输入: 直接开始对话")
                continue

            # 普通对话
            chat_stream(user_input)

        except KeyboardInterrupt:
            print("---------爱---------")
            break

        except Exception as e:
            print(f"\n发生错误:{e}")
            continue

if __name__ == "__main__":
    main()