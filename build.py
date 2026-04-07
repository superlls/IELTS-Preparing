#!/usr/bin/env python3
"""读取 生词本.md，生成 flashcard 网页 index.html"""

import re, json, html
from pathlib import Path

DIR = Path(__file__).parent
MD_FILE = DIR / "生词本.md"
OUT_FILE = DIR / "index.html"


def parse_vocab(text: str) -> list[dict]:
    """把 markdown 拆分成 [{word, body}, ...]"""
    # 按 ## 标题拆分
    parts = re.split(r'^## ', text, flags=re.MULTILINE)
    cards = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split('\n', 1)
        word = lines[0].strip().rstrip('-').strip()
        body = lines[1].strip().rstrip('-').strip() if len(lines) > 1 else ''
        # 去掉尾部的 ---
        body = re.sub(r'\n---\s*$', '', body).strip()
        if word and body:
            cards.append({"word": word, "body": body})
    return cards


def md_to_html(md: str) -> str:
    """简易 markdown → html 转换（支持表格、粗体、引用、列表、代码）"""
    lines = md.split('\n')
    result = []
    in_table = False
    in_list = False
    i = 0
    while i < len(lines):
        line = lines[i]

        # 表格
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                result.append('<table>')
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            # 跳过分隔行
            if all(re.match(r'^[-:]+$', c) for c in cells):
                i += 1
                continue
            tag = 'th' if not any('<tr>' in r for r in result if '<tr>' in r) else 'td'
            # 如果已有行则用 td
            if result and '<tr>' in ''.join(result[-5:]):
                tag = 'td'
            row = '<tr>' + ''.join(f'<{tag}>{inline(html.escape(c))}</{tag}>' for c in cells) + '</tr>'
            result.append(row)
            i += 1
            continue
        else:
            if in_table:
                in_table = False
                result.append('</table>')

        # 引用块
        if line.strip().startswith('>'):
            text = line.strip().lstrip('>').strip()
            result.append(f'<blockquote>{inline(html.escape(text))}</blockquote>')
            i += 1
            continue

        # 无序列表
        if re.match(r'^[-*] ', line.strip()):
            if not in_list:
                in_list = True
                result.append('<ul>')
            text = re.sub(r'^[-*] ', '', line.strip())
            result.append(f'<li>{inline(html.escape(text))}</li>')
            i += 1
            continue
        else:
            if in_list:
                in_list = False
                result.append('</ul>')

        # 空行
        if not line.strip():
            i += 1
            continue

        # 普通段落
        result.append(f'<p>{inline(html.escape(line))}</p>')
        i += 1

    if in_table:
        result.append('</table>')
    if in_list:
        result.append('</ul>')
    return '\n'.join(result)


def inline(text: str) -> str:
    """处理行内 markdown：粗体、行内代码"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def build_html(cards: list[dict]) -> str:
    cards_json = json.dumps(cards, ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>雅思生词卡</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  background: #0f0f1a;
  color: #e0e0e0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  user-select: none;
  -webkit-user-select: none;
}}

/* 顶栏 */
.topbar {{
  width: 100%;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}}
.topbar h1 {{
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
}}
.topbar .counter {{
  font-size: 0.95rem;
  color: #888;
  white-space: nowrap;
}}
.search-box {{
  flex: 1;
  min-width: 160px;
  max-width: 320px;
  position: relative;
}}
.search-box input {{
  width: 100%;
  padding: 8px 12px 8px 36px;
  border-radius: 8px;
  border: 1px solid #333;
  background: #1a1a2e;
  color: #e0e0e0;
  font-size: 0.95rem;
  outline: none;
  transition: border-color .2s;
}}
.search-box input:focus {{ border-color: #6c63ff; }}
.search-box svg {{
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  stroke: #666;
}}
.btn-group {{
  display: flex;
  gap: 8px;
}}
.btn {{
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #333;
  background: #1a1a2e;
  color: #ccc;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all .2s;
  white-space: nowrap;
}}
.btn:hover {{ background: #252545; border-color: #6c63ff; color: #fff; }}
.btn.active {{ background: #6c63ff; border-color: #6c63ff; color: #fff; }}

/* 卡片容器 */
.card-area {{
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 720px;
  padding: 16px 24px 24px;
  perspective: 1200px;
}}
.card-wrapper {{
  width: 100%;
  aspect-ratio: 4 / 3;
  max-height: 70vh;
  cursor: pointer;
  position: relative;
}}
.card {{
  width: 100%;
  height: 100%;
  position: relative;
  transform-style: preserve-3d;
  transition: transform .5s cubic-bezier(.4,.2,.2,1);
}}
.card.flipped {{ transform: rotateY(180deg); }}

.card-face {{
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  border-radius: 16px;
  padding: 32px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* 正面 */
.card-front {{
  background: linear-gradient(135deg, #1e1e3a 0%, #2a2a4a 100%);
  border: 1px solid #333;
  align-items: center;
  justify-content: center;
}}
.card-front .word {{
  font-size: clamp(1.8rem, 5vw, 3rem);
  font-weight: 700;
  color: #fff;
  text-align: center;
  line-height: 1.3;
  word-break: break-word;
}}
.card-front .hint {{
  margin-top: 20px;
  font-size: 0.85rem;
  color: #666;
}}

/* 背面 */
.card-back {{
  background: linear-gradient(135deg, #1a1a30 0%, #222244 100%);
  border: 1px solid #333;
  transform: rotateY(180deg);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}}
.card-back .back-word {{
  font-size: 1.2rem;
  font-weight: 700;
  color: #b8b0ff;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #333;
}}
.card-back p {{ margin: 4px 0; line-height: 1.65; font-size: 0.92rem; color: #d0d0d0; }}
.card-back strong {{ color: #e8c547; font-weight: 600; }}
.card-back table {{
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 0.85rem;
}}
.card-back th, .card-back td {{
  padding: 6px 10px;
  border: 1px solid #3a3a5a;
  text-align: left;
}}
.card-back th {{ background: #2a2a4a; color: #b8b0ff; font-weight: 600; }}
.card-back td {{ color: #ccc; }}
.card-back blockquote {{
  border-left: 3px solid #6c63ff;
  padding: 8px 12px;
  margin: 8px 0;
  background: rgba(108,99,255,.08);
  font-size: 0.88rem;
  color: #aaa;
  border-radius: 0 6px 6px 0;
}}
.card-back ul {{ padding-left: 20px; margin: 6px 0; }}
.card-back li {{ margin: 3px 0; font-size: 0.9rem; line-height: 1.6; color: #ccc; }}
.card-back code {{
  background: #2a2a4a;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.88em;
  color: #e8c547;
}}

/* 底部导航 */
.nav {{
  width: 100%;
  max-width: 720px;
  padding: 0 24px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}}
.nav-btn {{
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid #333;
  background: #1a1a2e;
  color: #ccc;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .2s;
}}
.nav-btn:hover {{ background: #252545; border-color: #6c63ff; color: #fff; }}
.progress {{
  font-size: 0.95rem;
  color: #888;
  min-width: 80px;
  text-align: center;
}}

/* 列表模式 */
.list-area {{
  width: 100%;
  max-width: 720px;
  padding: 0 24px 24px;
  display: none;
}}
.list-area.active {{ display: block; }}
.list-item {{
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 10px;
  margin-bottom: 12px;
  overflow: hidden;
  transition: border-color .2s;
}}
.list-item:hover {{ border-color: #6c63ff; }}
.list-item-header {{
  padding: 14px 18px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.list-item-header .word {{ font-weight: 600; font-size: 1.05rem; color: #fff; }}
.list-item-header .arrow {{
  transition: transform .2s;
  color: #666;
  font-size: .8rem;
}}
.list-item.open .arrow {{ transform: rotate(90deg); }}
.list-item-body {{
  display: none;
  padding: 0 18px 14px;
}}
.list-item.open .list-item-body {{ display: block; }}
.list-item-body p {{ margin: 4px 0; line-height: 1.65; font-size: 0.9rem; color: #ccc; }}
.list-item-body strong {{ color: #e8c547; }}
.list-item-body table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 0.82rem; }}
.list-item-body th, .list-item-body td {{ padding: 5px 8px; border: 1px solid #3a3a5a; text-align: left; }}
.list-item-body th {{ background: #2a2a4a; color: #b8b0ff; }}
.list-item-body td {{ color: #bbb; }}
.list-item-body blockquote {{
  border-left: 3px solid #6c63ff;
  padding: 8px 12px;
  margin: 8px 0;
  background: rgba(108,99,255,.08);
  font-size: 0.85rem;
  color: #aaa;
  border-radius: 0 6px 6px 0;
}}
.list-item-body ul {{ padding-left: 18px; margin: 6px 0; }}
.list-item-body li {{ margin: 2px 0; font-size: 0.88rem; color: #bbb; }}
.list-item-body code {{ background: #2a2a4a; padding: 1px 5px; border-radius: 4px; font-size: 0.88em; color: #e8c547; }}

.card-area.hidden, .nav.hidden {{ display: none; }}

@media (max-width: 500px) {{
  .topbar {{ padding: 12px 16px; }}
  .card-area {{ padding: 12px 16px 16px; }}
  .card-face {{ padding: 20px; }}
  .nav {{ padding: 0 16px 16px; }}
  .list-area {{ padding: 0 16px 16px; }}
}}

/* 滚动条 */
.card-back::-webkit-scrollbar {{ width: 4px; }}
.card-back::-webkit-scrollbar-track {{ background: transparent; }}
.card-back::-webkit-scrollbar-thumb {{ background: #444; border-radius: 2px; }}
</style>
</head>
<body>

<div class="topbar">
  <h1>雅思生词卡</h1>
  <div class="search-box">
    <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" id="search" placeholder="搜索单词...">
  </div>
  <span class="counter" id="total"></span>
  <div class="btn-group">
    <button class="btn" id="btnShuffle">随机</button>
    <button class="btn" id="btnList">列表</button>
  </div>
</div>

<div class="card-area" id="cardArea">
  <div class="card-wrapper" id="cardWrapper">
    <div class="card" id="card">
      <div class="card-face card-front">
        <div class="word" id="frontWord"></div>
        <div class="hint">点击翻转</div>
      </div>
      <div class="card-face card-back">
        <div class="back-word" id="backWord"></div>
        <div id="backBody"></div>
      </div>
    </div>
  </div>
</div>

<div class="nav" id="navBar">
  <button class="nav-btn" id="prevBtn">&larr;</button>
  <span class="progress" id="progress"></span>
  <button class="nav-btn" id="nextBtn">&rarr;</button>
</div>

<div class="list-area" id="listArea"></div>

<script>
const ALL_CARDS = {cards_json};
const BODY_HTML = {{}};
''' + '''
// 预渲染的 body html 由 python 注入
''' + f'''const BODY_PRE = {json.dumps({c["word"]: md_to_html(c["body"]) for c in cards}, ensure_ascii=False)};

let filtered = [...ALL_CARDS];
let idx = 0;
let listMode = false;

const $ = s => document.querySelector(s);

function render() {{
  if (!filtered.length) {{
    $('#frontWord').textContent = '没有匹配的单词';
    $('#backWord').textContent = '';
    $('#backBody').innerHTML = '';
    $('#progress').textContent = '0 / 0';
    return;
  }}
  const c = filtered[idx];
  $('#frontWord').textContent = c.word;
  $('#backWord').textContent = c.word;
  $('#backBody').innerHTML = BODY_PRE[c.word] || '';
  $('#progress').textContent = `${{idx + 1}} / ${{filtered.length}}`;
  $('#card').classList.remove('flipped');
}}

function go(delta) {{
  if (!filtered.length) return;
  idx = (idx + delta + filtered.length) % filtered.length;
  render();
}}

// 翻转
$('#cardWrapper').addEventListener('click', e => {{
  // 如果点击背面的可滚动区域内的链接等，不翻转
  if (e.target.closest('.card-back') && e.target !== $('#card') && e.target.closest('a')) return;
  $('#card').classList.toggle('flipped');
}});

// 背面滚动时阻止翻转
let scrolling = false;
const backFace = document.querySelector('.card-back');
backFace.addEventListener('scroll', () => {{ scrolling = true; }});
backFace.addEventListener('touchmove', e => e.stopPropagation(), {{ passive: true }});

// 导航
$('#prevBtn').addEventListener('click', () => go(-1));
$('#nextBtn').addEventListener('click', () => go(1));

// 键盘
document.addEventListener('keydown', e => {{
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowLeft') go(-1);
  else if (e.key === 'ArrowRight') go(1);
  else if (e.key === ' ' || e.key === 'Enter') {{
    e.preventDefault();
    $('#card').classList.toggle('flipped');
  }}
}});

// 触摸滑动
let tx = 0;
$('#cardArea').addEventListener('touchstart', e => {{ tx = e.touches[0].clientX; }}, {{ passive: true }});
$('#cardArea').addEventListener('touchend', e => {{
  const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
}});

// 搜索
$('#search').addEventListener('input', e => {{
  const q = e.target.value.trim().toLowerCase();
  filtered = q ? ALL_CARDS.filter(c => c.word.toLowerCase().includes(q) || c.body.toLowerCase().includes(q)) : [...ALL_CARDS];
  idx = 0;
  render();
  if (listMode) renderList();
  $('#total').textContent = `共 ${{filtered.length}} 词`;
}});

// 随机
$('#btnShuffle').addEventListener('click', () => {{
  for (let i = filtered.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [filtered[i], filtered[j]] = [filtered[j], filtered[i]];
  }}
  idx = 0;
  render();
  if (listMode) renderList();
}});

// 列表模式
function renderList() {{
  const area = $('#listArea');
  area.innerHTML = filtered.map((c, i) => `
    <div class="list-item" data-i="${{i}}">
      <div class="list-item-header">
        <span class="word">${{esc(c.word)}}</span>
        <span class="arrow">&#9654;</span>
      </div>
      <div class="list-item-body">${{BODY_PRE[c.word] || ''}}</div>
    </div>
  `).join('');
  area.querySelectorAll('.list-item-header').forEach(h => {{
    h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
  }});
}}

function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}

$('#btnList').addEventListener('click', () => {{
  listMode = !listMode;
  $('#btnList').classList.toggle('active', listMode);
  $('#cardArea').classList.toggle('hidden', listMode);
  $('#navBar').classList.toggle('hidden', listMode);
  $('#listArea').classList.toggle('active', listMode);
  if (listMode) renderList();
}});

// 初始化
$('#total').textContent = `共 ${{ALL_CARDS.length}} 词`;
render();
</script>
</body>
</html>'''


def main():
    text = MD_FILE.read_text(encoding='utf-8')
    cards = parse_vocab(text)
    print(f"解析到 {len(cards)} 个词条")
    html_content = build_html(cards)
    OUT_FILE.write_text(html_content, encoding='utf-8')
    print(f"已生成 → {OUT_FILE}")


if __name__ == '__main__':
    main()
