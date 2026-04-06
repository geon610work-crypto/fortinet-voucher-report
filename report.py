import os
import json
import urllib.request
import urllib.error
from datetime import datetime

ASANA_TOKEN = os.environ["ASANA_TOKEN"]
ASANA_PROJECT_GID = os.environ["ASANA_PROJECT_GID"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

def asana_get(path):
    req = urllib.request.Request(
        f"https://app.asana.com/api/1.0{path}",
import os
        import json
import urllib.request
import urllib.error
from datetime import datetime

ASANA_TOKEN = os.environ["ASANA_TOKEN"]
ASANA_PROJECT_GID = os.environ["ASANA_PROJECT_GID"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

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
                                                        return f.get("display_value", "")
                                return ""
                
def is_expiring_soon(expire_str):
        months = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                                "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
        try:
                    parts = expire_str.split(".")
                    day, mon, yr = int(parts[0]), months[parts[1]], 2000 + int(parts[2])
                    expire_date = datetime(yr, mon, day)
                    diff = (expire_date - datetime.now()).days
                    return 0 < diff <= 30
                except:
                            return False
                    
    VOUCHERS = {
            "FTE2544E3106": {"no": 1,  "expire": "31.Mar.26"},
            "FTE278896A65": {"no": 2,  "expire": "4.Jun.26"},
            "FTE2788C240E": {"no": 3,  "expire": "4.Jun.26"},
            "FTE2788C127C": {"no": 4,  "expire": "4.Jun.26"},
            "FTE254500125": {"no": 5,  "expire": "31.Mar.26"},
            "FTE2788C2A5F": {"no": 6,  "expire": "4.Jun.26"},
            "FTE2788C745B": {"no": 7,  "expire": "4.Jun.26"},
            "FTE278914737": {"no": 8,  "expire": "4.Jun.26"},
            "FTE27896255C": {"no": 9,  "expire": "4.Jun.26"},
            "FTE279027E40": {"no": 10, "expire": "4.Jun.26"},
            "FTE279069305": {"no": 11, "expire": "4.Jun.26"},
            "FTE27910435E": {"no": 12, "expire": "4.Jun.26"},
    }

def main():
        print("아사나 태스크 불러오는 중...")
        tasks_raw = asana_get(
                    f"/projects/{ASANA_PROJECT_GID}/tasks"
                    "?opt_fields=name,assignee.name,custom_fields,completed&limit=100"
        )
    
    import re
    rows = []
    for t in tasks_raw:
                name = t.get("name", "")
                m = re.match(r"\[(\d+)\]\s+(\S+?)(?:\s+—\s+(.+))?$", name)
                code = m.group(2) if m else name
                base = VOUCHERS.get(code, {})
                rows.append({
                                "no":       m.group(1) if m else str(base.get("no", "")),
                                "code":     code,
                                "expire":   base.get("expire", ""),
                                "assignee": (t.get("assignee") or {}).get("name", ""),
                                "used":     get_cf(t, "사용여부") or "미사용",
                                "passed":   get_cf(t, "합격여부") or "미정",
                })
        
    today = datetime.now()
    days = ["월","화","수","목","금","토","일"]
    date_str = f"{today.year}년 {today.month}월 {today.day}일 ({days[today.weekday()]})"

    used   = [r for r in rows if r["used"] == "사용"]
    unused = [r for r in rows if r["used"] != "사용"]
    passed = [r for r in rows if r["passed"] == "합격"]
    failed = [r for r in rows if r["passed"] == "불합격"]
    expire = [r for r in rows if r["expire"] and is_expiring_soon(r["expire"])]

    msg = f"📋 *포티넷 NSE 자격증 바우처 현황 보고*\n"
    msg += f"🗓 {date_str}\n"
    msg += "─" * 36 + "\n\n"
    msg += f"📊 *전체 현황*\n"
    msg += f"• 전체 바우처: {len(rows)}개\n"
    msg += f"• 사용됨: {len(used)}개 / 미사용: {len(unused)}개\n"
    msg += f"• 합격: {len(passed)}명 / 불합격: {len(failed)}명\n\n"

    if used:
                msg += "✅ *바우처 사용 내역*\n"
                for r in used:
                                who = r["assignee"] or "담당자 미배정"
                                res = ("🟢 합격"    if r["passed"] == "합격"
                                                     else "🔴 불합격" if r["passed"] == "불합격"
                                                     else "⏳ 결과 대기")
                                msg += f"• [{r['no']}] {who} → {res}\n"
                            msg += "\n"

    if unused:
                msg += f"📦 *미사용 바우처 ({len(unused)}개)*\n"
        for r in unused:
                        who  = r["assignee"] or "미배정"
                        warn = " ⚠️만료임박" if r["expire"] and is_expiring_soon(r["expire"]) else ""
                        msg += f"• [{r['no']}] {r['code']} | {who}{warn}\n"
                    msg += "\n"

    if expire:
                msg += "⚠️ *만료 임박 바우처 (30일 이내)*\n"
        for r in expire:
                        msg += f"• [{r['no']}] {r['code']} — 만료: {r['expire']}\n"
                    msg += "\n"

    msg += "─" * 36 + "\n_문의사항은 담당자에게 연락 주세요._"

    print("슬랙에 전송 중...")
    payload = json.dumps({"text": msg}).encode("utf-8")
    req = urllib.request.Request(
                SLACK_WEBHOOK_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
    )
    with urllib.request.urlopen(req) as res:
                print(f"슬랙 전송 완료: {res.status}")

if __name__ == "__main__":
        main()
headers=
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
            return f.get("display_value", "")
    return ""

def is_expiring_soon(expire_str):
    months = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
              "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    try:
        parts = expire_str.split(".")
        day, mon, yr = int(parts[0]), months[parts[1]], 2000 + int(parts[2])
        expire_date = datetime(yr, mon, day)
        diff = (expire_date - datetime.now()).days
        return 0 < diff <= 30
    except:
        return False

VOUCHERS = {
    "FTE2544E3106": {"no": 1,  "expire": "31.Mar.26", "team": "NI기술팀"},
    "FTE278896A65": {"no": 2,  "expire": "4.Jun.26",  "team": ""},
    "FTE2788C240E": {"no": 3,  "expire": "4.Jun.26",  "team": ""},
    "FTE2788C127C": {"no": 4,  "expire": "4.Jun.26",  "team": ""},
    "FTE254500125": {"no": 5,  "expire": "31.Mar.26", "team": "기술지원센터"},
    "FTE2788C2A5F": {"no": 6,  "expire": "4.Jun.26",  "team": ""},
    "FTE2788C745B": {"no": 7,  "expire": "4.Jun.26",  "team": "보안기술팀"},
    "FTE278914737": {"no": 8,  "expire": "4.Jun.26",  "team": ""},
    "FTE27896255C": {"no": 9,  "expire": "4.Jun.26",  "team": ""},
    "FTE279027E40": {"no": 10, "expire": "4.Jun.26",  "team": ""},
    "FTE279069305": {"no": 11, "expire": "4.Jun.26",  "team": "보안인프라팀"},
    "FTE27910435E": {"no": 12, "expire": "4.Jun.26",  "team": ""},
}

def main():
    print("아사나 태스크 불러오는 중...")
    tasks_raw = asana_get(
        f"/projects/{ASANA_PROJECT_GID}/tasks"
        "?opt_fields=name,assignee.name,custom_fields,completed&limit=100"
    )

    import re
    rows = []
    for t in tasks_raw:
        name = t.get("name", "")
        m = re.match(r"\[(\d+)\]\s+(\S+?)(?:\s+—\s+(.+))?$", name)
        code = m.group(2) if m else name
        base = VOUCHERS.get(code, {})
        rows.append({
            "no":       m.group(1) if m else base.get("no", ""),
            "code":     code,
            "team":     m.group(3) if (m and m.group(3)) else base.get("team", ""),
            "expire":   base.get("expire", ""),
            "assignee": (t.get("assignee") or {}).get("name", ""),
            "used":     get_cf(t, "사용여부") or "미사용",
            "passed":   get_cf(t, "합격여부") or "미정",
        })

    today = datetime.now()
        days = ["월","화","수","목","금","토","일"]
    date_str = f"{today.year}년 {today.month}월 {today.day}일 ({days[today.weekday()]})"

    used   = [r for r in rows if r["used"] == "사용"]
    unused = [r for r in rows if r["used"] != "사용"]
    passed = [r for r in rows if r["passed"] == "합격"]
    failed = [r for r in rows if r["passed"] == "불합격"]
    expire = [r for r in rows if r["expire"] and is_expiring_soon(r["expire"])]

    msg = f"📋 *포티넷 NSE 자격증 바우처 현황 보고*\n"
    msg += f"🗓 {date_str}\n"
    msg += "─" * 36 + "\n\n"
    msg += f"📊 *전체 현황*\n"
    msg += f"• 전체 바우처: {len(rows)}개\n"
    msg += f"• 사용됨: {len(used)}개 / 미사용: {len(unused)}개\n"
    msg += f"• 합격: {len(passed)}명 / 불합격: {len(failed)}명\n\n"

    if used:
        msg += "✅ *바우처 사용 내역*\n"
        for r in used:
            who  = r["assignee"] or "미기재"
            team = r["team"] or "미기재"
            res  = ("🟢 합격"    if r["passed"] == "합격"
               else "🔴 불합격" if r["passed"] == "불합격"
               else "⏳ 결과 대기")
            msg += f"• [{r['no']}] {team} / {who} → {res}\n"
        msg += "\n"

    if unused:
        msg += f"📦 *미사용 바우처 ({len(unused)}개)*\n"
        for r in unused:
            warn = " ⚠️만료임박" if r["expire"] and is_expiring_soon(r["expire"]) else ""
            msg += f"• [{r['no']}] {r['code']} | {r['team'] or '미배정'}{warn}\n"
        msg += "\n"

    if expire:
        msg += "⚠️ *만료 임박 바우처 (30일 이내)*\n"
        for r in expire:
            msg += f"• [{r['no']}] {r['code']} — 만료: {r['expire']}\n"
        msg += "\n"

    msg += "─" * 36 + "\n_문의사항은 담당자에게 연락 주세요._"

    print("슬랙에 전송 중...")
    payload = json.dumps({"text": msg}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        print(f"슬랙 전송 완료: {res.status}")

if __name__ == "__main__":
    main()
