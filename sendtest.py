import os, requests, monitor as M
topic = os.environ.get("NTFY_TOPIC", "")
out = []
def post(title, body, prio, tag):
    r = requests.post("https://ntfy.sh/", json={"topic": topic, "title": title, "message": body, "priority": prio, "tags": [tag]}, timeout=10)
    out.append(f"{title} -> {r.status_code}")
post("[알림] 연결 확인", "뉴스 알림 연결이 정상입니다.", 3, "newspaper")
t, b = M.message_recl("PEPE", {"price": 3.862e-6, "lvl": 3.847e-6, "low": 3.765e-6, "cvx": 5.57}, 1792363500, 0.002, 1.26)
post(t, "(테스트) " + b, 4, "newspaper")
open("sendtest.txt", "w").write("\n".join(out) + f"\ntopic_set={bool(topic)}\n")
print(open("sendtest.txt").read())
