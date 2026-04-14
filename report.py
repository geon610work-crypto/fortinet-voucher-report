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

def shorten_exam(name):
    if not name: return "-"
    if "Network Security" in name: return "NST"
    if "Enterprise Firewall" in name: return "EFW"
    if "FortiManager" in name: return "FMG"
    if "FortiOS" in name: return "FOS"
    return name.split()[0][:6] if name.split() else name[:6]

def status_text(used, passed):
    if used != "사용": return "⬜ 미사용"
    if passed == "합격": return "✅ 합격"
    if passed == "불합격": return "❌ 불합격"
    return "🔄 결과대기"

def count_qualified(people_dict):
    count = 0
    for tasks in people_dict.values():
        used = [t for t in tasks if t["used"] == "사용"]
        if len(used) >= 2 and all(t["passed"] == "합격" for t in used):
            count += 1
    return count

def make_table_text(header_cols, rows_data):
    """고정폭 텍스트 표 생성 - 슬랙 코드블록용"""
    COL_W = [10, 12, 12, 8]
    def cell(s, w):
        vis = sum(2 if ord(c) > 127 else 1 for c in s)
        return s + " " * max(0, w - vis)

    lines = []
    # 헤더
    h = ""
    for i, col in enumerate(header_cols):
        h += cell(col, COL_W[i])
    lines.append(h.rstrip())
    lines.append("─" * 44)
    # 데이터
    for row in rows_data:
        r = ""
        for i, col in enumerate(row):
            r += cell(col, COL_W[i])
        lines.append(r.rstrip())
    return "\n".join(lines)

def build_blocks(date_str, fcss_people, fcp_people, fcss_done, fcp_done):
    blocks = []

    # 헤더
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{MENTION}\n*📋 포티넷 NSE 자격증 취득 현황 보고*\n🗓 {date_str}"
        }
    })
    blocks.append({"type": "divider"})

    # 요약
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"📊 *취득 현황 요약*\n• FCSS: *{fcss_done}/{FCSS_GOAL}명* 취득완료　|　FCP: *{fcp_done}/{FCP_GOAL}명* 취득완료"
        }
    })
    blocks.append({"type": "divider"})

    # FCSS 표
    fcss_rows = []
    for assignee, tasks in fcss_people.items():
        nst = next((t for t in tasks if "Network Security" in t["exam"]), None)
        efw = next((t for t in tasks if "Enterprise Firewall" in t["exam"]), None)
        nst_s = status_text(nst["used"], nst["passed"]) if nst else "⬜ 미배정"
        efw_s = status_text(efw["used"], efw["passed"]) if efw else "⬜ 미배정"
        used_tasks = [t for t in tasks if t["used"] == "사용"]
        acq = "🏆 취득" if len(used_tasks) >= 2 and all(t["passed"] == "합격" for t in used_tasks) else "❌"
        fcss_rows.append([assignee, nst_s, efw_s, acq])

    fcss_table = make_table_text(["담당자", "NST", "EFW", "취득"], fcss_rows)
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"🔵 *FCSS 현황* ({fcss_done}/{FCSS_GOAL}명)"}
    })
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"```{fcss_table}```"}
    })
    blocks.append({"type": "divider"})

    # FCP 표
    fcp_exams = []
    for tasks in fcp_people.values():
        for t in tasks:
            s = shorten_exam(t["exam"])
            if s not in fcp_exams:
                fcp_exams.append(s)
    e1 = fcp_exams[0] if len(fcp_exams) > 0 else "과목1"
    e2 = fcp_exams[1] if len(fcp_exams) > 1 else "과목2"

    fcp_rows = []
    for assignee, tasks in fcp_people.items():
        t1 = tasks[0] if len(tasks) > 0 else None
        t2 = tasks[1] if len(tasks) > 1 else None
        s1 = status_text(t1["used"], t1["passed"]) if t1 else "⬜ 미배정"
        s2 = status_text(t2["used"], t2["passed"]) if t2 else "⬜ 미배정"
        used_tasks = [t for t in tasks if t["used"] == "사용"]
        acq = "🏆 취득" if len(used_tasks) >= 2 and all(t["passed"] == "합격" for t in used_tasks) else "❌"
        fcp_rows.append([assignee, s1, s2, acq])

    fcp_table = make_table_text(["담당자", e1, e2, "취득"], fcp_rows)
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"🟠 *FCP 현황* ({fcp_done}/{FCP_GOAL}명)"}
    })
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"```{fcp_table}```"}
    })

    return blocks

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

    blocks = build_blocks(date_str, fcss_people, fcp_people, fcss_done, fcp_done)
    payload = json.dumps({"blocks": blocks}).encode("utf-8")

    webhook = SLACK_DM_WEBHOOK_URL if IS_MANUAL and SLACK_DM_WEBHOOK_URL else SLACK_WEBHOOK_URL
    target = "DM" if IS_MANUAL and SLACK_DM_WEBHOOK_URL else "채널"

    print(f"슬랙 {target}에 전송 중...")
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
