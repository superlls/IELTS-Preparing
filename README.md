# 雅思备考

个人雅思备考笔记与工具，基于剑桥雅思真题集（CAM 5–20）。

## 在线 Flashcard

**https://superlls.github.io/IELTS-Preparing/**

生词本词汇卡片，支持翻转、搜索、随机、列表模式。

## 项目结构

```
├── 生词本.md              # 词汇笔记（词义、对比、例句、备考提示）
├── build.py              # 生成 flashcard 网页并自动部署
├── index.html            # 生成的 flashcard 网页
├── Listening/            # 听力练习笔记（CAM 5–20 × Test1–4 × Section1–4）
├── Reading/              # 阅读练习笔记
├── Speaking/             # 口语练习笔记
└── Writing/              # 写作练习笔记
```

## 使用方法

更新生词本后，运行以下命令重新生成并部署：

```bash
python3 build.py
```
