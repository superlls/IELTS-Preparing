#!/usr/bin/env python3
# build_speaking.py — 将口语表达.md 转换为精美的复习网页
import re
from pathlib import Path

MD_FILE = Path(__file__).parent / "口语表达.md"
OUT_FILE = Path(__file__).parent / "speaking.html"

def parse_entries(text):
    entries = []
    # 按 ## 分割条目（跳过 # 主标题和孤立的 ---）
    blocks = re.split(r'\n(?=## )', text)
    for block in blocks:
        block = block.strip()
        if not block.startswith('## '):
            continue
        lines = block.split('\n')
        title = lines[0][3:].strip()

        body = '\n'.join(lines[1:])

        def extract_field(label, content):
            pattern = rf'\*\*{re.escape(label)}[:：]\*\*\s*(.*?)(?=\n\*\*|\n---|\n>|\Z)'
            m = re.search(pattern, content, re.S)
            return m.group(1).strip() if m else ''

        def extract_list_after(label, content):
            pattern = rf'\*\*{re.escape(label)}[:：]\*\*\s*\n((?:[-*].+\n?)+)'
            m = re.search(pattern, content)
            if not m:
                return []
            items = re.findall(r'^[-*]\s*(.+)$', m.group(1), re.M)
            return items

        def extract_tip(content):
            m = re.search(r'>\s*\*\*雅思口语提示[:：]\*\*\s*(.*?)(?=\n---|\Z)', content, re.S)
            return m.group(1).strip() if m else ''

        type_ = extract_field('类型', body)
        meaning = extract_field('中文含义', body)
        tip = extract_tip(body)

        # 英文表达
        english = extract_list_after('英文表达', body)
        if not english:
            # 尝试多种可能的块格式
            m = re.search(r'\*\*英文表达[与和区别：:]*\*\*\s*\n(.*?)(?=\n\*\*|\n---|\n>|\Z)', body, re.S)
            if m:
                english = re.findall(r'^[-*]\s*\*{0,2}(.+?)\*{0,2}\s*(?:（.*?）)?$', m.group(1), re.M)

        # 关键词汇
        vocab = extract_list_after('关键词汇', body)

        # 口语例句
        examples = extract_list_after('口语例句', body)
        if not examples:
            examples = extract_list_after('口语用法', body)

        entries.append({
            'title': title,
            'type': type_,
            'meaning': meaning,
            'english': english[:4],   # 最多4条
            'vocab': vocab[:6],
            'examples': examples[:3],
            'tip': tip,
        })
    return entries


def escape_html(s):
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


def bold_md(s):
    """把 **text** 转成 <strong>text</strong>"""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escape_html(s))


def render_entry(e, idx):
    title_id = f"entry-{idx}"
    type_tag = f'<span class="tag">{escape_html(e["type"])}</span>' if e['type'] else ''

    english_html = ''
    for i, item in enumerate(e['english']):
        item = re.sub(r'\*\*(.+?)\*\*', r'\1', item)
        item = re.sub(r'（.+?）$', '', item).strip()
        cls = 'en-primary' if i == 0 else 'en-alt'
        english_html += f'<li class="{cls}">{escape_html(item)}</li>'

    vocab_html = ''
    for v in e['vocab']:
        # 去除 ** 加粗标记
        v_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', v)
        vocab_html += f'<li>{bold_md(v_clean)}</li>'

    ex_html = ''
    for ex in e['examples']:
        ex_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', ex)
        ex_html += f'<li>{escape_html(ex_clean)}</li>'

    tip_html = ''
    if e['tip']:
        tip_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', e['tip'])
        tip_html = f'<div class="tip"><span class="tip-label">雅思提示</span>{escape_html(tip_clean)}</div>'

    meaning_html = f'<p class="meaning">{escape_html(e["meaning"])}</p>' if e['meaning'] else ''

    return f'''
<article class="card" id="{title_id}">
  <header class="card-header">
    <div class="card-meta">{type_tag}</div>
    <h2 class="card-title">{escape_html(e["title"])}</h2>
    {meaning_html}
  </header>
  <div class="card-body">
    {f'<section class="section"><h3>英文表达</h3><ul class="en-list">{english_html}</ul></section>' if english_html else ''}
    {f'<section class="section"><h3>关键词汇</h3><ul class="vocab-list">{vocab_html}</ul></section>' if vocab_html else ''}
    {f'<section class="section"><h3>口语例句</h3><ul class="ex-list">{ex_html}</ul></section>' if ex_html else ''}
    {tip_html}
  </div>
</article>'''


def build_nav(entries):
    items = ''
    for i, e in enumerate(entries):
        items += f'<li><a href="#entry-{i}" class="nav-link" data-idx="{i}">{escape_html(e["title"])}</a></li>\n'
    return items


def build_html(entries):
    nav = build_nav(entries)
    cards = ''.join(render_entry(e, i) for i, e in enumerate(entries))
    count = len(entries)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Speaking Journal — 雅思口语笔记</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Noto+Serif+SC:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg:       #0b0f18;
  --sidebar:  #101520;
  --card:     #161d2e;
  --card-bd:  rgba(255,255,255,0.06);
  --text:     #ddd6c8;
  --muted:    #7a8499;
  --gold:     #e8a74c;
  --gold-dim: rgba(232,167,76,0.12);
  --blue:     #7dd3fc;
  --green:    #86efac;
  --sidebar-w: 270px;
}}

html {{ scroll-behavior: smooth; }}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'DM Sans', 'Noto Serif SC', serif;
  min-height: 100vh;
  display: flex;
}}

/* ── SIDEBAR ── */
.sidebar {{
  width: var(--sidebar-w);
  min-height: 100vh;
  background: var(--sidebar);
  border-right: 1px solid var(--card-bd);
  position: fixed;
  top: 0; left: 0; bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

.sidebar-brand {{
  padding: 28px 24px 20px;
  border-bottom: 1px solid var(--card-bd);
}}

.brand-label {{
  font-size: 10px;
  letter-spacing: 0.2em;
  color: var(--gold);
  text-transform: uppercase;
  font-family: 'DM Sans', sans-serif;
  font-weight: 500;
  margin-bottom: 6px;
}}

.brand-title {{
  font-family: 'Playfair Display', serif;
  font-size: 22px;
  font-weight: 700;
  color: #f0ece3;
  line-height: 1.2;
}}

.brand-sub {{
  font-size: 12px;
  color: var(--muted);
  margin-top: 6px;
  font-family: 'Noto Serif SC', serif;
}}

.search-wrap {{
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--card-bd);
}}

.search-input {{
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--card-bd);
  border-radius: 8px;
  color: var(--text);
  font-size: 13px;
  padding: 9px 12px;
  font-family: 'Noto Serif SC', serif;
  outline: none;
  transition: border-color 0.2s;
}}
.search-input::placeholder {{ color: var(--muted); }}
.search-input:focus {{ border-color: var(--gold); }}

.nav-count {{
  padding: 10px 18px 6px;
  font-size: 11px;
  color: var(--muted);
  font-family: 'DM Sans', sans-serif;
  letter-spacing: 0.05em;
}}

.nav-list {{
  list-style: none;
  overflow-y: auto;
  flex: 1;
  padding: 4px 0 20px;
}}

.nav-list::-webkit-scrollbar {{ width: 4px; }}
.nav-list::-webkit-scrollbar-track {{ background: transparent; }}
.nav-list::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 4px; }}

.nav-link {{
  display: block;
  padding: 9px 20px;
  font-size: 13px;
  color: var(--muted);
  text-decoration: none;
  font-family: 'Noto Serif SC', serif;
  border-left: 2px solid transparent;
  transition: all 0.18s;
  line-height: 1.4;
}}
.nav-link:hover, .nav-link.active {{
  color: var(--gold);
  border-left-color: var(--gold);
  background: var(--gold-dim);
}}

/* ── MAIN ── */
.main {{
  margin-left: var(--sidebar-w);
  flex: 1;
  padding: 48px 48px 80px;
  max-width: 860px;
}}

.main-header {{
  margin-bottom: 40px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--card-bd);
}}

.main-header h1 {{
  font-family: 'Playfair Display', serif;
  font-size: 36px;
  color: #f0ece3;
  letter-spacing: -0.02em;
}}

.main-header p {{
  color: var(--muted);
  font-size: 14px;
  margin-top: 8px;
  font-family: 'DM Sans', sans-serif;
}}

/* ── CARD ── */
.card {{
  background: var(--card);
  border: 1px solid var(--card-bd);
  border-radius: 16px;
  margin-bottom: 28px;
  overflow: hidden;
  transition: border-color 0.25s, transform 0.2s;
  animation: fadeUp 0.4s ease both;
}}

.card:hover {{
  border-color: rgba(232,167,76,0.25);
  transform: translateY(-2px);
}}

@keyframes fadeUp {{
  from {{ opacity: 0; transform: translateY(16px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

.card-header {{
  padding: 24px 28px 18px;
  border-bottom: 1px solid var(--card-bd);
  background: rgba(255,255,255,0.015);
}}

.card-meta {{
  margin-bottom: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}}

.tag {{
  font-size: 11px;
  background: var(--gold-dim);
  color: var(--gold);
  border: 1px solid rgba(232,167,76,0.25);
  padding: 3px 10px;
  border-radius: 20px;
  font-family: 'DM Sans', sans-serif;
  font-weight: 500;
  letter-spacing: 0.04em;
}}

.card-title {{
  font-family: 'Noto Serif SC', serif;
  font-size: 20px;
  font-weight: 600;
  color: #f0ece3;
  line-height: 1.4;
}}

.meaning {{
  margin-top: 8px;
  font-size: 13.5px;
  color: var(--muted);
  line-height: 1.7;
  font-family: 'Noto Serif SC', serif;
}}

.card-body {{
  padding: 20px 28px 24px;
}}

.section {{
  margin-bottom: 20px;
}}

.section h3 {{
  font-size: 10.5px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: 'DM Sans', sans-serif;
  font-weight: 500;
  margin-bottom: 10px;
}}

/* 英文表达 */
.en-list {{ list-style: none; }}
.en-primary {{
  font-size: 17px;
  color: var(--blue);
  font-family: 'Playfair Display', serif;
  font-style: italic;
  padding: 6px 0 6px 14px;
  border-left: 2px solid var(--blue);
  margin-bottom: 8px;
}}
.en-alt {{
  font-size: 13.5px;
  color: rgba(125, 211, 252, 0.65);
  padding: 3px 0 3px 14px;
  border-left: 1px solid rgba(125,211,252,0.2);
  font-family: 'DM Sans', sans-serif;
}}

/* 关键词汇 */
.vocab-list {{
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
}}
.vocab-list li {{
  font-size: 12.5px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--card-bd);
  border-radius: 8px;
  padding: 7px 12px;
  font-family: 'Noto Serif SC', serif;
  color: var(--text);
}}
.vocab-list li strong {{
  color: var(--gold);
}}

/* 例句 */
.ex-list {{ list-style: none; }}
.ex-list li {{
  font-size: 13px;
  color: var(--green);
  padding: 5px 0 5px 14px;
  border-left: 1px solid rgba(134,239,172,0.25);
  margin-bottom: 6px;
  font-family: 'Noto Serif SC', serif;
  opacity: 0.85;
  line-height: 1.6;
}}

/* 雅思提示 */
.tip {{
  background: rgba(232,167,76,0.07);
  border: 1px solid rgba(232,167,76,0.2);
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 13px;
  color: rgba(232,167,76,0.85);
  line-height: 1.7;
  font-family: 'Noto Serif SC', serif;
}}
.tip-label {{
  display: block;
  font-size: 10px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  font-family: 'DM Sans', sans-serif;
  margin-bottom: 6px;
  font-weight: 600;
  color: var(--gold);
}}

/* 搜索无结果 */
.no-result {{
  text-align: center;
  color: var(--muted);
  padding: 60px 0;
  font-family: 'Noto Serif SC', serif;
  display: none;
}}

/* 动画延迟 */
.card:nth-child(1)  {{ animation-delay: 0.04s; }}
.card:nth-child(2)  {{ animation-delay: 0.08s; }}
.card:nth-child(3)  {{ animation-delay: 0.12s; }}
.card:nth-child(4)  {{ animation-delay: 0.16s; }}
.card:nth-child(5)  {{ animation-delay: 0.20s; }}
.card:nth-child(6)  {{ animation-delay: 0.24s; }}
.card:nth-child(7)  {{ animation-delay: 0.28s; }}
.card:nth-child(8)  {{ animation-delay: 0.32s; }}

@media (max-width: 768px) {{
  .sidebar {{ display: none; }}
  .main {{ margin-left: 0; padding: 24px 20px; }}
}}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="sidebar-brand">
    <div class="brand-label">IELTS Speaking</div>
    <div class="brand-title">Speaking<br>Journal</div>
    <div class="brand-sub">口语表达笔记 · {count} 条</div>
  </div>
  <div class="search-wrap">
    <input class="search-input" type="text" placeholder="搜索表达..." id="searchInput">
  </div>
  <div class="nav-count" id="navCount">共 {count} 条表达</div>
  <ul class="nav-list" id="navList">
    {nav}
  </ul>
</aside>

<main class="main">
  <div class="main-header">
    <h1>Speaking Journal</h1>
    <p>雅思口语表达手账 · 共 {count} 条 · 持续更新中</p>
  </div>
  <div id="cardContainer">
    {cards}
  </div>
  <div class="no-result" id="noResult">没有找到相关表达</div>
</main>

<script>
const searchInput = document.getElementById('searchInput');
const cards = document.querySelectorAll('.card');
const navLinks = document.querySelectorAll('.nav-link');
const navCount = document.getElementById('navCount');
const noResult = document.getElementById('noResult');

searchInput.addEventListener('input', () => {{
  const q = searchInput.value.trim().toLowerCase();
  let visible = 0;
  cards.forEach((card, i) => {{
    const text = card.textContent.toLowerCase();
    const show = !q || text.includes(q);
    card.style.display = show ? '' : 'none';
    navLinks[i].style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  navCount.textContent = `共 ${{visible}} 条表达`;
  noResult.style.display = visible === 0 ? 'block' : 'none';
}});

// 高亮当前导航项
const observer = new IntersectionObserver((entries) => {{
  entries.forEach(entry => {{
    if (entry.isIntersecting) {{
      const id = entry.target.id;
      navLinks.forEach(a => {{
        a.classList.toggle('active', a.getAttribute('href') === '#' + id);
      }});
    }}
  }});
}}, {{ rootMargin: '-30% 0px -60% 0px' }});

cards.forEach(card => observer.observe(card));
</script>
</body>
</html>'''


def main():
    text = MD_FILE.read_text(encoding='utf-8')
    entries = parse_entries(text)
    # 去重（标题相同的只保留最后一条）
    seen = {}
    for e in entries:
        seen[e['title']] = e
    entries = list(seen.values())

    html = build_html(entries)
    OUT_FILE.write_text(html, encoding='utf-8')
    print(f'✅ 已生成 → {OUT_FILE}')
    print(f'📚 共解析 {len(entries)} 条口语表达')


if __name__ == '__main__':
    main()
