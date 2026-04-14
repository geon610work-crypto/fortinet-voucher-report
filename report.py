import os
import json
import urllib.request
from datetime import datetime

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
        headers={
            "Authorization": f"Bearer {ASANA_TOKEN}",
            "Accept": "application/json"
        }
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
    if not name:
        return "-"
    if "Network Security" in name:
        return "NST"
    if "Enterprise Firewall" in name:
        return "EFW"
    if "FortiManager" in name:
        return "FMG"
    if "FortiOS" in name:
        return "FOS"
    words = name.split()
    return words[0][:8] if words else name[:8]

def status_mark(used, passed):
    if used != "사용":
        return "⬜ 미사용 "
    if passed == "합격":
        return "✅ 합격   "
    if passed == "불합격":
        return "❌ 불합격 "
    return "🔄 결과대기"

def pad(s, width):
    count = 0
    for c in s:
        count += 2 if ord(c) > 127 else 1
    spaces = max(0, width - count)
    return s + " " * spaces

def count_qualified(people_dict):
    count = 0
    for assignee, tasks in people_dict.items():
        used_tasks = [t for t in tasks if t["used"] == "사용"]
        if len(used_tasks) >= 2 and all(t["passed"] == "합격" for t in used_tasks):
            count += 1
    return count

def main():
    print("아사나 태스크 불러오는 중...")
    tasks_raw = asana_get(
        f"/projects/{ASANA_PROJECT_GID}/tasks"
        "?opt_fields=name,assignee.name,custom_fields&limit=100"
    )

    import re
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

    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        key = (r["assignee"], r["qual"])
        groups[key].append(r)

    fcss_people = {}
    fcp_people = {}
    for (assignee, qual), tasks in groups.items():
        if qual == "FCSS":
            fcss_people[assignee] = tasks
        elif qual == "FCP":
            fcp_people[assignee] = tasks

    fcss_done = count_qualified(fcss_people)
    fcp_done = count_qualified(fcp_people)

    today = datetime.now()
    days = ["월","화","수","목","금","토","일"]
    date_str = f"{today.year}년 {today.month}월 {today.day}일 ({days[today.weekday()]})"

    msg = f"{MENTION}\n"
    msg += f"📋 *포티넷 NSE 자격증 취득 현황 보고*\n"
    msg += f"🗓 {date_str}\n"
    msg += "─" * 40 + "\n\n"

    msg += f"📊 *취득 현황 요약*\n"
    msg += f"• FCSS: {fcss_done}/{FCSS_GOAL}명 취득완료\n"
    msg += f"• FCP:  {fcp_done}/{FCP_GOAL}명 취득완료\n\n"

    # FCSS 표
    msg += f"🔵 *FCSS 현황* ({fcss_done}/{FCSS_GOAL}명)\n"
    msg += "```\n"
    msg += pad("담당자", 10) + pad("NST", 12) + pad("EFW", 12) + "취득\n"
    msg += "─" * 42 + "\n"
    for assignee, tasks in fcss_people.items():
        nst = next((t for t in tasks if "Network Security" in t["exam"]), None)
        efw = next((t for t in tasks if "Enterprise Firewall" in t["exam"]), None)
        nst_s = status_mark(nst["used"], nst["passed"]) if nst else "⬜ 미배정  "
        efw_s = status_mark(efw["used"], efw["passed"]) if efw else "⬜ 미배정  "
        used_tasks = [t for t in tasks if t["used"] == "사용"]
        qualified = len(used_tasks) >= 2 and all(t["passed"] == "합격" for t in used_tasks)
        acq = "🏆 취득" if qualified else "❌ 미취득"
        msg += pad(assignee, 10) + pad(nst_s, 12) + pad(efw_s, 12) + acq + "\n"
    msg += "```\n\n"

    # FCP 표
    fcp_exams = []
    for tasks in fcp_people.values():
        for t in tasks:
            s = shorten_exam(t["exam"])
            if s not in fcp_exams:
                fcp_exams.append(s)
    e1 = fcp_exams[0] if len(fcp_exams) > 0 else "과목1"
    e2 = fcp_exams[1] if len(fcp_exams) > 1 else "과목2"

    msg += f"🟠 *FCP 현황* ({fcp_done}/{FCP_GOAL}명)\n"
    msg += "```\n"
    msg += pad("담당자", 10) + pad(e1, 12) + pad(e2, 12) + "취득\n"
    msg += "─" * 42 + "\n"
    for assignee, tasks in fcp_people.items():
        t1 = tasks[0] if len(tasks) > 0 else None
        t2 = tasks[1] if len(tasks) > 1 else None
        s1 = status_mark(t1["used"], t1["passed"]) if t1 else "⬜ 미배정  "
        s2 = status_mark(t2["used"], t2["passed"]) if t2 else "⬜ 미배정  "
        used_tasks = [t for t in tasks if t["used"] == "사용"]
        qualified = len(used_tasks) >= 2 and all(t["passed"] == "합격" for t in used_tasks)
        acq = "🏆 취득" if qualified else "❌ 미취득"
        msg += pad(assignee, 10) + pad(s1, 12) + pad(s2, 12) + acq + "\n"
    msg += "```\n"
    msg += "─" * 40

    # 수동 실행이면 DM, 자동 실행이면 채널
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
