#!/usr/bin/env python3
"""
알뜰살뜰 머니노트 - 정적 블로그 빌드 엔진 (표준 라이브러리만 사용)

역할:
  1) content/posts/*.md (프론트매터 + 마크다운) 를 읽는다
  2) 각 글을 HTML 로 변환해 site/posts/<slug>.html 로 저장
  3) 홈(index), 소개/개인정보처리방침/문의 등 애드센스 필수 페이지 생성
  4) sitemap.xml, robots.txt, ads.txt, style.css 생성

사용법:
  python3 build.py            # 전체 사이트 빌드
"""
import json
import os
import re
import html
from datetime import datetime, timezone
from urllib.parse import urlsplit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTO = os.path.join(BASE, "automation")
POSTS_SRC = os.path.join(BASE, "content", "posts")
SITE = os.path.join(BASE, "site")
POSTS_OUT = os.path.join(SITE, "posts")


def load_config():
    with open(os.path.join(AUTO, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    # base_url 에 하위 경로가 포함돼 있으면(예: 커스텀 도메인 연결 전
    # https://user.github.io/repo 형태) 사이트 내부 링크에도 그 경로를
    # 붙여줘야 깨지지 않는다. 커스텀 도메인 루트라면 빈 문자열이 된다.
    cfg["_prefix"] = urlsplit(cfg["base_url"]).path.rstrip("/")
    return cfg


# ---------- 프론트매터 파서 ----------
def parse_front_matter(text):
    """--- 로 감싼 key: value 블록과 본문을 분리."""
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip()
            body = text[end + 4:].lstrip("\n")
            for line in block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


# ---------- 최소 마크다운 → HTML 변환 ----------
def inline(text):
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" rel="noopener">\1</a>', text)
    return text


def md_to_html(md):
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        # 구분선
        if re.match(r"^---+$", s):
            out.append("<hr>")
            i += 1
            continue
        # 헤딩
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        # 인용
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(buf))}</blockquote>")
            continue
        # 표
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in header)
            body = ""
            for r in rows:
                body += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>")
            continue
        # 순서 목록
        if re.match(r"^\d+\.\s+", s):
            buf = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                buf.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in buf) + "</ol>")
            continue
        # 비순서 목록
        if re.match(r"^[-*]\s+", s):
            buf = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                buf.append(re.sub(r"^[-*]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in buf) + "</ul>")
            continue
        # 일반 문단
        buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,4}\s|>|\||[-*]\s|\d+\.\s|---+$)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")
    return "\n".join(out)


# ---------- 공통 레이아웃 ----------
def page(cfg, title, description, body, canonical, is_post=False):
    p = cfg["_prefix"]  # 커스텀 도메인 루트면 "", 프로젝트 하위 경로면 "/repo명"
    adsense = ""
    if cfg.get("adsense_client") and not cfg["adsense_client"].endswith("0000"):
        adsense = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
                   f'adsbygoogle.js?client={cfg["adsense_client"]}" crossorigin="anonymous"></script>')
    nav = (
        f'<a href="{p}/index.html">홈</a>'
        f'<a href="{p}/about.html">소개</a>'
        f'<a href="{p}/privacy.html">개인정보처리방침</a>'
        f'<a href="{p}/contact.html">문의</a>'
    )
    year = datetime.now().year
    return f"""<!doctype html>
<html lang="{cfg['language']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | {html.escape(cfg['site_name'])}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="{p}/style.css">
{adsense}
</head>
<body>
<header class="site-header">
  <a class="brand" href="{p}/index.html">{html.escape(cfg['site_name'])}</a>
  <p class="tagline">{html.escape(cfg['site_tagline'])}</p>
  <nav>{nav}</nav>
</header>
<main class="{'post' if is_post else 'page'}">
{body}
</main>
<footer class="site-footer">
  <p>&copy; {year} {html.escape(cfg['site_name'])}. 본 블로그의 정보는 일반적인 참고용이며 투자·법률·세무 자문이 아닙니다.</p>
  <p><a href="{p}/about.html">소개</a> · <a href="{p}/privacy.html">개인정보처리방침</a> · <a href="{p}/contact.html">문의</a></p>
</footer>
</body>
</html>
"""


def read_posts():
    posts = []
    if not os.path.isdir(POSTS_SRC):
        return posts
    for fn in os.listdir(POSTS_SRC):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS_SRC, fn), encoding="utf-8") as f:
            meta, body = parse_front_matter(f.read())
        meta.setdefault("slug", fn[:-3])
        meta.setdefault("title", meta["slug"])
        meta.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
        meta.setdefault("category", "생활비 절약")
        meta.setdefault("description", meta["title"])
        meta["_body_html"] = md_to_html(body)
        meta["_reading"] = max(1, len(body) // 500)
        posts.append(meta)
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def build():
    cfg = load_config()
    os.makedirs(POSTS_OUT, exist_ok=True)
    posts = read_posts()
    base = cfg["base_url"].rstrip("/")
    prefix = cfg["_prefix"]

    # 개별 글
    for p in posts:
        article = (
            f'<article>'
            f'<p class="meta"><span class="cat">{html.escape(p["category"])}</span>'
            f' · {p["date"]} · 읽는 시간 약 {p["_reading"]}분</p>'
            f'<h1>{html.escape(p["title"])}</h1>'
            f'{p["_body_html"]}'
            f'</article>'
            f'<p class="back"><a href="{prefix}/index.html">← 목록으로</a></p>'
        )
        out = page(cfg, p["title"], p["description"], article,
                   f'{base}/posts/{p["slug"]}.html', is_post=True)
        with open(os.path.join(POSTS_OUT, f'{p["slug"]}.html'), "w", encoding="utf-8") as f:
            f.write(out)

    # 홈
    cards = ""
    for p in posts:
        cards += (
            f'<a class="card" href="{prefix}/posts/{p["slug"]}.html">'
            f'<span class="cat">{html.escape(p["category"])}</span>'
            f'<h2>{html.escape(p["title"])}</h2>'
            f'<p>{html.escape(p["description"])}</p>'
            f'<span class="date">{p["date"]}</span>'
            f'</a>'
        )
    intro = (f'<section class="hero"><h1>{html.escape(cfg["site_name"])}</h1>'
             f'<p>{html.escape(cfg["site_tagline"])}</p></section>'
             f'<section class="grid">{cards or "<p>아직 글이 없습니다.</p>"}</section>')
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(cfg, "홈", cfg["site_tagline"], intro, f"{base}/index.html"))

    # 정적 페이지
    write_static_pages(cfg, base)

    # 사이트맵 / robots / ads
    write_sitemap(cfg, base, posts)
    write_robots(base)
    write_ads(cfg)
    write_css()

    print(f"빌드 완료: 글 {len(posts)}개 + 필수 페이지 4개 생성")
    print(f"결과물 위치: {SITE}")


def write_static_pages(cfg, base):
    prefix = cfg["_prefix"]
    about = f"""
<h1>블로그 소개</h1>
<p><strong>{html.escape(cfg['site_name'])}</strong>는 평범한 직장인과 사회초년생이 '새는 돈'을 막고
꾸준히 자산을 모을 수 있도록 실전 생활 재테크 정보를 정리하는 블로그입니다.</p>
<p>저희는 광고성 과장 없이, 직접 확인하고 계산한 내용만을 다룹니다. 다루는 주제는 다음과 같습니다.</p>
<ul>
{''.join(f'<li>{html.escape(c)}</li>' for c in cfg['categories'])}
</ul>
<h2>운영 원칙</h2>
<ul>
<li>모든 글은 독자에게 실질적으로 도움이 되는 정보 제공을 목적으로 합니다.</li>
<li>특정 금융상품 가입을 권유하지 않으며, 수치·제도는 공개된 자료를 근거로 합니다.</li>
<li>제도·금리 등은 시점에 따라 달라질 수 있어, 중요한 결정 전 공식 기관 확인을 권합니다.</li>
</ul>
<h2>운영자</h2>
<p>{html.escape(cfg['author'])} · 문의: <a href="{prefix}/contact.html">문의 페이지</a></p>
"""
    privacy = f"""
<h1>개인정보처리방침</h1>
<p>{html.escape(cfg['site_name'])}(이하 '본 사이트')는 이용자의 개인정보를 소중히 여기며 관련 법령을 준수합니다.
본 방침은 {datetime.now().strftime('%Y년 %m월 %d일')}부터 적용됩니다.</p>
<h2>1. 수집하는 정보</h2>
<p>본 사이트는 회원가입 기능이 없으며 이름·연락처 등 개인정보를 직접 수집하지 않습니다.
다만 방문 통계 및 광고 제공을 위해 쿠키를 통한 비식별 정보(브라우저 종류, 방문 페이지 등)가 수집될 수 있습니다.</p>
<h2>2. 쿠키 및 광고</h2>
<p>본 사이트는 Google AdSense 등 제3자 광고를 게재할 수 있습니다. Google을 포함한 제3자 공급업체는
쿠키를 사용해 이용자의 이전 방문 기록을 바탕으로 광고를 게재합니다. 이용자는
<a href="https://www.google.com/settings/ads" rel="noopener">Google 광고 설정</a>에서 맞춤 광고를 해제할 수 있습니다.</p>
<h2>3. 로그 분석</h2>
<p>Google Analytics 등 분석 도구가 사용될 수 있으며, 이는 통계 목적의 비식별 데이터입니다.</p>
<h2>4. 문의</h2>
<p>개인정보 관련 문의는 <a href="mailto:{html.escape(cfg['email'])}">{html.escape(cfg['email'])}</a> 로 연락 주시기 바랍니다.</p>
"""
    contact = f"""
<h1>문의하기</h1>
<p>제휴, 정정 요청, 정보 오류 신고 등 어떤 문의든 환영합니다.</p>
<ul>
<li>이메일: <a href="mailto:{html.escape(cfg['email'])}">{html.escape(cfg['email'])}</a></li>
<li>운영자: {html.escape(cfg['author'])}</li>
</ul>
<p>영업일 기준 2~3일 내 회신드립니다. 특정 상품 가입 여부에 대한 개별 자문은 제공하지 않는 점 양해 부탁드립니다.</p>
"""
    for name, title, body in [
        ("about", "소개", about),
        ("privacy", "개인정보처리방침", privacy),
        ("contact", "문의", contact),
    ]:
        with open(os.path.join(SITE, f"{name}.html"), "w", encoding="utf-8") as f:
            f.write(page(cfg, title, f"{title} - {cfg['site_name']}", body, f"{base}/{name}.html"))


def write_sitemap(cfg, base, posts):
    urls = ["", "about.html", "privacy.html", "contact.html"]
    urls += [f"posts/{p['slug']}.html" for p in posts]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    body = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        loc = f"{base}/{u}" if u else f"{base}/"
        body += f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod></url>\n"
    body += "</urlset>\n"
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(body)


def write_robots(base):
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")


def write_ads(cfg):
    # 애드센스 승인/게시자 확인용. 승인 후 실제 pub 번호로 교체하세요.
    pub = cfg.get("adsense_client", "").replace("ca-", "")
    with open(os.path.join(cfg_site(), "ads.txt"), "w", encoding="utf-8") as f:
        f.write(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")


def cfg_site():
    return SITE


def write_css():
    css = """:root{--fg:#1f2328;--muted:#6b7280;--bg:#ffffff;--soft:#f6f7f9;--brand:#0d7d5a;--line:#e5e7eb}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;color:var(--fg);background:var(--bg);line-height:1.75}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}
.site-header{border-bottom:1px solid var(--line);padding:28px 20px;text-align:center}
.brand{font-size:1.6rem;font-weight:800;color:var(--fg)}
.tagline{color:var(--muted);margin:6px 0 14px}
nav a{margin:0 10px;font-weight:600}
main{max-width:760px;margin:0 auto;padding:28px 20px}
.hero{text-align:center;padding:24px 0 8px}
.hero h1{font-size:1.9rem;margin:.2em 0}
.grid{display:grid;grid-template-columns:1fr;gap:16px;margin-top:20px}
@media(min-width:640px){.grid{grid-template-columns:1fr 1fr}}
.card{display:block;border:1px solid var(--line);border-radius:14px;padding:18px;background:var(--soft);transition:.15s}
.card:hover{transform:translateY(-2px);text-decoration:none;box-shadow:0 6px 20px rgba(0,0,0,.06)}
.card h2{font-size:1.12rem;margin:8px 0}
.card p{color:var(--muted);font-size:.94rem;margin:6px 0}
.cat{display:inline-block;font-size:.75rem;font-weight:700;color:var(--brand);background:#e7f5ef;padding:3px 9px;border-radius:999px}
.date{font-size:.8rem;color:var(--muted)}
.post h1{font-size:1.7rem;line-height:1.35}
.post h2{margin-top:1.6em;border-left:4px solid var(--brand);padding-left:10px}
.post .meta{color:var(--muted);font-size:.88rem}
.post table{width:100%;border-collapse:collapse;margin:1.2em 0}
.post th,.post td{border:1px solid var(--line);padding:9px 11px;text-align:left}
.post th{background:var(--soft)}
blockquote{border-left:4px solid var(--line);margin:1.2em 0;padding:4px 16px;color:var(--muted);background:var(--soft)}
.back{margin-top:32px}
.site-footer{border-top:1px solid var(--line);margin-top:40px;padding:24px 20px;text-align:center;color:var(--muted);font-size:.85rem}
.site-footer a{color:var(--muted)}
"""
    with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8") as f:
        f.write(css)


if __name__ == "__main__":
    build()
