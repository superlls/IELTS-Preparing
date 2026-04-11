#!/usr/bin/env python3
"""听力辨词卡：听音 → 看词 → 按需查释义（HTTP 服务器模式）"""
import json, http.server, socketserver, webbrowser, threading, sys
from pathlib import Path

DIR = Path(__file__).parent
MD = DIR / "听不出的词.md"
OUT = DIR / "index.html"
PORT = 8765


def parse(text: str) -> list[str]:
    words = []
    seen = set()
    for line in text.splitlines():
        w = line.strip()
        if not w or w.startswith('#'):
            continue
        if w not in seen:
            seen.add(w)
            words.append(w)
    return words


def build(words: list[str]) -> str:
    words_json = json.dumps(words, ensure_ascii=False)
    return r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>听力辨词 · Ear Training</title>
<style>
:root {
  --bg: #fbfbfd;
  --text: #1d1d1f;
  --text-2: #6e6e73;
  --text-3: #86868b;
  --hairline: rgba(0,0,0,0.08);
  --hairline-strong: rgba(0,0,0,0.14);
  --accent: #0071e3;
  --card: #ffffff;
}

* { margin: 0; padding: 0; box-sizing: border-box; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }

html, body { height: 100%; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
  background: var(--bg);
  background-image:
    radial-gradient(ellipse 70% 50% at 50% -8%, #eef2f7 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 100% 100%, #f3eef7 0%, transparent 55%),
    radial-gradient(ellipse 50% 40% at 0% 80%, #eef5f3 0%, transparent 55%);
  color: var(--text);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  letter-spacing: -0.01em;
}

/* Frosted nav */
.nav {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  background: rgba(251, 251, 253, 0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 0.5px solid var(--hairline);
}
.nav-inner {
  width: 100%;
  max-width: 980px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.nav-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.nav-title .dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--accent); margin: 0 10px 2px; vertical-align: middle; }
.nav-title em { font-style: normal; color: var(--text-3); font-weight: 400; }
.nav-counter {
  font-size: 12px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
}

/* Hero */
.hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 56px 24px 24px;
  position: relative;
}

.eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 14px;
  opacity: 0;
  animation: fadeUp 0.9s 0.05s forwards cubic-bezier(0.16, 1, 0.3, 1);
}

.headline {
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 600;
  letter-spacing: -0.028em;
  line-height: 1.08;
  text-align: center;
  margin-bottom: 40px;
  opacity: 0;
  animation: fadeUp 0.9s 0.15s forwards cubic-bezier(0.16, 1, 0.3, 1);
}
.headline .gradient {
  background: linear-gradient(135deg, #0071e3 0%, #6e5bff 50%, #a15bff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* Card */
.card {
  width: 100%;
  max-width: 680px;
  min-height: 460px;
  background: var(--card);
  border-radius: 28px;
  box-shadow:
    0 30px 80px -20px rgba(0,0,0,0.15),
    0 10px 30px -10px rgba(0,0,0,0.08),
    0 1px 2px rgba(0,0,0,0.04),
    inset 0 0 0 0.5px rgba(255,255,255,0.6);
  padding: 64px 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  opacity: 0;
  transform: translateY(24px);
  animation: fadeUp 1s 0.25s forwards cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}
.card::before {
  content: '';
  position: absolute;
  top: 0; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,0,0,0.1), transparent);
}

/* Stage: play */
.stage { width: 100%; display: flex; flex-direction: column; align-items: center; }
.stage.hidden { display: none; }

.play-btn {
  width: 148px;
  height: 148px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 25%, rgba(255,255,255,0.35), transparent 50%),
    linear-gradient(180deg, #0a84ff 0%, #0060d0 100%);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 24px 50px -12px rgba(10, 132, 255, 0.45),
    0 8px 20px -8px rgba(10, 132, 255, 0.3),
    inset 0 1px 0 rgba(255,255,255,0.35),
    inset 0 -2px 6px rgba(0,0,0,0.1);
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.35s ease;
  position: relative;
}
.play-btn:hover {
  transform: scale(1.04) translateY(-2px);
  box-shadow:
    0 32px 60px -12px rgba(10, 132, 255, 0.55),
    0 12px 24px -8px rgba(10, 132, 255, 0.35),
    inset 0 1px 0 rgba(255,255,255,0.4),
    inset 0 -2px 6px rgba(0,0,0,0.1);
}
.play-btn:active { transform: scale(0.98); }
.play-btn svg {
  width: 54px;
  height: 54px;
  fill: white;
  margin-left: 6px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
}
.play-btn.playing::after {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 2px solid rgba(10, 132, 255, 0.4);
  animation: ripple 1.6s ease-out infinite;
}
@keyframes ripple {
  0% { transform: scale(0.9); opacity: 1; }
  100% { transform: scale(1.3); opacity: 0; }
}

.play-hint {
  margin-top: 30px;
  font-size: 15px;
  color: var(--text-2);
  font-weight: 400;
  letter-spacing: -0.008em;
}
.play-hint kbd {
  display: inline-block;
  padding: 2px 7px;
  margin: 0 2px;
  font-family: inherit;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-2);
  background: #f5f5f7;
  border: 0.5px solid var(--hairline-strong);
  border-radius: 5px;
  box-shadow: 0 1px 0 rgba(0,0,0,0.04);
}

.speed-toggle {
  margin-top: 22px;
  display: flex;
  gap: 6px;
  padding: 4px;
  background: #f5f5f7;
  border-radius: 980px;
  border: 0.5px solid var(--hairline);
}
.speed-btn {
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 500;
  background: transparent;
  color: var(--text-2);
  border: none;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: inherit;
  letter-spacing: -0.005em;
}
.speed-btn:hover { color: var(--text); }
.speed-btn.active {
  background: white;
  color: var(--text);
  box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 0.5px rgba(0,0,0,0.04);
}

.reveal-btn {
  margin-top: 32px;
  padding: 11px 24px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: var(--accent);
  border: none;
  cursor: pointer;
  border-radius: 980px;
  transition: all 0.2s ease;
  font-family: inherit;
  letter-spacing: -0.005em;
}
.reveal-btn:hover { background: rgba(0, 113, 227, 0.08); }
.reveal-btn .arrow { display: inline-block; transition: transform 0.2s; margin-left: 2px; }
.reveal-btn:hover .arrow { transform: translateX(3px); }

/* Stage: word */
.word-stage { animation: revealUp 0.65s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes revealUp {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

.word-display {
  font-size: clamp(44px, 7.5vw, 84px);
  font-weight: 600;
  letter-spacing: -0.04em;
  line-height: 1.02;
  background: linear-gradient(180deg, #1d1d1f 0%, #4a4a4d 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
  word-break: break-word;
  padding: 0 8px;
}

.phonetic {
  margin-top: 14px;
  font-size: 14px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
  min-height: 18px;
}

.replay-row {
  display: flex;
  gap: 10px;
  margin-top: 24px;
}
.icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 0.5px solid var(--hairline-strong);
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  color: var(--text-2);
}
.icon-btn:hover {
  background: #f5f5f7;
  color: var(--text);
  border-color: var(--text-3);
  transform: translateY(-1px);
}
.icon-btn:active { transform: translateY(0); }
.icon-btn svg { width: 15px; height: 15px; fill: currentColor; }
.icon-btn .label {
  position: absolute;
  font-size: 9px;
  font-weight: 600;
  bottom: -16px;
  color: var(--text-3);
  white-space: nowrap;
}
.icon-btn { position: relative; }

.detail-btn {
  margin-top: 38px;
  padding: 11px 22px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: var(--accent);
  border: 0.5px solid rgba(0, 113, 227, 0.45);
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  letter-spacing: -0.005em;
}
.detail-btn:hover {
  background: rgba(0, 113, 227, 0.06);
  border-color: var(--accent);
}
.detail-btn.loaded { display: none; }

/* Meaning reveal */
.meaning {
  width: 100%;
  max-width: 480px;
  margin-top: 30px;
  padding-top: 30px;
  border-top: 0.5px solid var(--hairline);
  display: none;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.meaning.show { display: flex; animation: revealUp 0.5s cubic-bezier(0.16, 1, 0.3, 1); }

.meaning-label {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 12px;
  font-weight: 600;
}
.meaning-text {
  font-size: 19px;
  font-weight: 400;
  color: var(--text);
  letter-spacing: -0.015em;
  line-height: 1.45;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(0,0,0,0.08);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.youdao-link {
  margin-top: 18px;
  font-size: 12px;
  color: var(--text-3);
  text-decoration: none;
  transition: color 0.2s;
  font-weight: 500;
  letter-spacing: -0.005em;
}
.youdao-link:hover { color: var(--accent); }
.youdao-link .arr { display: inline-block; transition: transform 0.2s; margin-left: 2px; }
.youdao-link:hover .arr { transform: translate(2px, -2px); }

/* Bottom controls */
.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 28px 24px 44px;
  opacity: 0;
  animation: fadeUp 1s 0.4s forwards cubic-bezier(0.16, 1, 0.3, 1);
}
.ctrl-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 0.5px solid var(--hairline-strong);
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text);
  transition: all 0.2s ease;
}
.ctrl-btn:hover {
  background: white;
  border-color: var(--text-3);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0,0,0,0.08);
}
.ctrl-btn:active { transform: translateY(0); }
.ctrl-btn svg { width: 14px; height: 14px; fill: currentColor; }

.progress {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.005em;
  min-width: 52px;
  text-align: center;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Empty state */
.empty {
  text-align: center;
  color: var(--text-3);
  font-size: 15px;
  line-height: 1.7;
}
.empty code {
  display: inline-block;
  padding: 2px 8px;
  background: #f5f5f7;
  border-radius: 5px;
  font-size: 13px;
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, monospace;
}

.footer {
  text-align: center;
  font-size: 11px;
  color: var(--text-3);
  padding: 8px 24px 24px;
  letter-spacing: 0;
}

/* Floating add button */
.fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(180deg, #1d1d1f 0%, #000 100%);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow:
    0 16px 32px -8px rgba(0,0,0,0.3),
    0 4px 12px -4px rgba(0,0,0,0.2),
    inset 0 1px 0 rgba(255,255,255,0.12);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
  z-index: 200;
}
.fab:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow:
    0 20px 40px -8px rgba(0,0,0,0.35),
    0 6px 16px -4px rgba(0,0,0,0.22),
    inset 0 1px 0 rgba(255,255,255,0.12);
}
.fab:active { transform: translateY(0) scale(0.98); }
.fab svg { width: 20px; height: 20px; fill: white; }

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.32);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 300;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 24px;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.modal-backdrop.show { display: flex; opacity: 1; }

.modal {
  width: 100%;
  max-width: 440px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: saturate(180%) blur(30px);
  -webkit-backdrop-filter: saturate(180%) blur(30px);
  border-radius: 22px;
  padding: 28px 28px 24px;
  box-shadow:
    0 40px 100px -20px rgba(0,0,0,0.35),
    0 16px 40px -12px rgba(0,0,0,0.2),
    inset 0 0 0 0.5px rgba(255,255,255,0.8);
  transform: scale(0.94) translateY(8px);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-backdrop.show .modal { transform: scale(1) translateY(0); }

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.modal-title {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
}
.modal-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(0,0,0,0.06);
  color: var(--text-2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.2s;
}
.modal-close:hover { background: rgba(0,0,0,0.1); color: var(--text); }

.modal-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.modal-input {
  flex: 1;
  padding: 12px 16px;
  font-size: 15px;
  font-family: inherit;
  color: var(--text);
  background: white;
  border: 0.5px solid var(--hairline-strong);
  border-radius: 12px;
  outline: none;
  transition: all 0.2s;
  letter-spacing: -0.005em;
}
.modal-input::placeholder { color: var(--text-3); }
.modal-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.15);
}
.modal-add {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  color: white;
  background: var(--accent);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: -0.005em;
}
.modal-add:hover { background: #0077ed; }
.modal-add:active { transform: scale(0.97); }
.modal-add:disabled { opacity: 0.4; cursor: not-allowed; }

.modal-section {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-3);
  font-weight: 600;
  margin: 18px 0 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-section .count {
  background: rgba(0,0,0,0.06);
  padding: 2px 8px;
  border-radius: 980px;
  letter-spacing: 0;
  font-weight: 500;
}

.user-list {
  max-height: 220px;
  overflow-y: auto;
  margin: 0 -6px;
  padding: 0 6px;
}
.user-list:empty::before {
  content: '尚未添加 · 输入单词后按 Enter';
  display: block;
  text-align: center;
  font-size: 12px;
  color: var(--text-3);
  padding: 24px 0;
  letter-spacing: -0.005em;
  text-transform: none;
}
.user-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 14px;
  background: white;
  border: 0.5px solid var(--hairline);
  border-radius: 10px;
  margin-bottom: 6px;
  transition: all 0.2s;
}
.user-item:hover { border-color: var(--hairline-strong); }
.user-item .w {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  letter-spacing: -0.01em;
}
.user-item .del {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
}
.user-item .del:hover { background: rgba(255, 59, 48, 0.1); color: #ff3b30; }

.modal-hint {
  font-size: 11px;
  color: var(--text-3);
  text-align: center;
  margin-top: 14px;
  letter-spacing: -0.005em;
}

@media (max-width: 600px) {
  .card { padding: 48px 24px; min-height: 420px; border-radius: 22px; }
  .play-btn { width: 124px; height: 124px; }
  .play-btn svg { width: 46px; height: 46px; }
  .hero { padding: 32px 16px 16px; }
  .headline { margin-bottom: 28px; }
}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <div class="nav-title">听力辨词<span class="dot"></span><em>Ear Training</em></div>
    <div class="nav-counter" id="counter">— / —</div>
  </div>
</nav>

<main class="hero">
  <div class="eyebrow">Listen · Recall · Reveal</div>
  <h1 class="headline">听懂每一个<span class="gradient">陌生的音节</span>。</h1>

  <div class="card" id="card">
    <!-- Stage 1: Listen -->
    <div class="stage" id="stagePlay">
      <button class="play-btn" id="playBtn" aria-label="播放">
        <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
      </button>
      <div class="play-hint">按 <kbd>Space</kbd> 或点击播放</div>
      <div class="speed-toggle">
        <button class="speed-btn active" data-speed="1">正常</button>
        <button class="speed-btn" data-speed="0.7">慢速 0.7×</button>
      </div>
      <button class="reveal-btn" id="revealBtn">显示单词 <span class="arrow">→</span></button>
    </div>

    <!-- Stage 2 + 3: Word & Meaning -->
    <div class="stage hidden" id="stageWord">
      <div class="word-display" id="wordDisplay"></div>
      <div class="phonetic" id="phonetic">&nbsp;</div>
      <div class="replay-row">
        <button class="icon-btn" id="replayNormal" title="正常速度重播">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </button>
        <button class="icon-btn" id="replaySlow" title="慢速重播">
          <svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
        </button>
        <button class="icon-btn" id="hideWord" title="返回听音模式">
          <svg viewBox="0 0 24 24"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27z"/></svg>
        </button>
      </div>
      <button class="detail-btn" id="detailBtn">查看释义</button>

      <div class="meaning" id="meaning">
        <div class="meaning-label">中文释义</div>
        <div class="meaning-text" id="meaningText"></div>
        <a class="youdao-link" id="youdaoLink" target="_blank" rel="noopener">在有道查看例句与更多 <span class="arr">↗</span></a>
      </div>
    </div>
  </div>
</main>

<div class="controls">
  <button class="ctrl-btn" id="prevBtn" title="上一个 ←">
    <svg viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>
  </button>
  <div class="progress" id="progress">— / —</div>
  <button class="ctrl-btn" id="nextBtn" title="下一个 →">
    <svg viewBox="0 0 24 24"><path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z"/></svg>
  </button>
  <button class="ctrl-btn" id="shuffleBtn" title="随机">
    <svg viewBox="0 0 24 24"><path d="M10.59 9.17L5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41l-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z"/></svg>
  </button>
</div>

<div class="footer">编辑 <code style="font-family:ui-monospace,monospace">听不出的词.md</code> 或点右下 + 添加 · 有道发音 + MyMemory 翻译</div>

<button class="fab" id="fab" title="添加单词">
  <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
</button>

<div class="modal-backdrop" id="modalBackdrop">
  <div class="modal" id="modal">
    <div class="modal-header">
      <div class="modal-title">添加听不出的词</div>
      <button class="modal-close" id="modalClose">✕</button>
    </div>
    <div class="modal-input-row">
      <input type="text" class="modal-input" id="wordInput" placeholder="输入英文单词，如 itinerary" autocomplete="off" spellcheck="false">
      <button class="modal-add" id="modalAdd">添加</button>
    </div>
    <div class="modal-section">当前词库 <span class="count" id="userCount">0</span></div>
    <div class="user-list" id="userList"></div>
    <div class="modal-hint">自动写入 听不出的词.md · 刷新即重新构建</div>
  </div>
</div>

<script>
let WORDS = __WORDS__;
const CACHE_KEY = 'listening-vocab-cache-v1';
const cache = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}');
const hasServer = location.protocol === 'http:' || location.protocol === 'https:';

let order = WORDS.map((_, i) => i);
let pos = 0;
let currentSpeed = 1;
let audio = null;
let revealMode = false;

const $ = s => document.querySelector(s);

function currentWord() { return WORDS[order[pos]]; }

function play(speed) {
  const word = currentWord();
  if (!word) return;
  if (audio) { audio.pause(); audio = null; }
  const s = speed || currentSpeed;
  audio = new Audio(`https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(word)}&type=1`);
  audio.playbackRate = s;
  const btn = $('#playBtn');
  btn.classList.add('playing');
  audio.play().catch(() => {});
  audio.onended = () => btn.classList.remove('playing');
  audio.onerror = () => btn.classList.remove('playing');
}

function showPlayStage() {
  $('#stagePlay').classList.remove('hidden');
  $('#stageWord').classList.add('hidden');
  $('#meaning').classList.remove('show');
  $('#detailBtn').style.display = '';
}

function showWordStage() {
  const w = currentWord();
  if (!w) return;
  $('#wordDisplay').textContent = w;
  $('#youdaoLink').href = `https://www.youdao.com/result?word=${encodeURIComponent(w)}&lang=en`;
  $('#stagePlay').classList.add('hidden');
  $('#stageWord').classList.remove('hidden');
  // reset meaning panel each time we land on a new word
  $('#meaning').classList.remove('show');
  $('#detailBtn').style.display = '';
  // re-trigger entrance animation
  $('#stageWord').classList.remove('word-stage');
  void $('#stageWord').offsetWidth;
  $('#stageWord').classList.add('word-stage');
}

function reveal() {
  revealMode = true;
  showWordStage();
}

function hideWord() {
  revealMode = false;
  showPlayStage();
}

async function loadMeaning() {
  const word = currentWord();
  const m = $('#meaning');
  const text = $('#meaningText');
  const btn = $('#detailBtn');

  if (cache[word]) {
    text.textContent = cache[word];
    m.classList.add('show');
    btn.style.display = 'none';
    return;
  }

  btn.style.display = 'none';
  m.classList.add('show');
  text.innerHTML = '<div class="spinner"></div>';

  try {
    const res = await fetch(`https://api.mymemory.translated.net/get?q=${encodeURIComponent(word)}&langpair=en|zh-CN`);
    const data = await res.json();
    const translation = (data.responseData && data.responseData.translatedText) || '未找到释义';
    cache[word] = translation;
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    text.textContent = translation;
  } catch (e) {
    text.textContent = '加载失败，请检查网络';
  }
}

function update() {
  if (!WORDS.length) {
    $('#card').innerHTML = '<div class="empty">还没有添加任何单词<br><br>编辑 <code>听不出的词.md</code><br>每行写一个单词，然后重新运行 <code>build.py</code></div>';
    $('#counter').textContent = '0';
    $('#progress').textContent = '0 / 0';
    return;
  }
  if (revealMode) showWordStage(); else showPlayStage();
  $('#counter').textContent = `${pos + 1} / ${WORDS.length}`;
  $('#progress').textContent = `${pos + 1} / ${WORDS.length}`;
  setTimeout(() => play(), 320);
}

function go(d) {
  if (!WORDS.length) return;
  pos = (pos + d + WORDS.length) % WORDS.length;
  update();
}

// Events
$('#playBtn').addEventListener('click', () => play());
$('#revealBtn').addEventListener('click', reveal);
$('#replayNormal').addEventListener('click', () => play(1));
$('#replaySlow').addEventListener('click', () => play(0.7));
$('#hideWord').addEventListener('click', hideWord);
$('#detailBtn').addEventListener('click', loadMeaning);
$('#prevBtn').addEventListener('click', () => go(-1));
$('#nextBtn').addEventListener('click', () => go(1));
$('#shuffleBtn').addEventListener('click', () => {
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  pos = 0;
  update();
});

document.querySelectorAll('.speed-btn').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.speed-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    currentSpeed = parseFloat(b.dataset.speed);
    play();
  });
});

// Modal: server-backed word management
const escapeHtml = s => s.replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]));

async function refreshWordsFromServer() {
  try {
    const res = await fetch('/api/words', { cache: 'no-store' });
    WORDS = await res.json();
    order = WORDS.map((_, i) => i);
    if (pos >= WORDS.length) pos = Math.max(0, WORDS.length - 1);
    renderUserList();
    update();
  } catch (e) { console.error(e); }
}

function renderUserList() {
  const list = $('#userList');
  $('#userCount').textContent = WORDS.length;
  list.innerHTML = WORDS.map(w => `
    <div class="user-item">
      <span class="w">${escapeHtml(w)}</span>
      <button class="del" data-w="${escapeHtml(w)}" title="删除">×</button>
    </div>
  `).join('');
  list.querySelectorAll('.del').forEach(b => {
    b.addEventListener('click', async () => {
      if (!hasServer) { alert('请通过 python3 build.py 启动服务器再操作'); return; }
      await fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word: b.dataset.w })
      });
      await refreshWordsFromServer();
    });
  });
}

async function addWord() {
  const input = $('#wordInput');
  const val = input.value.trim();
  if (!val) return;
  if (!hasServer) {
    input.value = '';
    input.placeholder = '请通过 python3 build.py 启动服务器';
    return;
  }
  if (WORDS.includes(val)) {
    input.value = '';
    input.placeholder = '已存在：' + val;
    setTimeout(() => { input.placeholder = '输入英文单词，如 itinerary'; }, 1600);
    return;
  }
  const res = await fetch('/api/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ word: val })
  });
  const data = await res.json();
  input.value = '';
  if (data.ok) {
    WORDS = data.words;
    order = WORDS.map((_, i) => i);
    renderUserList();
    update();
  }
}

function openModal() {
  $('#modalBackdrop').classList.add('show');
  if (hasServer) refreshWordsFromServer(); else renderUserList();
  setTimeout(() => $('#wordInput').focus(), 100);
}
function closeModal() { $('#modalBackdrop').classList.remove('show'); }

$('#fab').addEventListener('click', openModal);
$('#modalClose').addEventListener('click', closeModal);
$('#modalAdd').addEventListener('click', addWord);
$('#wordInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); addWord(); }
  else if (e.key === 'Escape') closeModal();
  e.stopPropagation();
});
$('#modalBackdrop').addEventListener('click', e => {
  if (e.target === $('#modalBackdrop')) closeModal();
});

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if ($('#modalBackdrop').classList.contains('show')) {
    if (e.key === 'Escape') closeModal();
    return;
  }
  if (e.key === ' ') { e.preventDefault(); play(); }
  else if (e.key === 'Enter') {
    e.preventDefault();
    if ($('#stageWord').classList.contains('hidden')) reveal();
    else if (!$('#meaning').classList.contains('show')) loadMeaning();
  }
  else if (e.key === 'ArrowRight') go(1);
  else if (e.key === 'ArrowLeft') go(-1);
});

update();
</script>
</body>
</html>'''.replace('__WORDS__', words_json)


def current_words() -> list[str]:
    return parse(MD.read_text(encoding='utf-8'))


def write_words(words: list[str]) -> None:
    header = "# 听力辨词 · 听不出的词\n# 每行一个单词（# 开头为注释）\n\n"
    MD.write_text(header + "\n".join(words) + "\n", encoding='utf-8')


def add_word(word: str) -> bool:
    word = word.strip()
    if not word:
        return False
    words = current_words()
    if word in words:
        return False
    words.append(word)
    write_words(words)
    return True


def delete_word(word: str) -> bool:
    words = current_words()
    if word not in words:
        return False
    words.remove(word)
    write_words(words)
    return True


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, status, body, ctype='application/json'):
        data = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', f'{ctype}; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            html = build(current_words())
            OUT.write_text(html, encoding='utf-8')
            self._send(200, html, 'text/html')
        elif self.path == '/api/words':
            self._send(200, json.dumps(current_words(), ensure_ascii=False))
        else:
            self._send(404, json.dumps({'error': 'not found'}))

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length).decode('utf-8') if length else ''
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._send(400, json.dumps({'error': 'invalid json'}))
            return

        if self.path == '/api/add':
            ok = add_word(data.get('word', ''))
            self._send(200, json.dumps({'ok': ok, 'words': current_words()}, ensure_ascii=False))
        elif self.path == '/api/delete':
            ok = delete_word(data.get('word', ''))
            self._send(200, json.dumps({'ok': ok, 'words': current_words()}, ensure_ascii=False))
        else:
            self._send(404, json.dumps({'error': 'not found'}))

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  · {fmt % args}\n")


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    if not MD.exists():
        MD.write_text("# 听力辨词 · 听不出的词\n# 每行一个单词\n\n", encoding='utf-8')

    # 预生成一份 index.html（离线也能看静态版）
    words = current_words()
    OUT.write_text(build(words), encoding='utf-8')
    print(f"📖 词库：{len(words)} 个单词")

    url = f'http://127.0.0.1:{PORT}/'
    with ReusableTCPServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f"🚀 服务已启动 → {url}")
        print(f"   修改来源：{MD}")
        print(f"   按 Ctrl+C 停止\n")
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 已停止")


if __name__ == '__main__':
    main()
