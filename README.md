# 🎓 习概题库刷题系统 (Web版)

这是一个基于 **Python** 和 **Streamlit** 开发的轻量级 Web 端刷题工具。专为《习近平新时代中国特色社会主义思想概论》课程复习设计，支持单选题和多选题的随机抽查、即时判分和解析查看。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg) ![Streamlit](https://img.shields.io/badge/Streamlit-App-ff4b4b.svg)

## ✨ 功能特点

*   **💻 Web 交互界面**：清爽的卡片式设计，支持夜间/日间模式。
*   **🔀 智能识别**：自动解析文本文件，区分单选题和多选题。
*   **🎲 随机出题**：支持自定义刷题数量，防止背答案位置。
*   **✅ 即时反馈**：提交答案后立即判断对错，并显示解析。
*   **📋 灵活导入**：支持本地 `tiku.txt` 或网页直接粘贴文本。

## 🛠️ 环境依赖

请确保安装 Python 环境，并安装以下库：
```bash
pip install streamlit
```

## 🚀 快速开始

### 1. 启动方式
**注意：不能直接双击脚本！** 请在终端（CMD/PowerShell）运行：

**方式 A (推荐)**：
```bash
streamlit run web_quiz.py
```

**方式 B (Anaconda 用户)**：
```bash
D:\Anaconda\python.exe -m streamlit run web_quiz.py
```

### 2. 开始刷题
浏览器会自动打开 `http://localhost:8501`。
*   如果没有自动加载题库，请在左侧侧边栏粘贴你的题目内容。
*   点击 **“开始测试”** 即可。

## 📝 题库格式说明

请将题目保存为 `tiku.txt`，格式如下（系统会自动忽略判断/简答题）：

```text
一、单项选择题
1. 题目内容...
A. 选项A
B. 选项B
答案：A
答案解析：...

二、多项选择题
1. 题目内容...
A. 选项A
B. 选项B
C. 选项C
答案：ABC
```

## ❓ 常见报错

*   **报错 `missing ScriptRunContext`**：
    *   原因：你直接用了 `python web_quiz.py`。
    *   解决：必须用 `streamlit run web_quiz.py`。

*   **网页提示“未检测到 tiku.txt”**：
    *   解决：请确保 txt 文件和 py 文件在同一目录下，或者直接在网页左侧文本框粘贴内容。

---
祝考试高分！ 💯
