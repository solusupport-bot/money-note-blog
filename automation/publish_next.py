#!/usr/bin/env python3
"""
content/drafts/ 에 미리 완성해둔 원고 중 다음 순번(파일명 정렬 기준)을 골라
content/posts/ 로 옮기고 날짜를 오늘 날짜로 갱신한다.

자동화가 '글을 즉석에서 지어내지' 않고, 미리 검수·완성된 원고만 발행하도록
하기 위한 스크립트다. new_post.py 는 초안 뼈대를 만들 때만 수동으로 쓰고,
실제 예약 발행 파이프라인은 이 스크립트를 사용한다.

사용법:
  python3 publish_next.py
"""
import os
import re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(BASE, "content", "drafts")
POSTS = os.path.join(BASE, "content", "posts")


def main():
    os.makedirs(DRAFTS, exist_ok=True)
    os.makedirs(POSTS, exist_ok=True)

    files = sorted(f for f in os.listdir(DRAFTS) if f.endswith(".md"))
    if not files:
        print("발행할 완성 원고가 없습니다. content/drafts 에 원고를 추가하세요.")
        return

    fn = files[0]
    src = os.path.join(DRAFTS, fn)
    with open(src, encoding="utf-8") as f:
        text = f.read()

    today = datetime.now().strftime("%Y-%m-%d")
    if re.search(r"(?m)^date:.*$", text):
        text = re.sub(r"(?m)^date:.*$", f"date: {today}", text, count=1)

    slug_match = re.search(r"(?m)^slug:\s*(.+)$", text)
    slug = slug_match.group(1).strip() if slug_match else re.sub(r"^\d+-", "", fn)[:-3]

    dst = os.path.join(POSTS, f"{slug}.md")
    if os.path.exists(dst):
        print(f"이미 발행됨: {dst} (건너뜀)")
        os.remove(src)
        return

    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    os.remove(src)

    print(f"발행 완료: {fn} -> content/posts/{slug}.md (date={today})")


if __name__ == "__main__":
    main()
