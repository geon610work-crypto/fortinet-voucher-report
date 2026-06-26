# 포티넷 NSE 바우처 관리 시스템 — Claude Code 지침

## 프로젝트 개요
포티넷 NSE 자격증 바우처 현황을 아사나(Asana)에서 읽어와 GitHub Pages HTML 보고서를 자동 생성하고, 금요일마다 슬랙 채널에 요약 보고하는 자동화 시스템.

---

## 저장소 구조

```
fortinet-voucher-report/
├── report.py                        # 메인 스크립트 (아사나 → data.json + 슬랙 전송)
├── report_template.html             # HTML 보고서 템플릿 (data.json 읽어서 렌더링)
├── .github/
│   └── workflows/
│       └── weekly-report.yml        # GitHub Actions 워크플로
└── docs/                            # GitHub Pages 배포 폴더 (Actions가 자동 생성)
    ├── index.html                   # 배포된 HTML 보고서
    └── data.json                    # 배포된 아사나 데이터
```

---

## GitHub Actions 스케줄

```yaml
schedule:
  - cron: '0 * * * *'    # 매시간 — data.json + HTML 업데이트만
  - cron: '0 0 * * 5'    # 금요일 오전 9시 (KST) — 슬랙 채널 보고
workflow_dispatch:         # 수동 실행 — 본인 DM으로 테스트 전송
```

---

## GitHub Secrets (Settings → Secrets → Actions)

| Secret 이름 | 설명 |
|---|---|
| `ASANA_TOKEN` | 아사나 Personal Access Token |
| `ASANA_PROJECT_GID` | 아사나 프로젝트 GID |
| `SLACK_WEBHOOK_URL` | 슬랙 채널 Webhook URL (금요일 자동 보고용) |
| `SLACK_DM_WEBHOOK_URL` | 본인 DM Webhook URL (수동 실행 테스트용) |

---

## 아사나 프로젝트 구조

### 태스크 이름 형식
```
[번호] 바우처코드 — 팀명
예: [1] FTE2544E3106 — NI기술팀
```

### 커스텀 필드
| 필드명 | 값 |
|---|---|
| `사용여부` | `사용` / `미사용` / `개인결제` |
| `합격여부` | `합격` / `불합격` / `미정` |
| `시험` | 시험 전체 이름 (예: FCSS - Network Security 7.6 Support Engineer) |
| `자격` | `FCSS` / `FCP` |

**`사용여부` 값 의미**
- `사용` — 회사 바우처를 소모하여 응시
- `미사용` — 바우처 미배정 / 미응시
- `개인결제` — 회사 바우처 없이 개인이 결제하여 응시 (회사 바우처 통계에서 제외, "💳 개인결제" 별도 집계)

### 바우처 목록 (총 12개)
```
[1]  FTE2544E3106  만료: 31.Mar.26  팀: NI기술팀
[2]  FTE278896A65  만료: 4.Jun.26
[3]  FTE2788C240E  만료: 4.Jun.26
[4]  FTE2788C127C  만료: 4.Jun.26
[5]  FTE254500125  만료: 31.Mar.26  팀: 기술지원센터
[6]  FTE2788C2A5F  만료: 4.Jun.26
[7]  FTE2788C745B  만료: 4.Jun.26   팀: 보안기술팀
[8]  FTE278914737  만료: 4.Jun.26
[9]  FTE27896255C  만료: 4.Jun.26
[10] FTE279027E40  만료: 4.Jun.26
[11] FTE279069305  만료: 4.Jun.26   팀: 보안인프라팀
[12] FTE27910435E  만료: 4.Jun.26
```

---

## 자격 취득 조건

### FCSS (목표: 3명)
- NSE4 (FortiOS) 합격
- NSE6 (Network Security) 합격
- NSE7 (Enterprise Firewall) 합격
- → 세 과목 모두 합격 시 🏆 FCSS 취득

### FCP (목표: 1명)
- NSE4 (FortiOS) 합격
- NSE5 (FortiManager) 합격
- → 두 과목 모두 합격 시 🏆 FCP 취득

### 시험 과목 판별 기준 (exam 필드 키워드)
| 과목 | 키워드 |
|---|---|
| NSE4 | `FortiOS` |
| NSE5 | `FortiManager` |
| NSE6 (NST) | `Network Security` |
| NSE7 (EFW) | `Enterprise Firewall` |

---

## 재시험 처리 방식
- 한 사람이 같은 과목을 재시험 볼 수 있음 (불합격 후 남은 바우처 사용)
- 아사나에서 같은 담당자에게 바우처를 추가 배정하는 방식
- 코드에서는 아사나 태스크 번호(no) 순서 그대로 표시
- 취득 판별: 해당 과목 태스크 중 합격인 게 하나라도 있으면 합격 처리

---

## 슬랙 보고 형식

```
@성영삼 (슬랙 ID: U04PN00MA4B)
📋 포티넷 NSE 자격증 취득 현황 보고
🗓 2026년 6월 6일 (금)
────────────────────────────────────

• FCSS: 0/3명 취득완료
• FCP:  0/1명 취득완료

📊 <HTML 보고서 링크|상세 현황 보기 →>
```

- 수동 실행(workflow_dispatch)이면 @멘션 없이 DM으로 전송
- 금요일 자동 실행이면 @성영삼 멘션 포함하여 채널로 전송

---

## HTML 보고서 (GitHub Pages)

**URL:** `https://geon610work-crypto.github.io/fortinet-voucher-report/`

### 동작 방식
1. Actions 실행 시 `data.json` + `index.html` 생성 → GitHub Pages 배포
2. 페이지 로드 시 `data.json` fetch → 렌더링
3. `↻ 새로고침` 버튼으로 최신 `data.json` 재로드

### 보고서 구성
1. **FCSS 현황 표** — 담당자별 시험1/2/3 결과 + 취득 여부 (🏆/⭐/—)
2. **FCP 현황 표** — 담당자별 시험1/2 결과 + 취득 여부
3. **바우처 소모 현황** — 전체/사용됨/잔여/불합격 요약 + 담당자별 소모 내역
4. **CSV / 엑셀 다운로드** — 헤더: 담당자, 시험1~3 과목명/사용여부/합격여부, 자격취득

### data.json 구조
```json
{
  "generated_at": "2026-06-06T09:00:00",
  "fcss_done": 0,
  "fcss_full": 0,
  "fcp_done": 0,
  "total_vouchers": 12,
  "used_vouchers": 4,
  "remain_vouchers": 8,
  "fail_vouchers": 1,
  "all_vouchers": [
    {
      "no": 1, "code": "FTE2544E3106",
      "assignee": "박건욱",
      "exam": "FCSS - Network Security 7.6 Support Engineer",
      "qual": "FCSS", "used": "사용", "passed": "합격"
    }
  ],
  "fcss": [
    {
      "name": "박건욱",
      "tasks": [
        {"exam": "FCSS - Network Security 7.6 Support Engineer", "used": "사용", "passed": "합격"},
        {"exam": "FCSS - Enterprise Firewall 7.6 Administrator", "used": "미사용", "passed": "미정"}
      ]
    }
  ],
  "fcp": [...]
}
```

---

## report.py 주요 함수

| 함수 | 역할 |
|---|---|
| `asana_get(path)` | 아사나 API GET 요청 |
| `get_cf(task, name)` | 태스크에서 커스텀 필드 값 추출 |
| `is_qualified(tasks)` | FCSS/FCP 취득 여부 판별 |
| `is_full_qualified(tasks)` | FCSS + NSE4 완전 완료 여부 판별 |
| `make_person_data(name, tasks)` | 담당자별 태스크 데이터 정리 (번호순) |
| `count_qualified(people)` | 취득 인원 집계 |
| `main()` | 전체 실행 (아사나 읽기 → data.json → HTML → 슬랙) |

---

## 환경 변수 (weekly-report.yml에서 주입)

| 변수 | 설명 |
|---|---|
| `ASANA_TOKEN` | 아사나 PAT |
| `ASANA_PROJECT_GID` | 아사나 프로젝트 GID |
| `SLACK_WEBHOOK_URL` | 채널 Webhook |
| `SLACK_DM_WEBHOOK_URL` | DM Webhook |
| `GITHUB_EVENT_NAME` | `schedule` / `workflow_dispatch` |
| `CRON_SCHEDULE` | 실행된 cron 표현식 (슬랙 전송 여부 판별용) |
| `GITHUB_REPOSITORY` | GitHub Pages URL 생성용 |

---

## 주요 로직 분기

```python
IS_MANUAL   = GITHUB_EVENT_NAME == "workflow_dispatch"
IS_SLACK_RUN = CRON_SCHEDULE == "0 0 * * 5"  # 금요일 9시 스케줄

# 슬랙 전송: 금요일 스케줄 또는 수동 실행일 때만
if IS_SLACK_RUN or IS_MANUAL:
    webhook = DM_URL if IS_MANUAL else CHANNEL_URL
    # @멘션: 채널 전송일 때만 포함

# HTML 업데이트: 항상 실행
```

---

## 알려진 이슈 및 참고사항

1. **GitHub Actions cron 지연** — 무료 플랜에서 매시간 cron이 실제로는 1~2시간 지연될 수 있음. 즉시 업데이트가 필요하면 `Run workflow` 수동 실행 필요.

2. **GitHub Pages 배포 지연** — Actions 완료 후 페이지 반영까지 1~2분 소요.

3. **아사나 태스크 번호 기준 정렬** — `make_person_data`에서 태스크를 `no`(바우처 번호) 순으로 정렬. 재시험 태스크는 번호가 더 높으므로 시험2, 시험3으로 표시됨.

4. **NSE4 태스크 그룹핑** — NSE4는 FCSS/FCP 모두에 등장할 수 있음. `자격` 필드가 FCSS인 사람의 NSE4는 FCSS 그룹에, FCP인 사람의 NSE4는 FCP 그룹에 포함됨.

5. **저장소 Public 설정** — GitHub Pages 무료 사용을 위해 저장소가 Public으로 설정되어 있음. 토큰 등 민감 정보는 모두 GitHub Secrets에 저장됨.
