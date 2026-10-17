#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
posts/*.md を読んで docs/ 以下に静的サイトを生成する。
使い方:  python3 build.py
依存ライブラリなし（Python 3.8以上があれば動く）
"""

import html
import os
import re
import shutil
from datetime import datetime, timezone, timedelta

# ============================================================
# ここを書き換えるとサイトの表示が変わります
# ============================================================
CONFIG = {
    "site_name": "hohemaro15",
    "tagline": "ラグビー20年、不動産1棟。調べてから書く記録",
    "description": "ラグビー・不動産投資・健康・子育て。20年分の経験を、制度や統計と突き合わせて書き残しています。",
    "author": "hohemaro15",
    "note_url": "https://note.com/hohemaro15",
    # 公開後のURL（GitHub Pagesのアドレス）。分かったら書き換える
    "base_url": "https://taishiiwamoto.github.io/denki1",
    "profile": [
        "小学5年でラグビーを始めて、大学まで20年続けた。大阪の激戦区で6年、同志社大で4年。ポジションはユーティリティバックス。",
        "今はメーカーで設備の電気を担当しながら、兵庫県尼崎市に木造9戸の一棟アパートを運用している。2児の父。",
        "経験談だけで終わらせないために、書く前に必ず制度と統計を調べることにしている。数字が確認できなかった話は書かない。",
    ],
    "pillars": [
        ("ラグビー", "小5から大学まで20年。大阪の激戦区で見たこと、カテゴリが上がるたびに起きたこと。"),
        ("不動産・資産運用", "2016年に検討を始めて2026年に1棟目。判断基準と、断り続けた10年の話。"),
        ("健康・トレーニング", "増量の失敗と成功、サプリで肝臓の数値を悪くした経験、続けている設計。"),
        ("子育て・家族", "2歳と0歳を育てながらの時間の使い方と、資産形成の時間軸。"),
    ],
}

ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(ROOT, "posts")
OUT_DIR = os.path.join(ROOT, "docs")
JST = timezone(timedelta(hours=9))


# ------------------------------------------------------------
# Markdown の読み込み
# ------------------------------------------------------------
def parse_front_matter(text):
    """先頭の --- で囲まれたメタ情報を辞書にする"""
    meta = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def inline(text):
    """段落内の記法（太字・リンク）を変換する"""
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def md_to_html(body):
    """見出しと段落だけの、記事に必要な最小限の変換"""
    out = []
    for block in re.split(r"\n\s*\n", body.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("### "):
            out.append("<h3>%s</h3>" % inline(block[4:].strip()))
        elif block.startswith("## "):
            out.append("<h2>%s</h2>" % inline(block[3:].strip()))
        elif block.startswith("> "):
            lines = [inline(l[2:].strip()) for l in block.splitlines()]
            out.append("<blockquote><p>%s</p></blockquote>" % "<br>".join(lines))
        else:
            out.append("<p>%s</p>" % "<br>".join(inline(l) for l in block.splitlines()))
    return "\n".join(out)


def load_posts():
    posts = []
    if not os.path.isdir(POSTS_DIR):
        return posts
    for name in sorted(os.listdir(POSTS_DIR)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(POSTS_DIR, name)
        with open(path, encoding="utf-8") as f:
            meta, body = parse_front_matter(f.read())
        raw = meta.get("date", "")
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                dt = datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                dt = datetime.fromtimestamp(os.path.getmtime(path))
        dt = dt.replace(tzinfo=JST)
        text = re.sub(r"[#*\[\]()]", "", body)
        plain = re.sub(r"\s+", "", text)
        posts.append({
            "slug": os.path.splitext(name)[0],
            "title": meta.get("title", "(無題)"),
            "category": meta.get("category", "その他"),
            "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
            "note": meta.get("note", ""),
            "date": dt,
            "html": md_to_html(body),
            "excerpt": body.strip().split("\n\n")[0].strip()[:110],
            "chars": len(plain),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


# ------------------------------------------------------------
# HTML の組み立て
# ------------------------------------------------------------
def page(title, body, description="", rel="", active="", ogimg="icon.png"):
    nav = [("ホーム", rel + "index.html", "home"),
           ("記事一覧", rel + "posts/index.html", "posts")]
    links = "".join(
        '<a href="%s"%s>%s</a>' % (url, ' class="on"' if key == active else "", label)
        for label, url, key in nav
    )
    return """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:type" content="website">
<link rel="alternate" type="application/rss+xml" title="%(site)s" href="%(rel)sfeed.xml">
<link rel="icon" type="image/png" href="%(rel)sassets/img/icon.png">
<link rel="apple-touch-icon" href="%(rel)sassets/img/icon.png">
<meta property="og:image" content="%(rel)sassets/img/%(ogimg)s">
<link rel="stylesheet" href="%(rel)sassets/style.css">
</head>
<body>
<header class="site-head">
  <a class="brand" href="%(rel)sindex.html">%(site)s</a>
  <nav>%(nav)s</nav>
</header>
<main>
%(body)s
</main>
<footer class="site-foot">
  <p><a href="%(note)s">note</a> ・ <a href="%(rel)sfeed.xml">RSS</a></p>
  <p class="muted">&copy; %(year)s %(author)s</p>
</footer>
</body>
</html>
""" % {
        "title": html.escape(title),
        "desc": html.escape(description or CONFIG["description"]),
        "site": html.escape(CONFIG["site_name"]),
        "nav": links,
        "body": body,
        "rel": rel,
        "note": CONFIG["note_url"],
        "year": datetime.now(JST).year,
        "author": html.escape(CONFIG["author"]),
        "ogimg": ogimg,
    }


def card(p, rel):
    return """<li class="card">
  <a class="card-link" href="%(rel)sposts/%(slug)s.html">
    <img class="thumb" src="%(rel)sassets/img/%(slug)s.png" alt="" loading="lazy">
    <span class="cat">%(cat)s</span>
    <h3>%(title)s</h3>
    <p class="excerpt">%(ex)s…</p>
    <span class="meta">%(date)s ・ 約%(chars)s字</span>
  </a>
</li>""" % {
        "rel": rel,
        "slug": p["slug"],
        "cat": html.escape(p["category"]),
        "title": html.escape(p["title"]),
        "ex": html.escape(p["excerpt"]),
        "date": p["date"].strftime("%Y年%-m月%-d日") if os.name != "nt" else p["date"].strftime("%Y年%m月%d日"),
        "chars": "{:,}".format(p["chars"]),
    }


def build_index(posts):
    latest = "".join(card(p, "") for p in posts[:6])
    pillars = "".join(
        "<li><h3>%s</h3><p>%s</p></li>" % (html.escape(t), html.escape(d))
        for t, d in CONFIG["pillars"]
    )
    profile = "".join("<p>%s</p>" % html.escape(t) for t in CONFIG["profile"])
    body = """<section class="hero">
  <h1>%(name)s</h1>
  <p class="tagline">%(tag)s</p>
</section>

<section class="block">
  <h2>このサイトについて</h2>
  %(profile)s
</section>

<section class="block">
  <h2>書いていること</h2>
  <ul class="pillars">%(pillars)s</ul>
</section>

<section class="block">
  <h2>最近の記事</h2>
  <ul class="cards">%(latest)s</ul>
  <p class="more"><a href="posts/index.html">記事をすべて見る（%(n)s本）</a></p>
</section>
""" % {
        "name": html.escape(CONFIG["site_name"]),
        "tag": html.escape(CONFIG["tagline"]),
        "profile": profile,
        "pillars": pillars,
        "latest": latest,
        "n": len(posts),
    }
    return page(CONFIG["site_name"] + " | " + CONFIG["tagline"], body, rel="", active="home")


def build_archive(posts):
    groups = {}
    for p in posts:
        groups.setdefault(p["category"], []).append(p)
    order = [c for c, _ in CONFIG["pillars"]] + sorted(set(groups) - {c for c, _ in CONFIG["pillars"]})
    sections = []
    for cat in order:
        if cat not in groups:
            continue
        items = "".join(card(p, "../") for p in groups[cat])
        sections.append('<h2 id="%s">%s<span class="count">%d</span></h2><ul class="cards">%s</ul>'
                        % (html.escape(cat), html.escape(cat), len(groups[cat]), items))
    body = '<section class="hero small"><h1>記事一覧</h1><p class="tagline">全%d本</p></section>%s' \
           % (len(posts), "".join(sections))
    return page("記事一覧 | " + CONFIG["site_name"], body, rel="../", active="posts")


def build_post(p, prev_post, next_post):
    tags = "".join('<span class="tag">#%s</span>' % html.escape(t) for t in p["tags"])
    note = ('<p class="note-link">この記事は <a href="%s">note</a> にも掲載しています。</p>' % p["note"]) if p["note"] else ""
    nav = []
    if next_post:
        nav.append('<a class="pn" href="%s.html"><span>前の記事</span>%s</a>'
                   % (next_post["slug"], html.escape(next_post["title"])))
    if prev_post:
        nav.append('<a class="pn" href="%s.html"><span>次の記事</span>%s</a>'
                   % (prev_post["slug"], html.escape(prev_post["title"])))
    body = """<article class="post">
  <img class="hero" src="../assets/img/%(slug)s.png" alt="">
  <span class="cat">%(cat)s</span>
  <h1>%(title)s</h1>
  <p class="meta">%(date)s ・ 約%(chars)s字</p>
  <div class="body">%(html)s</div>
  <p class="tags">%(tags)s</p>
  %(note)s
</article>
<nav class="prevnext">%(nav)s</nav>
""" % {
        "slug": p["slug"],
        "cat": html.escape(p["category"]),
        "title": html.escape(p["title"]),
        "date": p["date"].strftime("%Y年%m月%d日"),
        "chars": "{:,}".format(p["chars"]),
        "html": p["html"],
        "tags": tags,
        "note": note,
        "nav": "".join(nav),
    }
    return page(p["title"] + " | " + CONFIG["site_name"], body, description=p["excerpt"], rel="../", active="posts", ogimg=p["slug"] + ".png")


def build_feed(posts):
    base = CONFIG["base_url"].rstrip("/")
    items = []
    for p in posts[:20]:
        items.append("""  <item>
    <title>%s</title>
    <link>%s/posts/%s.html</link>
    <guid>%s/posts/%s.html</guid>
    <pubDate>%s</pubDate>
    <description>%s</description>
  </item>""" % (html.escape(p["title"]), base, p["slug"], base, p["slug"],
                p["date"].strftime("%a, %d %b %Y %H:%M:%S +0900"), html.escape(p["excerpt"])))
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>%s</title>
  <link>%s/</link>
  <description>%s</description>
  <language>ja</language>
%s
</channel>
</rss>
""" % (html.escape(CONFIG["site_name"]), base, html.escape(CONFIG["description"]), "\n".join(items))


def build_sitemap(posts):
    base = CONFIG["base_url"].rstrip("/")
    urls = ["%s/" % base, "%s/posts/index.html" % base]
    urls += ["%s/posts/%s.html" % (base, p["slug"]) for p in posts]
    body = "".join("  <url><loc>%s</loc></url>\n" % u for u in urls)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % body


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    posts = load_posts()
    if not posts:
        print("posts/ に記事がありません")
        return
    write(os.path.join(OUT_DIR, "index.html"), build_index(posts))
    write(os.path.join(OUT_DIR, "posts", "index.html"), build_archive(posts))
    for i, p in enumerate(posts):
        prev_post = posts[i - 1] if i > 0 else None
        next_post = posts[i + 1] if i + 1 < len(posts) else None
        write(os.path.join(OUT_DIR, "posts", p["slug"] + ".html"), build_post(p, prev_post, next_post))
    write(os.path.join(OUT_DIR, "feed.xml"), build_feed(posts))
    write(os.path.join(OUT_DIR, "sitemap.xml"), build_sitemap(posts))
    write(os.path.join(OUT_DIR, ".nojekyll"), "")
    src = os.path.join(ROOT, "assets", "style.css")
    if os.path.exists(src):
        os.makedirs(os.path.join(OUT_DIR, "assets"), exist_ok=True)
        shutil.copy(src, os.path.join(OUT_DIR, "assets", "style.css"))
    imgsrc = os.path.join(ROOT, "assets", "img")
    if os.path.isdir(imgsrc):
        imgdst = os.path.join(OUT_DIR, "assets", "img")
        os.makedirs(imgdst, exist_ok=True)
        # rmtree はクラウド同期フォルダで権限エラーになることがあるので、
        # 差分コピー（新しいものだけ上書き）にしている
        for name in os.listdir(imgsrc):
            s = os.path.join(imgsrc, name)
            dpath = os.path.join(imgdst, name)
            if not os.path.isfile(s):
                continue
            if (not os.path.exists(dpath)) or os.path.getmtime(s) > os.path.getmtime(dpath):
                shutil.copy2(s, dpath)
    print("生成しました: 記事%d本" % len(posts))
    for p in posts:
        print("  - %s (%s / %s字)" % (p["title"][:34], p["category"], p["chars"]))


if __name__ == "__main__":
    main()
