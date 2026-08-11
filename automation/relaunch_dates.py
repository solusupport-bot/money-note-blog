#!/usr/bin/env python3
"""
도메인을 실제로 연결하는 '런칭 당일' 딱 한 번 실행하는 스크립트.

목적: 지금 content/posts 에 있는 글들의 날짜가 실제 도메인 생성일보다
앞서 있으면(백데이트), 애드센스 심사에서 "발행일·사이트 생성일 불일치"로
의심받을 수 있다. 이 스크립트는 그 글들을 전부 '오늘(=도메인 생성일)'
하나의 날짜로 재설정해서, 도메인 나이와 콘텐츠 이력이 항상 일치하도록
만든다. 이후 매일 발행되는 글은 publish_next.py 가 그날 날짜를 그대로
쓰므로 별도 조치가 필요 없다.

사용법:
  python3 relaunch_dates.py                # 오늘 날짜로 전체 재설정
  python3 relaunch_dates.py 2026-08-12     # 특정 날짜로 재설정 (예: 도메인 등록일)
"""
import os
import re
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(BASE, "content", "posts")


def main():
    launch_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(launch_date, "%Y-%m-%d")
    except ValueError:
        print(f"날짜 형식이 잘못됐습니다: {launch_date} (YYYY-MM-DD 형식으로 입력)")
        return

    if not os.path.isdir(POSTS):
        print("content/posts 디렉터리가 없습니다.")
        return

    changed = 0
    for fn in sorted(os.listdir(POSTS)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(POSTS, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new_text, n = re.subn(r"(?m)^date:.*$", f"date: {launch_date}", text, count=1)
        if n:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            changed += 1
            print(f"  {fn} -> date: {launch_date}")

    print(f"\n총 {changed}개 글의 발행일을 {launch_date}(런칭일)로 통일했습니다.")
    print("→ 이제 'python3 build.py' 로 다시 빌드한 뒤 커밋/배포하세요.")
    print("→ 이후 매일 자동 발행되는 글은 publish_next.py 가 그날 실제 날짜를 사용하니 추가 조치가 필요 없습니다.")


if __name__ == "__main__":
    main()
