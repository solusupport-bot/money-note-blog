#!/usr/bin/env python3
"""
카테고리별 원본 SVG 배너를 코드로 직접 그려서 만든다.
외부 스톡사진을 가져오지 않는 이유: (1) 저작권 문제를 원천 차단하고
(2) 완전 자동화가 가능하며 (3) 사이트 톤앤매너(브랜드 색상)와 항상 일치시키기 위함.
"""
import html

CATEGORY_SLUGS = {
    "생활비 절약": "saving",
    "청년·정부지원금": "youth-support",
    "통장·예적금": "banking",
    "세금·연말정산": "tax",
    "구독·통신비 관리": "subscription",
}

# 240x240 뷰포트(translate 80,80 기준) 안에 그리는 단순 라인 아이콘.
_ICONS = {
    "saving": """
      <circle cx="60" cy="180" r="55" fill="none" stroke="#ffffff" stroke-width="8"/>
      <circle cx="60" cy="180" r="26" fill="none" stroke="#ffffff" stroke-width="4" opacity="0.55"/>
      <circle cx="150" cy="150" r="55" fill="none" stroke="#ffffff" stroke-width="8"/>
      <circle cx="150" cy="150" r="26" fill="none" stroke="#ffffff" stroke-width="4" opacity="0.55"/>
    """,
    "youth-support": """
      <polygon points="0,55 120,5 240,55 120,105" fill="#ffffff"/>
      <rect x="106" y="55" width="28" height="65" fill="#ffffff"/>
      <circle cx="120" cy="145" r="9" fill="#ffffff"/>
    """,
    "banking": """
      <rect x="20" y="20" width="180" height="180" rx="20" fill="none" stroke="#ffffff" stroke-width="10"/>
      <circle cx="110" cy="110" r="38" fill="none" stroke="#ffffff" stroke-width="8"/>
      <line x1="110" y1="110" x2="110" y2="78" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
      <line x1="110" y1="110" x2="138" y2="110" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
    """,
    "tax": """
      <rect x="30" y="10" width="160" height="200" rx="12" fill="none" stroke="#ffffff" stroke-width="8"/>
      <line x1="55" y1="60" x2="165" y2="60" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
      <line x1="55" y1="100" x2="165" y2="100" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
      <line x1="55" y1="140" x2="130" y2="140" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
    """,
    "subscription": """
      <path d="M20,150 Q120,40 220,150" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round"/>
      <path d="M55,168 Q120,95 185,168" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round"/>
      <circle cx="120" cy="196" r="14" fill="#ffffff"/>
    """,
    "site": """
      <circle cx="120" cy="110" r="95" fill="none" stroke="#ffffff" stroke-width="10"/>
      <text x="120" y="140" font-family="'Segoe UI','Noto Sans KR',sans-serif" font-size="110"
            font-weight="800" fill="#ffffff" text-anchor="middle">₩</text>
    """,
}


def slug_for(category: str) -> str:
    return CATEGORY_SLUGS.get(category, "site")


def svg_banner(category: str, site_name: str) -> str:
    slug = slug_for(category)
    icon = _ICONS.get(slug, _ICONS["site"])
    label = html.escape(category if slug != "site" else site_name)
    sub = html.escape(site_name)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400"
     role="img" aria-label="{label}">
  <defs>
    <linearGradient id="g-{slug}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d7d5a"/>
      <stop offset="100%" stop-color="#14a37a"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="400" fill="url(#g-{slug})"/>
  <g transform="translate(80,80)">{icon}</g>
  <text x="80" y="330" font-family="'Segoe UI','Noto Sans KR',sans-serif" font-size="52"
        font-weight="800" fill="#ffffff">{label}</text>
  <text x="80" y="368" font-family="'Segoe UI','Noto Sans KR',sans-serif" font-size="22"
        fill="#d7f0e6">{sub}</text>
</svg>
'''
