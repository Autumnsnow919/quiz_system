import streamlit as st
import re
import random

# ===========================
# 1. 界面配置与移动端适配 CSS
# ===========================
st.set_page_config(page_title="习概刷题神器", page_icon="📝", layout="centered")

st.markdown("""
    <style>
    /* 全局优化 */
    .stApp {
        background-color: #f4f6f9;
    }

    /* 题目卡片 - 移动端大字体优化 */
    .question-card {
        background-color: white;
        padding: 22px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
        font-size: 1.2rem; /* 加大字体 */
        font-weight: 500;
        color: #1a1a1a;
        line-height: 1.6;
    }

    /* 徽章样式 */
    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: bold;
        color: white;
        margin-right: 10px;
        vertical-align: middle;
        margin-bottom: 5px;
    }
    .badge-single { background-color: #3498db; }
    .badge-multi { background-color: #9b59b6; }
    .badge-judge { background-color: #e67e22; }

    /* 选项容器 */
    .stRadio, .stCheckbox {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 5px;
    }

    /* 结果反馈框 */
    .result-box {
        padding: 18px;
        border-radius: 10px;
        margin-top: 20px;
        font-size: 1.1rem;
        animation: fadeIn 0.5s;
    }
    .success { background-color: #d1e7dd; color: #0f5132; border: 1px solid #badbcc; }
    .error { background-color: #f8d7da; color: #842029; border: 1px solid #f5c2c7; }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
""", unsafe_allow_html=True)


# ===========================
# 2. 核心逻辑：超强容错解析器
# ===========================
@st.cache_data
def load_and_parse_questions(file_content):
    """
    针对用户提供的 tiku.txt 进行深度适配
    """
    # 1. 预处理：统一标点，替换全角点为半角点，方便正则
    raw_text = file_content.replace('．', '.')

    single_choice = []
    multi_choice = []
    judge_choice = []

    lines = raw_text.split('\n')
    current_section = None
    current_q = None

    # --- 正则表达式 ---
    # 匹配大标题 (一、单项... 二、多项... 三、判断...)
    section_pat = re.compile(r'^[一二三四]、\s*(.*)')
    # 匹配题目开头: "1.题目" 或 "10. 题目"
    q_start_pat = re.compile(r'^(\d+)\s*[.](.*)')
    # 匹配答案行: "答案：A" 或 "答案: 对"
    ans_pat = re.compile(r'^\s*答案\s*[：:]\s*(.*)', re.IGNORECASE)
    # 匹配解析行
    expl_pat = re.compile(r'^\s*答案解析\s*[：:]\s*(.*)')
    # 匹配选项开头: "A." 或 "A "
    opt_start_pat = re.compile(r'^\s*([A-E])\s*[.](.*)')

    def save_q(q):
        if not q: return
        # 修正：如果是判断题，强行生成选项
        if q['type'] == 'judge':
            q['options'] = {'A': '对', 'B': '错'}
            # 修正答案：将 '对' 转为 'A', '错' 转为 'B' 以便系统统一判断
            if '对' in q['answer']:
                q['answer'] = 'A'
            elif '错' in q['answer']:
                q['answer'] = 'B'

        if q['type'] == 'single':
            single_choice.append(q)
        elif q['type'] == 'multi':
            multi_choice.append(q)
        elif q['type'] == 'judge':
            judge_choice.append(q)

    for line in lines:
        line = line.strip()
        if not line: continue

        # --- 1. 识别大类 ---
        sec_match = section_pat.match(line)
        if sec_match:
            save_q(current_q)
            current_q = None
            title = sec_match.group(1)
            if "单项" in title:
                current_section = 'single'
            elif "多项" in title:
                current_section = 'multi'
            elif "判断" in title:
                current_section = 'judge'
            else:
                current_section = 'ignore'  # 忽略简答题
            continue

        if current_section == 'ignore': continue

        # --- 2. 识别题目开始 ---
        q_match = q_start_pat.match(line)
        if q_match:
            save_q(current_q)
            q_id = q_match.group(1)
            content_raw = q_match.group(2).strip()

            current_q = {
                'type': current_section,
                'id': q_id,
                'content': content_raw,
                'options': {},
                'answer': '',
                'explanation': ''
            }

            # 【关键修复】检测题目行是否粘连了选项 (例如: "1.题目内容A.选项")
            # 查找 content_raw 中第一次出现 " A." 或 " A " 的位置
            # 为了防止误判 (如单词 "A"), 我们要求 A 前面有空格，或者 A 后面有点
            inline_opt_match = re.search(r'(\s+[A-E]\s*[.].*)', content_raw)
            if inline_opt_match:
                # 发现粘连，截断题目，剩余部分作为新的一行处理
                opt_part = inline_opt_match.group(1)
                current_q['content'] = content_raw.replace(opt_part, "")
                line = opt_part.strip()  # 强制让后续逻辑处理这部分作为选项
            else:
                continue  # 题目行处理完毕，进入下一行

        # --- 3. 识别内容 (选项、答案、解析) ---
        if current_q:
            # 3.1 答案
            ans_match = ans_pat.match(line)
            if ans_match:
                # 去除可能的空格，转大写
                ans_text = ans_match.group(1).strip().upper()
                current_q['answer'] = ans_text
                continue

            # 3.2 解析
            expl_match = expl_pat.match(line)
            if expl_match:
                current_q['explanation'] = expl_match.group(1)
                continue

            # 3.3 选项 (仅单选/多选)
            if current_q['type'] in ['single', 'multi']:
                # 尝试在一行中查找所有选项 (A.xxx B.xxx)
                # 正则解释：找 A-E 开头，后面跟点，非贪婪匹配内容，直到遇到下一个 A-E+点 或 行尾
                inline_opts = list(re.finditer(r'([A-E])\s*[.]\s*(.*?)(?=\s+[A-E]\s*[.]|$)', line))

                if inline_opts:
                    for m in inline_opts:
                        k, v = m.group(1), m.group(2).strip()
                        current_q['options'][k] = v
                else:
                    # 如果不是选项开头，也不是答案/解析，那可能是长题目的换行
                    # 但要小心，不要把判断题的内容当成选项
                    opt_start = opt_start_pat.match(line)
                    if opt_start:
                        # 是标准选项行 A. xxx
                        current_q['options'][opt_start.group(1)] = opt_start.group(2).strip()
                    else:
                        # 既不是选项也不是标签，拼接到题目内容或上一个选项
                        if not current_q['options']:
                            current_q['content'] += line
                        else:
                            last_key = sorted(current_q['options'].keys())[-1]
                            current_q['options'][last_key] += " " + line

            # 3.4 判断题内容拼接
            elif current_q['type'] == 'judge':
                # 判断题没有选项行，所有非关键词行都属于题目
                if not line.startswith("答案") and not line.startswith("解析"):
                    current_q['content'] += line

    save_q(current_q)
    return single_choice, multi_choice, judge_choice


# ===========================
# 3. 状态管理
# ===========================
def init_session():
    if 'quiz_state' not in st.session_state:
        st.session_state.quiz_state = 'setup'
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0
    if 'user_submitted' not in st.session_state:
        st.session_state.user_submitted = False
    if 'raw_text' not in st.session_state:
        # 默认尝试读取本地文件
        try:
            with open("tiku.txt", "r", encoding="utf-8") as f:
                st.session_state.raw_text = f.read()
        except:
            st.session_state.raw_text = ""


def start_quiz(mode, num):
    s, m, j = load_and_parse_questions(st.session_state.raw_text)

    pool = []
    if mode == "单选题":
        pool = s
    elif mode == "多选题":
        pool = m
    elif mode == "判断题":
        pool = j
    else:
        pool = s + m + j

    if not pool:
        st.error(f"未解析到题目。当前检测到：单选{len(s)}题，多选{len(m)}题，判断{len(j)}题。请检查题库格式。")
        return

    real_num = min(num, len(pool))
    st.session_state.quiz_list = random.sample(pool, real_num)
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.quiz_state = 'playing'
    st.session_state.user_submitted = False
    st.rerun()


def next_question():
    st.session_state.current_idx += 1
    st.session_state.user_submitted = False
    if st.session_state.current_idx >= len(st.session_state.quiz_list):
        st.session_state.quiz_state = 'finished'
    st.rerun()


def restart():
    st.session_state.quiz_state = 'setup'
    st.rerun()


# ===========================
# 4. 主界面
# ===========================
def main():
    init_session()

    st.title("📝 习概刷题神器")

    # --- 侧边栏 ---
    with st.sidebar:
        st.header("⚙️ 题库设置")
        if not st.session_state.raw_text:
            st.warning("请上传 tiku.txt 或在下方粘贴")

        with st.expander("📝 粘贴/编辑题库"):
            st.session_state.raw_text = st.text_area("题库内容", value=st.session_state.raw_text, height=200)

        st.divider()
        st.subheader("开始测试")
        mode = st.selectbox("选择题型", ["单选题", "多选题", "判断题", "混合全练"])
        num = st.slider("题目数量", 5, 200, 20)

        if st.button("🚀 开始生成试卷", use_container_width=True, type="primary"):
            if st.session_state.raw_text:
                start_quiz(mode, num)
            else:
                st.error("题库内容为空！")

    # --- 页面逻辑 ---
    if st.session_state.quiz_state == 'setup':
        st.info("👈 请在左侧菜单栏配置并开始刷题")
        st.markdown("""
        ### 💡 2.0 版本更新说明
        1. **完美适配判断题**：自动识别“对/错”并生成选项。
        2. **智能纠错**：修复了选项和题目粘连的问题。
        3. **移动端优化**：大按钮、大字体，手机刷题更舒适。
        """)

    elif st.session_state.quiz_state == 'playing':
        idx = st.session_state.current_idx
        q_data = st.session_state.quiz_list[idx]
        total = len(st.session_state.quiz_list)

        # 进度条
        st.progress((idx + 1) / total)
        st.caption(f"当前进度: {idx + 1}/{total}")

        # 徽章逻辑
        badge_type = "badge-single"
        badge_label = "单选题"
        if q_data['type'] == 'multi':
            badge_type = "badge-multi";
            badge_label = "多选题"
        elif q_data['type'] == 'judge':
            badge_type = "badge-judge";
            badge_label = "判断题"

        # 题目卡片
        st.markdown(f"""
        <div class="question-card">
            <span class="badge {badge_type}">{badge_label}</span>
            {q_data['content']}
        </div>
        """, unsafe_allow_html=True)

        # 选项交互
        user_ans = []

        # --- 判断题特殊处理 ---
        if q_data['type'] == 'judge':
            # 判断题内部已转换为 A:对, B:错
            choice = st.radio("请判断：", ["对", "错"], index=None, horizontal=True, key=f"q_{idx}",
                              disabled=st.session_state.user_submitted)
            if choice == '对': user_ans = ['A']
            if choice == '错': user_ans = ['B']

        # --- 单选题 ---
        elif q_data['type'] == 'single':
            opts = sorted(q_data['options'].items())
            # 显示 A. xxx
            display_opts = [f"{k}. {v}" for k, v in opts]
            choice = st.radio("请选择：", display_opts, index=None, key=f"q_{idx}",
                              disabled=st.session_state.user_submitted)
            if choice: user_ans = [choice.split('.')[0]]

        # --- 多选题 ---
        elif q_data['type'] == 'multi':
            st.write("请选择（多选）：")
            opts = sorted(q_data['options'].items())
            for k, v in opts:
                if st.checkbox(f"{k}. {v}", key=f"q_{idx}_{k}", disabled=st.session_state.user_submitted):
                    user_ans.append(k)

        # 提交按钮
        st.markdown("---")
        if not st.session_state.user_submitted:
            if st.button("提交答案", type="primary", use_container_width=True):
                if not user_ans:
                    st.toast("⚠️ 请先完成作答", icon="⚠️")
                else:
                    st.session_state.user_submitted = True
                    st.rerun()
        else:
            # 判分逻辑
            u_str = "".join(sorted(user_ans))
            c_str = q_data['answer']  # 此时已经是清洗过的 ABC...

            is_correct = (u_str == c_str)

            # 显示结果
            if is_correct:
                st.markdown(f'<div class="result-box success">✅ <b>回答正确！</b></div>', unsafe_allow_html=True)
            else:
                # 如果是判断题，显示中文对错，否则显示字母
                display_correct = c_str
                if q_data['type'] == 'judge':
                    display_correct = "对" if c_str == 'A' else "错"

                st.markdown(f'<div class="result-box error">❌ <b>回答错误</b><br>正确答案：{display_correct}</div>',
                            unsafe_allow_html=True)

            # 显示解析
            if q_data['explanation']:
                with st.expander("📖 查看详细解析", expanded=True):
                    st.write(q_data['explanation'])

            # 翻页按钮
            btn_txt = "下一题 ➡" if idx < total - 1 else "查看成绩单 🏁"
            if st.button(btn_txt, type="primary", use_container_width=True):
                if is_correct: st.session_state.score += 1
                next_question()

    elif st.session_state.quiz_state == 'finished':
        st.balloons()
        score = st.session_state.score
        total = len(st.session_state.quiz_list)
        rate = score / total * 100

        st.markdown(f"""
        <div style="text-align: center; padding: 40px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <h1 style="font-size: 3rem;">🎉</h1>
            <h2>测试结束</h2>
            <div style="font-size: 3.5rem; font-weight: bold; color: {'#198754' if rate >= 60 else '#dc3545'}; margin: 20px 0;">
                {score} <span style="font-size: 1.5rem; color: #6c757d;">/ {total}</span>
            </div>
            <p>正确率：{rate:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 再来一轮", use_container_width=True):
            restart()


if __name__ == "__main__":
    main()
