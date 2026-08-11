#!/usr/bin/env python3
"""
큐(topics.json)에서 다음 대기 주제를 꺼내 원고 뼈대(.md)를 자동 생성한다.
자동화 스케줄러(cron/GitHub Actions)에서 매일 1회 호출하는 것을 상정.

사용법:
  python3 new_post.py            # 큐의 다음 'queued' 주제로 초안 생성
  python3 new_post.py "제목"      # 임의 제목으로 초안 생성
"""
import json
import os
import re
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTO = os.path.join(BASE, "automation")
POSTS = os.path.join(BASE, "content", "posts")


def slugify(title):
    s = re.sub(r"[^\w가-힣]+", "-", title.strip()).strip("-").lower()
    return s[:60] or datetime.now().strftime("post-%Y%m%d%H%M")


def skeleton(title, category):
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    return slug, f"""---
title: {title}
description: {title} - 핵심만 정리한 실전 가이드
date: {today}
category: {category}
slug: {slug}
---

# {title}

도입: 이 글에서 다룰 문제와, 독자가 얻어갈 결론을 2~3문장으로 요약합니다.

## 핵심 요약

- 요점 1
- 요점 2
- 요점 3

## 왜 중요한가

배경과 맥락을 독자 관점에서 설명합니다.

## 실전 방법

1. 단계 1
2. 단계 2
3. 단계 3

## 자주 묻는 질문

> Q. 예상 질문?
> A. 답변.

## 마무리

행동을 유도하는 한 줄과, 관련 글로의 연결을 제안합니다.
"""


def main():
    os.makedirs(POSTS, exist_ok=True)
    title = sys.argv[1] if len(sys.argv) > 1 else None
    category = "생활비 절약"

    tq_path = os.path.join(AUTO, "topics.json")
    data = None
    if not title and os.path.exists(tq_path):
        with open(tq_path, encoding="utf-8") as f:
            data = json.load(f)
        nxt = next((t for t in data["queue"] if t.get("status") == "queued"), None)
        if not nxt:
            print("대기 중인 주제가 없습니다. topics.json 에 주제를 추가하세요.")
            return
        title, category = nxt["title"], nxt["category"]
        nxt["status"] = "drafted"

    slug, content = skeleton(title, category)
    path = os.path.join(POSTS, f"{slug}.md")
    if os.path.exists(path):
        print(f"이미 존재: {path}")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    if data:
        with open(tq_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"초안 생성: {path}")
    print("→ 내용을 채운 뒤 'python3 build.py' 로 사이트를 다시 빌드하세요.")


if __name__ == "__main__":
    main()
