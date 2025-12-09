import streamlit as st
import re
import random
import time

# ===========================
# 1. 界面配置与 CSS 美化
# ===========================
st.set_page_config(page_title="习概题库刷题系统", page_icon="🎓", layout="centered")

# 自定义 CSS 让界面更好看
st.markdown("""
    <style>
    .stApp {
        background-color: #f5f7f9;
    }
    .question-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        font-size: 18px;
        font-weight: 500;
        color: #333;
    }
    .option-box {
        font-size: 16px;
    }
    .success-msg {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .error-msg {
        padding: 10px;
        border-radius: 5px;
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    </style>
""", unsafe_allow_html=True)


# ===========================
# 2. 核心逻辑：题库解析
# ===========================
@st.cache_data
def load_and_parse_questions(file_content):
    """解析题库文本，返回单选题和多选题列表"""
    single_choice = []
    multi_choice = []

    lines = file_content.split('\n')
    current_section = None
    current_q = None

    # 正则表达式预编译
    section_pat = re.compile(r'^[一二三四]、\s*(.*)')
    q_start_pat = re.compile(r'^(\d+)\s*[.．](.*)')
    ans_pat = re.compile(r'^\s*答案\s*[：:]\s*([A-E]+)', re.IGNORECASE)
    expl_pat = re.compile(r'^\s*答案解析\s*[：:]\s*(.*)')

    def save_q(q):
        if q and q['type'] == 'single':
            single_choice.append(q)
        elif q and q['type'] == 'multi':
            multi_choice.append(q)

    for line in lines:
        line = line.strip()
        if not line: continue

        # 识别大标题
        sec_match = section_pat.match(line)
        if sec_match:
            save_q(current_q)
            current_q = None
            title = sec_match.group(1)
            if "单项" in title:
                current_section = 'single'
            elif "多项" in title:
                current_section = 'multi'
            else:
                current_section = 'ignore'
            continue

        if current_section == 'ignore': continue

        # 识别题目开始
        q_match = q_start_pat.match(line)
        if q_match:
            save_q(current_q)
            current_q = {
                'type': current_section,
                'id': q_match.group(1),
                'content': q_match.group(2),
                'options': {},
                'answer': '',
                'explanation': ''
            }
            continue

        # 识别题目内容
        if current_q:
            # 识别答案
            ans_match = ans_pat.match(line)
            if ans_match:
                current_q['answer'] = ans_match.group(1).upper()
                continue

            # 识别解析
            expl_match = expl_pat.match(line)
            if expl_match:
                current_q['explanation'] = expl_match.group(1)
                continue

            # 识别选项 (支持同一行多个选项或换行选项)
            inline_opts = list(re.finditer(r'([A-E])\s*[.．]\s*(.*?)(?=\s+[A-E]\s*[.．]|$)', line))
            if inline_opts:
                for m in inline_opts:
                    current_q['options'][m.group(1)] = m.group(2).strip()
            elif not line.startswith("答案"):
                # 如果不是答案行，拼接到题目或最后一个选项
                if not current_q['options']:
                    current_q['content'] += line
                else:
                    last_key = sorted(current_q['options'].keys())[-1]
                    current_q['options'][last_key] += " " + line

    save_q(current_q)
    return single_choice, multi_choice


# ===========================
# 3. 状态管理
# ===========================
def init_session():
    if 'quiz_state' not in st.session_state:
        st.session_state.quiz_state = 'setup'  # setup, playing, finished
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'quiz_list' not in st.session_state:
        st.session_state.quiz_list = []
    if 'user_submitted' not in st.session_state:
        st.session_state.user_submitted = False
    if 'raw_text' not in st.session_state:
        # 尝试自动读取本地文件
        try:
            with open("tiku.txt", "r", encoding="utf-8") as f:
                st.session_state.raw_text = f.read()
        except:
            st.session_state.raw_text = ""


def start_quiz(mode, num):
    singles, multis = load_and_parse_questions(st.session_state.raw_text)

    pool = []
    if mode == "单选题":
        pool = singles
    elif mode == "多选题":
        pool = multis
    else:
        pool = singles + multis

    if not pool:
        st.error("未检测到题目，请检查题库内容是否粘贴正确。")
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
# 4. 界面渲染
# ===========================
def main():
    init_session()

    st.title("🎓 习概题库刷题系统")

    # --- 侧边栏：设置 ---
    with st.sidebar:
        st.header("⚙️ 设置")

        # 允许用户粘贴题库（如果没有自动读取到文件）
        if not st.session_state.raw_text:
            st.warning("未检测到 tiku.txt")
            user_input = st.text_area("请在此处粘贴题库内容：", height=200)
            if user_input:
                st.session_state.raw_text = user_input
        else:
            st.success("✅ 已加载题库文件")
            with st.expander("查看/更新题库内容"):
                new_text = st.text_area("题库内容", value=st.session_state.raw_text, height=150)
                if new_text != st.session_state.raw_text:
                    st.session_state.raw_text = new_text

        st.divider()

        mode = st.radio("选择题型", ["单选题", "多选题", "混合模式 (单选+多选)"])
        num_questions = st.number_input("刷题数量", min_value=1, max_value=200, value=10)

        if st.button("🚀 开始测试", use_container_width=True):
            if st.session_state.raw_text:
                start_quiz(mode, num_questions)
            else:
                st.error("请先提供题库内容！")

    # --- 主界面逻辑 ---

    # 1. 准备阶段
    if st.session_state.quiz_state == 'setup':
        st.info("👈 请在左侧侧边栏配置并点击“开始测试”")
        st.markdown("""
        ### 使用说明：
        1. 确保目录下有 `tiku.txt` 文件，或者在左侧粘贴文本。
        2. 选择你想练习的题型。
        3. 系统会自动随机抽取题目。
        4. 交卷后会立即显示解析。
        """)
        st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=100)

    # 2. 答题阶段
    elif st.session_state.quiz_state == 'playing':
        total = len(st.session_state.quiz_list)
        current = st.session_state.current_idx
        q_data = st.session_state.quiz_list[current]

        # 进度条
        progress = (current) / total
        st.progress(progress)
        st.caption(f"进度: {current + 1} / {total}")

        # 题目卡片
        type_badge = "🔵 单选" if q_data['type'] == 'single' else "🟣 多选"
        st.markdown(f"""
        <div class="question-card">
            {type_badge} {q_data['content']}
        </div>
        """, unsafe_allow_html=True)

        # 选项显示
        sorted_opts = sorted(q_data['options'].items())
        user_choice = []

        # 根据题型渲染不同的输入组件
        if q_data['type'] == 'single':
            # 使用 radio，为了方便判断，我们在选项前加 A. B.
            options_display = [f"{k}. {v}" for k, v in sorted_opts]
            # 如果已经提交了，禁用输入
            choice = st.radio(
                "请选择答案：",
                options_display,
                index=None,
                key=f"q_{current}",
                disabled=st.session_state.user_submitted
            )
            if choice:
                user_choice = [choice.split('.')[0]]
        else:
            # 多选使用 checkbox
            st.write("请选择答案（多选）：")
            for k, v in sorted_opts:
                checked = st.checkbox(
                    f"{k}. {v}",
                    key=f"q_{current}_{k}",
                    disabled=st.session_state.user_submitted
                )
                if checked:
                    user_choice.append(k)

        # 提交按钮
        if not st.session_state.user_submitted:
            if st.button("提交答案", type="primary"):
                st.session_state.user_submitted = True
                st.rerun()
        else:
            # --- 判定逻辑 ---
            user_ans_str = "".join(sorted(user_choice))
            correct_ans_str = "".join(sorted(q_data['answer']))

            is_correct = (user_ans_str == correct_ans_str)

            if is_correct:
                st.markdown('<div class="success-msg">✅ <b>回答正确！</b></div>', unsafe_allow_html=True)
                # 防止重复加分 (Streamlit 刷新机制) - 这里的简易逻辑依赖于只点一次 Next
            else:
                st.markdown(f'<div class="error-msg">❌ <b>回答错误</b></div>', unsafe_allow_html=True)
                st.write(f"**正确答案：** `{q_data['answer']}`")

            # 显示解析
            if q_data['explanation']:
                with st.expander("📖 查看解析", expanded=True):
                    st.write(q_data['explanation'])

            # 下一题按钮
            col1, col2 = st.columns([4, 1])
            with col2:
                btn_text = "下一题 ➡" if current < total - 1 else "查看结果 🏁"
                if st.button(btn_text, type="primary"):
                    if is_correct:
                        st.session_state.score += 1
                    next_question()

    # 3. 结算界面
    elif st.session_state.quiz_state == 'finished':
        st.balloons()
        st.markdown(f"""
        <div style="text-align: center; padding: 50px;">
            <h1>🎉 测试完成！</h1>
            <h2>你的得分</h2>
            <h1 style="color: #00cc66; font-size: 80px;">{st.session_state.score} / {len(st.session_state.quiz_list)}</h1>
            <p>准确率: {(st.session_state.score / len(st.session_state.quiz_list)) * 100:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.button("🔄 再来一轮", on_click=restart, use_container_width=True)


if __name__ == "__main__":
    main()
