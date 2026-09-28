#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""atlas_gen.py — 《曲线图鉴》生成器

聚合曲线库全部条目 + 资料卡 (gallery.CARDS) + 缩略图，
输出**单文件自包含 HTML**：
  - 本地 KaTeX (physics_courseware/lib/katex) 内联, 公式可渲染
  - 缩略图 base64 内嵌, 按分类分章 + 目录导航 + 即时搜索过滤
  - 收藏 (gallery_favs.json) 条目带 ⭐ 标记
  - @media print 白底版式, 可直接打印成册

用法:  python3 atlas_gen.py [-o 输出路径/曲线图鉴.html]
"""
import argparse
import base64
import html
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
KATEX_DIR = os.path.normpath(
    os.path.join(DIR, '..', 'physics_courseware', 'lib', 'katex'))
DEFAULT_OUT = os.path.join(DIR, 'output', '曲线图鉴.html')
BG = '#0f1117'


# ---------------- KaTeX 内联 ----------------

def embed_katex():
    """返回 (css, js)；KaTeX 缺失时返回 (None, None)"""
    try:
        css = open(os.path.join(KATEX_DIR, 'katex.min.css'),
                   encoding='utf-8').read()
        js = open(os.path.join(KATEX_DIR, 'katex.min.js'),
                  encoding='utf-8').read()
        ar = open(os.path.join(KATEX_DIR, 'contrib', 'auto-render.min.js'),
                  encoding='utf-8').read()
    except OSError as ex:
        print(f'[atlas] KaTeX 读取失败, 公式将以纯文本显示: {ex}')
        return None, None
    # 每个 src 列表只保留 woff2 备选源, 再内嵌为 data URI
    # 注意: minified css 中 src 可能是块内最后声明(无尾分号, 直接跟 }), 需以 [;}] 截止并保留终止符
    def _keep_woff2(m):
        items = [s.strip() for s in m.group(1).split(',')]
        keep = [s for s in items if '.woff2' in s]
        return 'src:' + (keep[0] if keep else items[0]) + m.group(2)

    css = re.sub(r'src:([^;}]+)([;}])', _keep_woff2, css)

    def _woff2(m):
        p = os.path.join(KATEX_DIR, 'fonts', m.group(1) + '.woff2')
        if os.path.exists(p):
            b64 = base64.b64encode(open(p, 'rb').read()).decode()
            return f'url(data:font/woff2;base64,{b64})'
        return m.group(0)

    css = re.sub(r'url\(fonts/([A-Za-z0-9\-_.]+)\.woff2\)', _woff2, css)
    return css, js + '\n' + ar


# ---------------- HTML 组装 ----------------

_CSS = """
* { box-sizing: border-box; }
body { margin:0; background:%s; color:#cdd6f4;
       font-family:"DejaVu Sans","Microsoft YaHei",sans-serif; }
header { padding:28px 36px 14px; border-bottom:1px solid #26283a; }
header h1 { margin:0 0 6px; font-size:26px; color:#89b4fa; }
header .sub { color:#9aa0b4; font-size:13px; }
nav { position:sticky; top:0; z-index:9; background:#13151f;
      padding:8px 36px; border-bottom:1px solid #26283a;
      display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
nav a { color:#f9e2af; text-decoration:none; font-size:13px;
        padding:2px 10px; border:1px solid #313244; border-radius:12px; }
nav a:hover { background:#313244; }
#q { margin-left:auto; background:#181825; color:#cdd6f4; border:1px solid
     #313244; border-radius:6px; padding:4px 10px; width:230px; }
section.cat { padding:18px 36px; }
section.cat h2 { font-size:18px; border-left:5px solid; padding-left:10px;
                 margin:8px 0 14px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,
        minmax(350px,1fr)); gap:14px; }
.card { background:#161826; border:1px solid #26283a; border-radius:10px;
        padding:12px; display:flex; flex-direction:column; gap:8px; }
.card img { width:100%%; max-height:220px; object-fit:contain;
            background:%s; border-radius:6px; }
.cname { font-size:15px; font-weight:bold; color:#cdd6f4; }
.cname .star { color:#f9e2af; }
.meta { display:flex; gap:8px; align-items:center; font-size:12px; }
.badge { padding:1px 9px; border-radius:10px; color:#11111b; font-weight:bold; }
.kid { color:#6c7086; font-family:Consolas,monospace; }
.expr code { display:block; background:#101018; border:1px solid #26283a;
             border-radius:6px; padding:6px 8px; font-size:12px;
             color:#94e2d5; word-break:break-all; }
.kv b { color:#f9e2af; font-size:13px; }
.kv { font-size:13px; line-height:1.55; }
.kv ul { margin:4px 0 4px 18px; padding:0; }
.trivia { color:#a6adc8; font-style:italic; }
.desc { color:#7f849c; font-size:12px; }
footer { padding:22px 36px; color:#6c7086; font-size:12px;
         border-top:1px solid #26283a; }
@media print {
  body { background:#fff; color:#111; }
  header h1 { color:#1e66f5; }
  nav, #q { display:none; }
  section.cat { padding:10px 16px; page-break-inside:auto; }
  .card { background:#fff; border-color:#bbb; page-break-inside:avoid; }
  .card img { background:#fff; }
  .expr code { background:#f4f4f4; color:#0a6655; border-color:#ccc; }
  .desc, .trivia, .kid, footer, header .sub { color:#444; }
  .cname .star { color:#b58900; }
}
""" % (BG, BG)

_JS = """
document.getElementById('q').addEventListener('input', function () {
  var kw = this.value.trim().toLowerCase();
  document.querySelectorAll('.card').forEach(function (c) {
    c.style.display = (!kw || c.dataset.search.indexOf(kw) >= 0) ? '' : 'none';
  });
  document.querySelectorAll('section.cat').forEach(function (s) {
    var vis = Array.prototype.some.call(
      s.querySelectorAll('.card'),
      function (c) { return c.style.display !== 'none'; });
    s.style.display = vis ? '' : 'none';
  });
});
if (window.renderMathInElement) {
  renderMathInElement(document.body, {
    delimiters: [
      {left: '$$', right: '$$', display: true},
      {left: '$', right: '$', display: false}
    ],
    throwOnError: false
  });
}
"""


def _esc(s):
    """HTML 转义（保留 $ 供 KaTeX，属性用引号安全版）"""
    return html.escape(s, quote=True)


def _card_html(e, card, img_b64, fav, color):
    name = _esc(e['name'])
    star = ' <span class="star">★</span>' if fav else ''
    parts = [f'<div class="card" data-search="{_esc(e["name"] + " " + e["key"] + " " + e.get("category", "") + " " + e.get("desc", "")).lower()}">',
             f'<img alt="{name}" src="data:image/png;base64,{img_b64}">',
             f'<div class="cname">{star} {name}</div>',
             f'<div class="meta"><span class="badge" style="background:{color}">{_esc(e.get("category", "未分类"))}</span>'
             f'<span class="kid">{_esc(e["key"])}</span></div>']
    try:
        import mathparse
        plain = mathparse.parse_input(e['expr'])['plain']
    except Exception:
        plain = e['expr'] or f"生成曲面（{e.get('desc', '三角剖分')}）"
    parts.append(f'<div class="expr"><b style="color:#89b4fa;font-size:12px">表达式</b>'
                 f'<code>{_esc(plain)}</code></div>')
    if card:
        parts.append('<div class="kv">')
        if card.get('formula'):
            parts.append(f'<b>公式</b><div>{_esc(card["formula"])}</div>')
        if card.get('props'):
            parts.append('<b>性质</b><ul>'
                         + ''.join(f'<li>{_esc(p)}</li>' for p in card['props'])
                         + '</ul>')
        if card.get('trivia'):
            parts.append(f'<div class="trivia">📜 {_esc(card["trivia"])}</div>')
        parts.append('</div>')
    if e.get('desc') and not card:          # 资料卡已覆盖时不重复显示 desc
        parts.append(f'<div class="desc">{_esc(e["desc"])}</div>')
    parts.append('</div>')
    return '\n'.join(parts)


def generate(out_path=None):
    """生成《曲线图鉴》单文件 HTML，返回输出路径"""
    import curve_library
    import gallery
    from datetime import datetime

    out_path = out_path or DEFAULT_OUT
    grouped, warns = curve_library.load_all()
    if warns:
        print('[atlas] 曲线库警告:', '；'.join(warns))
    entries = [e for _, v in grouped for e in v]
    ok, failed = gallery.ensure_thumbs(entries)
    if failed:
        print(f'[atlas] {len(failed)} 张缩略图缺失: {failed}')
    favs = gallery.load_favs()
    katex_css, katex_js = embed_katex()

    head = [f'<title>曲线图鉴 · {len(entries)} 条</title>',
            '<meta charset="utf-8">',
            f'<style>{_CSS}</style>']
    if katex_css:
        head.append(f'<style>{katex_css}</style>')

    nav, secs = [], []
    n_fav = 0
    for i, (cat, es) in enumerate(grouped):
        color = gallery.CAT_COLORS.get(cat, gallery.DEFAULT_COLOR)
        nav.append(f'<a href="#cat-{i}">{_esc(cat)} ({len(es)})</a>')
        cards = []
        for e in es:
            fav = e['key'] in favs
            n_fav += fav
            try:
                img_b64 = base64.b64encode(
                    open(gallery.thumb_path(e['key']), 'rb').read()).decode()
            except OSError:
                img_b64 = ''
            cards.append(_card_html(e, gallery.CARDS.get(e['key']),
                                    img_b64, fav, color))
        secs.append(f'<section class="cat" id="cat-{i}">'
                    f'<h2 style="border-color:{color};color:{color}">{_esc(cat)}'
                    f' <small style="color:#6c7086">({len(es)})</small></h2>'
                    f'<div class="grid">{"".join(cards)}</div></section>')

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    body = [
        '<header>',
        '<h1>《曲线图鉴》</h1>',
        f'<div class="sub">{now} · 共 {len(entries)} 条曲线/曲面 · '
        f'{len(grouped)} 个分类 · ⭐ 收藏 {n_fav} 条 · '
        f'由 plot3d/atlas_gen.py 自动生成（KaTeX {"内联" if katex_css else "缺失"}）</div>',
        '</header>',
        f'<nav>{"".join(nav)}<input id="q" placeholder="🔍 搜索曲线/关键词…"></nav>',
        ''.join(secs),
        '<footer>plot3d · 3D 数学可视化平台 — 画廊内右键可收藏/取消，'
        '重新生成即同步 ⭐ 标记。</footer>',
    ]
    scripts = [f'<script>{_JS}</script>']
    if katex_js:                                    # KaTeX 需在过滤脚本前加载
        scripts.insert(0, f'<script>{katex_js}</script>')

    doc = ('<!DOCTYPE html><html lang="zh"><head>' + ''.join(head)
           + '</head><body>' + ''.join(body) + ''.join(scripts)
           + '</body></html>')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    return out_path


def main():
    ap = argparse.ArgumentParser(description='《曲线图鉴》生成器')
    ap.add_argument('-o', '--out', default=DEFAULT_OUT, help='输出 HTML 路径')
    args = ap.parse_args()
    path = generate(args.out)
    size = os.path.getsize(path) / 1e6
    print(f'✓ 图鉴已生成: {path}  ({size:.2f} MB)')
    return path


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
