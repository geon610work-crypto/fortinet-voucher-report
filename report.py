import os
import json
import shutil
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import re

KST = timezone(timedelta(hours=9))


def require_env(name, hint=""):
    val = os.environ.get(name)
    if not val:
        msg = f"환경변수 {name}가 설정되지 않았습니다."
        if hint:
            msg += f" ({hint})"
        raise SystemExit(msg)
    return val


ASANA_TOKEN          = require_env("ASANA_TOKEN", "아사나 Personal Access Token")
ASANA_PROJECT_GID    = require_env("ASANA_PROJECT_GID", "아사나 프로젝트 GID")
SLACK_WEBHOOK_URL    = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_DM_WEBHOOK_URL = os.environ.get("SLACK_DM_WEBHOOK_URL", "")
IS_MANUAL    = os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"
# 금요일 오전 9시(KST) 슬랙 보고용 cron 인지 확인
IS_SLACK_RUN = os.environ.get("CRON_SCHEDULE", "") == "0 0 * * 5"

GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
if "/" in GITHUB_REPO:
    _owner, _repo = GITHUB_REPO.split("/", 1)
    PAGES_URL = f"https://{_owner}.github.io/{_repo}"
else:
    PAGES_URL = ""

MENTION   = os.environ.get("SLACK_MENTION", "<@U04PN00MA4B>")
FCSS_GOAL = 3
FCP_GOAL  = 1


def asana_get(path):
    req = urllib.request.Request(
        f"https://app.asana.com/api/1.0{path}",
        headers={"Authorization": f"Bearer {ASANA_TOKEN}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())


def asana_get_all(path):
    sep = "&" if "?" in path else "?"
    results = []
    next_url = f"{path}{sep}limit=100"
    while next_url:
        body = asana_get(next_url)
        results.extend(body.get("data", []))
        np = body.get("next_page") or {}
        offset = np.get("offset")
        next_url = f"{path}{sep}limit=100&offset={offset}" if offset else None
    return results


def get_cf(task, name):
    for f in task.get("custom_fields", []):
        if f.get("name") == name:
            ev = f.get("enum_value")
            if ev:
                return ev.get("name", "")
            return f.get("display_value", "") or ""
    return ""


def is_fcss_qualified(tasks):
    """NSE4(FortiOS) + NSE6(Network Security) + NSE7(Enterprise Firewall) 세 과목 모두 합격"""
    fortios = any("FortiOS"             in t["exam"] and t["passed"] == "합격" for t in tasks)
    nst     = any("Network Security"    in t["exam"] and t["passed"] == "합격" for t in tasks)
    efw     = any("Enterprise Firewall" in t["exam"] and t["passed"] == "합격" for t in tasks)
    return fortios and nst and efw


def is_fcp_qualified(tasks):
    """NSE4(FortiOS) + NSE5(FortiManager) 둘 다 합격"""
    fortios  = any("FortiOS"      in t["exam"] and t["passed"] == "합격" for t in tasks)
    fortimgr = any("FortiManager" in t["exam"] and t["passed"] == "합격" for t in tasks)
    return fortios and fortimgr


def send_slack(webhook, msg, target):
    payload = json.dumps({"text": msg}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as res:
            print(f"슬랙 {target} 전송 완료: {res.status}")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"⚠️ 슬랙 {target} 전송 실패: {e}")


def main():
    print("아사나 태스크 불러오는 중...")
    tasks_raw = asana_get_all(
        f"/projects/{ASANA_PROJECT_GID}/tasks"
        "?opt_fields=name,assignee.name,custom_fields"
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

    missing_qual = [r for r in rows if not r["qual"]]
    if missing_qual:
        print(f"⚠️ '자격' 필드 누락 태스크 {len(missing_qual)}개 (FCSS/FCP 표에서 제외됨): " +
              ", ".join(f"[{r['no']}]{r['code']}" for r in missing_qual))

    groups = defaultdict(list)
    for r in rows:
        groups[(r["assignee"], r["qual"])].append(r)

    fcss_people = {a: t for (a, q), t in groups.items() if q == "FCSS"}
    fcp_people  = {a: t for (a, q), t in groups.items() if q == "FCP"}
    fcss_done = sum(1 for tasks in fcss_people.values() if is_fcss_qualified(tasks))
    fcp_done  = sum(1 for tasks in fcp_people.values()  if is_fcp_qualified(tasks))

    today = datetime.now(KST)
    days = ["월","화","수","목","금","토","일"]
    date_str = f"{today.year}년 {today.month}월 {today.day}일 ({days[today.weekday()]})"

    def make_person_data(name, tasks):
        return {
            "name": name,
            "tasks": [
                {"exam": t["exam"], "used": t["used"], "passed": t["passed"]}
                for t in tasks
            ],
        }

    all_vouchers = [
        {
            "no": r["no"],
            "code": r["code"],
            "assignee": r["assignee"],
            "exam": r["exam"],
            "qual": r["qual"],
            "used": r["used"],
            "passed": r["passed"],
        }
        for r in rows if r["used"] == "사용"
    ]

    total      = len(rows)
    used_count = sum(1 for r in rows if r["used"] == "사용")
    fail_count = sum(1 for r in rows if r["used"] == "사용" and r["passed"] == "불합격")

    report_data = {
        "generated_at":    today.isoformat(),
        "fcss_done":       fcss_done,
        "fcss_goal":       FCSS_GOAL,
        "fcp_done":        fcp_done,
        "fcp_goal":        FCP_GOAL,
        "total_vouchers":  total,
        "used_vouchers":   used_count,
        "remain_vouchers": total - used_count,
        "fail_vouchers":   fail_count,
        "all_vouchers":    all_vouchers,
        "fcss":            [make_person_data(a, tasks) for a, tasks in fcss_people.items()],
        "fcp":             [make_person_data(a, tasks) for a, tasks in fcp_people.items()],
    }

    print("HTML 보고서 생성 중...")
    os.makedirs("docs", exist_ok=True)
    shutil.copy("report_template.html", "docs/index.html")
    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print("HTML + data.json 생성 완료")

    if not (IS_SLACK_RUN or IS_MANUAL):
        print("HTML 페이지만 업데이트 (슬랙 전송 생략)")
        return

    use_dm  = IS_MANUAL and bool(SLACK_DM_WEBHOOK_URL)
    webhook = SLACK_DM_WEBHOOK_URL if use_dm else SLACK_WEBHOOK_URL
    target  = "DM" if use_dm else "채널"

    if not webhook:
        print(f"⚠️ 슬랙 {target} Webhook URL이 없어 전송 생략")
        return

    mention_line = "" if use_dm else f"{MENTION}\n"
    msg_lines = [
        "📋 *포티넷 NSE 자격증 취득 현황 보고*",
        f"🗓 {date_str}",
        "─" * 30,
        f"• FCSS: *{fcss_done}/{FCSS_GOAL}명* 취득완료",
        f"• FCP:  *{fcp_done}/{FCP_GOAL}명* 취득완료",
    ]
    if PAGES_URL:
        msg_lines += ["", f"📊 <{PAGES_URL}|상세 현황 보기 →>"]
    msg = mention_line + "\n".join(msg_lines)

    print(f"슬랙 {target}에 전송 중...")
    send_slack(webhook, msg, target)


if __name__ == "__main__":
    main()
