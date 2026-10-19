import os, requests
topic = os.environ.get("NTFY_TOPIC", "") + "-s"
r = requests.post("https://ntfy.sh/", json={"topic": topic, "title": "short [알림] 연결 확인", "message": "해설 기사 알림 연결이 정상입니다.", "priority": 3, "tags": ["newspaper"]}, timeout=10)
open("sendtest.txt", "w").write(f"short topic -> {r.status_code}\n"); print(open("sendtest.txt").read())
