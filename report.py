import os
import json
import urllib.request
from datetime import datetime
from collections import defaultdict
import re

ASANA_TOKEN = os.environ["ASANA_TOKEN"]
ASANA_PROJECT_GID = os.environ["ASANA_PROJECT_GID"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_DM_WEBHOOK_URL = os.environ.get("SLACK_DM_WEBHOOK_URL", "")
IS_MANUAL = os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
PAGES_URL = f"https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[1]}"

MENTION = "<@U04PN00MA4B>"
FCSS_GOAL = 3
FCP_GOAL = 1

def asana_get(path):
    req = urllib.request.Request(
        f"https://app.asana.com/api/1.0{path}",
        headers={"Authorization": f"Bearer {ASANA_TOKEN}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())["data"]

def get_cf(task, name):
    for f in task.get("custom_fields", []):
        if f.get("name") == name:
            ev = f.get("enum_value")
            if ev:
                return ev.get("name", "")
            return f.get("display_value", "") or ""
    return ""

def count_qualified(people):
    count = 0
    for tasks in people.values():
        used = [t for t in tasks if t["used"] == "사용"]
        if len(used) >= 2 and all(t["passed"] == "합격" for t in used):
            count += 1
    return count

def main():
    print("아사나 태스크 불러오는 중...")
    tasks_raw = asana_get(
        f"/projects/{ASANA_PROJECT_GID}/tasks"
        "?opt_fields=name,assignee.name,custom_fields&limit=100"
    )

    rows = []
    for t in tasks_raw:
        name = t.get("name", "")
        m = re.match(r"\[(\d+)\]\s+(\S+)", name)
        code = m.group(2) if m else name
        assignee = (t.get("assignee") or {}).get("name", "미배정")
        rows.append({
            "no":       int(m.group(1)) if m else 0,
            "code":     code,
            "assignee": assignee,
            "used":     get_cf(t, "사용여부") or "미사용",
            "passed":   get_cf(t, "합격여부") or "미정",
            "exam":     get_cf(t, "시험"),
            "qual":     get_cf(t, "자격"),
        })
    rows.sort(key=lambda r: r["no"])

    groups = defaultdict(list)
    for r in rows:
        groups[(r["assignee"], r["qual"])].append(r)

    fcss_people = {a: t for (a, q), t in groups.items() if q == "FCSS"}
    fcp_people  = {a: t for (a, q), t in groups.items() if q == "FCP"}
    fcss_done = count_qualified(fcss_people)
    fcp_done  = count_qualified(fcp_people)

    today = datetime.now()
    days = ["월","화","수","목","금","토","일"]
    date_str = f"{today.year}년 {today.month}월 {today.day}일 ({days[today.weekday()]})"

    # JSON 데이터 생성
    report_data = {
        "generated_at": today.isoformat(),
        "fcss_done": fcss_done,
        "fcp_done": fcp_done,
        "fcss": [
            {"name": a, "tasks": [{"exam": t["exam"], "used": t["used"], "passed": t["passed"]} for t in tasks]}
            for a, tasks in fcss_people.items()
        ],
        "fcp": [
            {"name": a, "tasks": [{"exam": t["exam"], "used": t["used"], "passed": t["passed"]} for t in tasks]}
            for a, tasks in fcp_people.items()
        ]
    }

    # HTML 생성
    print("HTML 보고서 생성 중...")
    with open("report_template.html", "r", encoding="utf-8") as f:
        template = f.read()

    html = template.replace("__REPORT_DATA__", json.dumps(report_data, ensure_ascii=False))

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML 생성 완료: docs/index.html")

    # 슬랙 메시지 (링크 포함 간단 요약)
    report_url = PAGES_URL
    mention_line = f"{MENTION}\n" if not IS_MANUAL else ""
    msg_lines = [
        f"📋 *포티넷 NSE 자격증 취득 현황 보고*",
        f"🗓 {date_str}",
        "─" * 30,
        f"• FCSS: *{fcss_done}/{FCSS_GOAL}명* 취득완료",
        f"• FCP:  *{fcp_done}/{FCP_GOAL}명* 취득완료",
        "",
        f"📊 <{report_url}|상세 현황 보기 →>",
    ]
    msg = mention_line + "\n".join(msg_lines)

    webhook = SLACK_DM_WEBHOOK_URL if IS_MANUAL and SLACK_DM_WEBHOOK_URL else SLACK_WEBHOOK_URL
    target = "DM" if IS_MANUAL and SLACK_DM_WEBHOOK_URL else "채널"

    print(f"슬랙 {target}에 전송 중...")
    payload = json.dumps({"text": msg}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        print(f"슬랙 전송 완료: {res.status}")

if __name__ == "__main__":
    main()
