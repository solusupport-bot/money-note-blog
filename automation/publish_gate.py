#!/usr/bin/env python3
"""
매일 발행 시각을 '고정'이 아니라 그날그날 다르게 만들기 위한 게이트.

동작 방식:
  - 오늘 날짜(KST)를 시드로 목표 발행 시각(시:분)을 하나 정한다.
    같은 날 여러 번 실행돼도 항상 같은 목표 시각이 나오므로 상태 파일이 필요 없다.
  - 워크플로우는 매시 정각에 이 스크립트를 실행한다.
    목표 시각이 아직 안 됐으면 건너뛰고, 목표 시각이 지났는데 오늘 날짜로
    아직 발행된 글이 없다면 "따라잡기(catch-up)"로 즉시 발행한다.
    이미 오늘 발행된 글이 있으면 두 번 발행하지 않도록 건너뛴다.

    (GitHub Actions의 예약 실행(schedule)은 정시 보장이 안 되고 특정 시간대가
    통째로 밀리거나 빠질 수 있다 — 예전엔 "현재 시 == 목표 시"일 때만 발행해서,
    그 시간대에 실행 자체가 없으면 그날은 영영 발행이 안 되는 문제가 있었다.
    지금은 "목표 시각을 지났고 아직 오늘 발행 안 됐으면 바로 발행"으로 바뀌어
    이런 누락을 스스로 만회한다.)

이렇게 하면 매일 07:00~23:00(KST) 사이 임의의 시:분에 글이 올라가고,
매일 정확히 같은 시각(예: 08:00)에 반복되지 않아 '봇처럼' 보이지 않는다.
"""
import hashlib
import os
import re
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 실제 사람이 글을 올릴 법한 시간대로 제한 (심야 발행은 오히려 부자연스러움)
START_HOUR = 7
END_HOUR = 23  # 이 시각 미포함 (즉 22:59까지)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(BASE, "content", "posts")


def target_time_for(date_str: str):
    seed = hashlib.sha256(date_str.encode()).hexdigest()
    n = int(seed[:12], 16)
    span = END_HOUR - START_HOUR
    hour = START_HOUR + (n % span)
    minute = (n // span) % 60
    return hour, minute


def already_published_today(today: str) -> bool:
    if not os.path.isdir(POSTS):
        return False
    for fn in os.listdir(POSTS):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS, fn), encoding="utf-8") as f:
            head = f.read(500)
        m = re.search(r"(?m)^date:\s*(\S+)", head)
        if m and m.group(1) == today:
            return True
    return False


def emit(should_publish: bool, wait_seconds: int = 0):
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"should_publish={'true' if should_publish else 'false'}\n")
            if should_publish:
                f.write(f"wait_seconds={wait_seconds}\n")


def main():
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    hour, minute = target_time_for(today)

    print(f"오늘({today}) 목표 발행 시각: {hour:02d}:{minute:02d} (KST) / 현재: {now.strftime('%H:%M')}")

    if already_published_today(today):
        print("오늘 이미 발행됨 - 건너뜀")
        emit(False)
        sys.exit(1)

    if now.hour < hour:
        print("아직 목표 시각 전 - 건너뜀")
        emit(False)
        sys.exit(1)

    if now.hour == hour:
        # 목표 '분'까지 남은 시간만큼 대기 (0~59분 사이 랜덤 지연 효과)
        wait_seconds = max(0, minute * 60 - now.minute * 60 - now.second)
        print(f"목표 시각 도달 - {wait_seconds}초 대기 후 발행")
    else:
        # 목표 시각이 지났는데 아직 발행 안 됨 - 실행이 밀렸던 것이므로 바로 따라잡기
        wait_seconds = 0
        print("목표 시각을 이미 지남 - 예약 실행 누락 감지, 즉시 따라잡기 발행")

    emit(True, wait_seconds)
    sys.exit(0)


if __name__ == "__main__":
    main()
