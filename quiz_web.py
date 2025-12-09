import streamlit as st
import re
import random

# ===========================
# 1. 界面配置与移动端适配 CSS
# ===========================
st.set_page_config(page_title="习概刷题神器", page_icon="📝", layout="centered")

st.markdown("""
    <style>
    /* 全局背景 */
    .stApp {
        background-color: #f0f2f6;
    }

    /* 题目卡片样式 - 移动端适配优化 */
    .question-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 25px;
        font-size: 1.1rem; /* 稍微调大字体适合手机阅读 */
        font-weight: 500;
        color: #2c3e50;
        line-height: 1.6;
    }

    /* 徽章样式 */
    .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        color: white;
        margin-right: 8px;
        vertical-align: middle;
    }
    .badge-single { background-color: #3498db; }
    .badge-multi { background-color: #9b59b6; }
    .badge-judge { background-color: #e67e22; }

    /* 成功/失败 提示框 */
    .result-box {
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
        margin-bottom: 15px;
        font-weight: bold;
    }
    .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

    /* 调整移动端按钮间距 */
    div.stButton > button {
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)


# ===========================
# 2. 核心逻辑：智能题库解析
# ===========================
@st.cache_data
def load_and_parse_questions(file_content):
    """
    解析题库文本
    返回: (单选题列表, 多选题列表, 判断题列表)
    """
    single_choice = []
    multi_choice = []
    judge_choice = []

    lines = file_content.split('\n')
    current_section = None
    current_q = None

    # --- 正则表达式 ---
    # 匹配大标题：一、单项选择题 / 二、多项... / 三、判断题
    section_pat = re.compile(r'^[一二三四]、\s*(.*)')
    # 匹配题目开头：1. / 1． / 10.
    q_start_pat = re.compile(r'^(\d+)\s*[.．](.*)')
    # 匹配答案：答案：A / 答案：对 / 答案：错
    # 这里的正则兼容了字母和汉字(对/错)
    ans_pat = re.compile(r'^\s*答案\s*[：:]\s*([A-E]+|[对错])', re.IGNORECASE)
    # 匹配解析
    expl_pat = re.compile(r'^\s*答案解析\s*[：:]\s*(.*)')

    def save_q(q):
        if not q: return
        if q['type'] == 'single':
            single_choice.append(q)
        elif q['type'] == 'multi':
            multi_choice.append(q)
        elif q['type'] == 'judge':
            judge_choice.append(q)

    for line in lines:
        line = line.strip()
        if not line: continue

        # 1. 检测大标题
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

        # 2. 检测题目开始
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

        # 3. 解析题目详情
        if current_q:
            # 解析答案
            ans_match = ans_pat.match(line)
            if ans_match:
                raw_ans = ans_match.group(1).upper()  # 转大写
                current_q['answer'] = raw_ans
                continue

            # 解析解析
            expl_match = expl_pat.match(line)
            if expl_match:
                current_q['explanation'] = expl_match.group(1)
                continue

            # 解析选项 (仅针对单选和多选)
            if current_q['type'] in ['single', 'multi']:
                # 查找行内的 A. xxx B. xxx
                inline_opts = list(re.finditer(r'([A-E])\s*[.．]\s*(.*?)(?=\s+[A-E]\s*[.．]|$)', line))
                if inline_opts:
                    for m in inline_opts:
                        current_q['options'][m.group(1)] = m.group(2).strip()
                elif not line.startswith("答案"):
                    # 处理换行的情况
                    if not current_q['options']:
                        # 还没有选项，说明这一行属于题干的延续
                        current_q['content'] += line
                    else:
                        # 已经有选项了，说明这一行属于上一个选项的延续
                        last_key = sorted(current_q['options'].keys())[-1]
                        current_q['options'][last_key] += " " + line

            # 解析判断题 (内容直接拼接，直到遇到答案)
            elif current_q['type'] == 'judge':
                if not line.startswith("答案"):
                    current_q['content'] += line

    save_q(current_q)  # 保存最后一题
    return single_choice, multi_choice, judge_choice


# ===========================
# 3. 状态管理
# ===========================
def init_session():
    defaults = {
        'quiz_state': 'setup',
        'current_idx': 0,
        'score': 0,
        'quiz_list': [],
        'user_submitted': False,
        'raw_text': ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 尝试自动读取
    if not st.session_state.raw_text:
        try:
            with open("tiku.txt", "r", encoding="utf-8") as f:
                st.session_state.raw_text = f.read()
        except:
            pass


def start_quiz(mode, num):
    singles, multis, judges = load_and_parse_questions(st.session_state.raw_text)

    pool = []
    if mode == "单选题":
        pool = singles
    elif mode == "多选题":
        pool = multis
    elif mode == "判断题":
        pool = judges
    else:  # 混合模式
        pool = singles + multis + judges

    if not pool:
        st.error("⚠️ 未检测到题目！请检查 tiku.txt 是否包含有效内容。")
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
# 4. 主界面渲染
# ===========================
def main():
    init_session()

    # 顶部标题栏
    st.title("📝 习概刷题系统")

    # --- 侧边栏 ---
    with st.sidebar:
        st.header("⚙️ 设置")

        # 题库加载区
        if not st.session_state.raw_text:
            st.warning("未找到 tiku.txt")
            st.session_state.raw_text = st.text_area("请粘贴题库内容：", height=150)
        else:
            st.success(f"✅ 题库已就绪")
            with st.expander("查看/编辑题库"):
                st.session_state.raw_text = st.text_area("", st.session_state.raw_text, height=200)

        st.markdown("---")
        mode = st.selectbox("选择题型", ["单选题", "多选题", "判断题", "全题型混合"])
        num = st.slider("刷题数量", 5, 200, 10)

        if st.button("🚀 开始刷题", use_container_width=True, type="primary"):
            if st.session_state.raw_text:
                start_quiz(mode, num)
            else:
                st.error("请先导入题库")

    # --- 主逻辑 ---

    # 1. 初始页
    if st.session_state.quiz_state == 'setup':
        st.info("👈 请点击左上角箭头打开侧边栏进行设置")
        st.markdown("""
        ### 📱 移动端适配版
        - **支持题型**：单选、多选、判断
        - **智能解析**：自动忽略简答题
        - **操作便捷**：大按钮设计，防止误触
        """)

    # 2. 答题页
    elif st.session_state.quiz_state == 'playing':
        q_list = st.session_state.quiz_list
        idx = st.session_state.current_idx
        q_data = q_list[idx]
        total = len(q_list)

        # 进度条
        st.progress((idx + 1) / total)
        st.caption(f"进度：{idx + 1} / {total}")

        # 渲染题目卡片
        badge_class = "badge-single"
        badge_text = "单选"
        if q_data['type'] == 'multi':
            badge_class = "badge-multi";
            badge_text = "多选"
        elif q_data['type'] == 'judge':
            badge_class = "badge-judge";
            badge_text = "判断"

        st.markdown(f"""
        <div class="question-card">
            <span class="badge {badge_class}">{badge_text}</span>
            {q_data['content']}
        </div>
        """, unsafe_allow_html=True)

        # 渲染选项交互
        user_choice = []

        # --- 单选题 ---
        if q_data['type'] == 'single':
            opts = sorted(q_data['options'].items())
            opt_labels = [f"{k}. {v}" for k, v in opts]
            choice = st.radio(
                "请选择：", opt_labels, index=None, key=f"q_{idx}",
                disabled=st.session_state.user_submitted,
                label_visibility="collapsed"
            )
            if choice: user_choice = [choice.split('.')[0]]

        # --- 判断题 ---
        elif q_data['type'] == 'judge':
            choice = st.radio(
                "请判断：", ["对", "错"], index=None, key=f"q_{idx}",
                disabled=st.session_state.user_submitted,
                horizontal=True
            )
            if choice: user_choice = [choice]

        # --- 多选题 ---
        elif q_data['type'] == 'multi':
            st.write("请选择（多选）：")
            opts = sorted(q_data['options'].items())
            for k, v in opts:
                if st.checkbox(f"{k}. {v}", key=f"q_{idx}_{k}", disabled=st.session_state.user_submitted):
                    user_choice.append(k)

        # 按钮区
        st.markdown("<br>", unsafe_allow_html=True)
        if not st.session_state.user_submitted:
            if st.button("提交答案", type="primary", use_container_width=True):
                if not user_choice:
                    st.warning("请先做出选择")
                else:
                    st.session_state.user_submitted = True
                    st.rerun()
        else:
            # --- 判分逻辑 ---
            # 统一转换排序：多选 'BA' -> 'AB'
            u_ans = "".join(sorted(user_choice))
            c_ans = "".join(sorted(q_data['answer']))

            is_correct = (u_ans == c_ans)

            if is_correct:
                st.markdown(f'<div class="result-box success">✅ 回答正确！</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="result-box error">❌ 回答错误<br>正确答案：{c_ans}</div>',
                            unsafe_allow_html=True)

            # 解析
            if q_data['explanation']:
                with st.expander("🔍 查看解析", expanded=True):
                    st.write(q_data['explanation'])

            # 下一题按钮
            if idx < total - 1:
                if st.button("下一题 ➡", type="primary", use_container_width=True):
                    if is_correct: st.session_state.score += 1
                    next_question()
            else:
                if st.button("查看结果 🏁", type="primary", use_container_width=True):
                    if is_correct: st.session_state.score += 1
                    st.session_state.quiz_state = 'finished'
                    st.rerun()

    # 3. 结算页
    elif st.session_state.quiz_state == 'finished':
        st.balloons()
        score = st.session_state.score
        total = len(st.session_state.quiz_list)
        rate = score / total * 100

        st.markdown(f"""
        <div style="text-align: center; padding: 40px 20px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h2 style="color: #2c3e50;">测试完成！🎉</h2>
            <div style="font-size: 60px; color: {'#27ae60' if rate >= 60 else '#e74c3c'}; font-weight: bold; margin: 20px 0;">
                {score} <span style="font-size: 30px; color: #7f8c8d;">/ {total}</span>
            </div>
            <p style="font-size: 18px; color: #7f8c8d;">正确率: {rate:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 再刷一轮", type="primary", use_container_width=True):
            restart()


if __name__ == "__main__":
    main()
