"""나의 일상 - 매일 아침 오늘·내일 일정 알림 보내기 (GitHub Actions에서 실행)"""
import json, os, sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
DAYS = ["월", "화", "수", "목", "금", "토", "일"]


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def items_for(day, tt):
    """day(날짜)에 해당하는 일정 목록 [(정렬키, 문자열)]"""
    wd = day.weekday()  # 월=0
    key = day.strftime("%Y-%m-%d")
    hide_nba = bool(tt.get("hideNba"))
    out = []
    for t in tt.get("tasks") or []:
        if t.get("day") == wd:
            out.append((t.get("start") or 0, f"{hm(t['start'])} {t.get('title', '')}" if t.get("start") is not None else t.get("title", "")))
    for e in tt.get("events") or []:
        if e.get("date") != key:
            continue
        if hide_nba and str(e.get("id", "")).startswith("mavs"):
            continue
        s = e.get("start")
        out.append((-1 if s is None else s, (f"{hm(s)} " if s is not None else "하루 종일 ") + e.get("title", "")))
    out.sort(key=lambda x: x[0])
    return [x[1] for x in out]


def dday_lines(today, tt):
    out = []
    for e in tt.get("events") or []:
        if not e.get("dday"):
            continue
        try:
            n = (datetime.strptime(e["date"], "%Y-%m-%d").date() - today).days
        except Exception:
            continue
        if 0 <= n <= 30:
            out.append((n, ("D-DAY" if n == 0 else f"D-{n}") + " " + e.get("title", "")))
    return [x[1] for x in sorted(out)]


def compose(tt, now=None):
    now = now or datetime.now(KST)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    lines = []
    for label, d in (("오늘", today), ("내일", tomorrow)):
        its = items_for(d, tt)
        lines.append(f"[{label} {d.month}/{d.day}({DAYS[d.weekday()]})]")
        lines += [f"· {x}" for x in its] if its else ["· 일정 없음"]
    dd = dday_lines(today, tt)
    if dd:
        lines.append("[D-day] " + " / ".join(dd[:3]))
    n_today = len(items_for(today, tt))
    title = f"☀️ 오늘 일정 {n_today}개" if n_today else "☀️ 오늘은 일정이 없어요"
    return title, "\n".join(lines)


def wait_until_target():
    """예약 실행이면 정해진 시각(WAIT_UNTIL, 예: 08:00)까지 기다렸다가 보내요."""
    import time
    target = os.environ.get("WAIT_UNTIL", "").strip()
    if not target:
        return
    h, m = map(int, target.split(":"))
    now = datetime.now(KST)
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    wait = (t - now).total_seconds()
    if 0 < wait < 3 * 3600:
        print(f"{target}까지 {int(wait // 60)}분 {int(wait % 60)}초 기다려요")
        time.sleep(wait)
    else:
        print(f"이미 {target}이 지나서 바로 보내요 (지금 {now:%H:%M})")


def main():
    wait_until_target()
    import firebase_admin
    from firebase_admin import credentials, firestore, messaging

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if not raw:
        sys.exit("FIREBASE_SERVICE_ACCOUNT 비밀 값이 없어요 (안내서 3단계)")
    firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
    db = firestore.client()

    sent = 0
    for user in db.collection("users").list_documents():
        push_ref = user.collection("data").document("push")
        push = push_ref.get().to_dict() or {}
        tokens = push.get("tokens") or []
        if not push.get("enabled") or not tokens:
            continue
        tt = user.collection("data").document("timetable").get().to_dict() or {}
        title, body = compose(tt)
        dead = []
        for tok in tokens:
            msg = messaging.Message(token=tok, webpush=messaging.WebpushConfig(
                headers={"Urgency": "high", "TTL": "43200"},
                data={"title": title, "body": body, "tag": "naui-morning"}))
            try:
                messaging.send(msg)
                sent += 1
            except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
                dead.append(tok)
            except Exception as ex:  # 다른 오류는 기록만
                print("보내기 실패:", type(ex).__name__, ex)
        if dead:
            push_ref.update({"tokens": firestore.ArrayRemove(dead)})
            print(f"만료된 기기 {len(dead)}개 정리")
        print(title)
        print(body)
    print(f"보낸 알림: {sent}개")


if __name__ == "__main__":
    main()
