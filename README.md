# 雅思备考

个人雅思备考笔记与工具，基于剑桥雅思真题集（CAM 5–20）。

## 在线工具

- **Flashcard 生词本**: https://superlls.github.io/IELTS-Preparing/
- **口语复习网页**: https://superlls.github.io/IELTS-Preparing/speaking.html

## 项目结构

```
├── 生词本.md              # 词汇笔记（词义、对比、例句、备考提示）
├── 口语表达.md            # 口语常见表达（中英文对照、关键词汇）
├── build.py              # 生成 flashcard 网页并自动部署
├── build_speaking.py     # 生成口语复习网页并自动部署
├── index.html            # 生成的 flashcard 网页
├── speaking.html         # 生成的口语复习网页
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

更新口语表达后，运行以下命令重新生成并部署：

```bash
python3 build_speaking.py
```
