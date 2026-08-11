#!/usr/bin/env python3
"""
매일 발행 시각을 '고정'이 아니라 그날그날 다르게 만들기 위한 게이트.

동작 방식:
  - 오늘 날짜(KST)를 시드로 목표 발행 시각(시:분)을 하나 정한다.
    같은 날 여러 번 실행돼도 항상 같은 목표 시각이 나오므로 상태 파일이 필요 없다.
  - 워크플로우는 매시 정각에 이 스크립트를 실행하고, 현재 시각이 목표 '시'와
    같을 때만 종료 코드 0(진행)을 반환한다. 그 외에는 1(건너뜀)을 반환한다.
  - 목표 시가 되면 목표 '분'까지 남은 시간만큼 랜덤하게 대기했다가 발행하도록
    WAIT_SECONDS 를 표준출력에 함께 남긴다 (워크플로우에서 sleep 에 사용).

이렇게 하면 매일 07:00~23:00(KST) 사이 임의의 시:분에 글이 올라가고,
매일 정확히 같은 시각(예: 08:00)에 반복되지 않아 '봇처럼' 보이지 않는다.
"""
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 실제 사람이 글을 올릴 법한 시간대로 제한 (심야 발행은 오히려 부자연스러움)
START_HOUR = 7
END_HOUR = 23  # 이 시각 미포함 (즉 22:59까지)


def target_time_for(date_str: str):
    seed = hashlib.sha256(date_str.encode()).hexdigest()
    n = int(seed[:12], 16)
    span = END_HOUR - START_HOUR
    hour = START_HOUR + (n % span)
    minute = (n // span) % 60
    return hour, minute


def main():
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    hour, minute = target_time_for(today)

    print(f"오늘({today}) 목표 발행 시각: {hour:02d}:{minute:02d} (KST) / 현재: {now.strftime('%H:%M')}")

    if now.hour != hour:
        print("목표 시각이 아님 - 이번 실행은 건너뜀")
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write("should_publish=false\n")
        sys.exit(1)

    # 목표 '분'까지 남은 시간만큼 대기 (0~59분 사이 랜덤 지연 효과)
    wait_seconds = max(0, minute * 60 - now.minute * 60 - now.second)
    print(f"목표 시각 도달 - {wait_seconds}초 대기 후 발행")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write("should_publish=true\n")
            f.write(f"wait_seconds={wait_seconds}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
