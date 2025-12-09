import re
import random
import os


class QuizSystem:
    def __init__(self, filename="tiku.txt"):
        self.filename = filename
        self.single_choice_questions = []
        self.multi_choice_questions = []
        self.raw_data = ""

    def load_file(self):
        if not os.path.exists(self.filename):
            print(f"错误：未找到文件 '{self.filename}'。")
            print("请创建一个名为 tiku.txt 的文件，并将题库内容粘贴进去。")
            return False

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.raw_data = f.read()
            return True
        except UnicodeDecodeError:
            # Fallback for Windows encoding
            try:
                with open(self.filename, 'r', encoding='gbk') as f:
                    self.raw_data = f.read()
                return True
            except Exception as e:
                print(f"读取文件出错: {e}")
                return False

    def parse_questions(self):
        print("正在解析题库...")
        lines = self.raw_data.split('\n')

        current_section = None  # 'single', 'multi', or None
        current_q = None

        # Regex patterns
        # 匹配标题，如 "一、单项选择题"
        section_pat = re.compile(r'^[一二三四]、\s*(.*)')
        # 匹配题目开头，如 "1.关于..." 或 "10."
        q_start_pat = re.compile(r'^(\d+)\s*[.．](.*)')
        # 匹配选项，如 "A.xxx" 或 "A．xxx"
        opt_start_pat = re.compile(r'^\s*([A-E])\s*[.．]\s*(.*)')
        # 匹配答案，如 "答案：B" 或 "答案: ACD"
        ans_pat = re.compile(r'^\s*答案\s*[：:]\s*([A-E]+)', re.IGNORECASE)
        # 匹配解析
        expl_pat = re.compile(r'^\s*答案解析\s*[：:]\s*(.*)')

        for line in lines:
            line = line.strip()
            if not line: continue

            # 1. Check Section Header
            sec_match = section_pat.match(line)
            if sec_match:
                title = sec_match.group(1)
                if "单项" in title:
                    current_section = 'single'
                elif "多项" in title:
                    current_section = 'multi'
                else:
                    current_section = 'ignore'  # 忽略判断题和简答题
                # 保存上一个题目（如果存在）
                if current_q:
                    self._save_question(current_q)
                    current_q = None
                continue

            if current_section == 'ignore':
                continue

            # 2. Check Question Start
            q_match = q_start_pat.match(line)
            if q_match:
                # Save previous question
                if current_q:
                    self._save_question(current_q)

                # Start new question
                current_q = {
                    'type': current_section,
                    'id': q_match.group(1),
                    'content': q_match.group(2),
                    'options': {},
                    'answer': '',
                    'explanation': ''
                }
                continue

            # 3. Check Data within a question
            if current_q:
                # Check Answer
                ans_match = ans_pat.match(line)
                if ans_match:
                    current_q['answer'] = ans_match.group(1).upper()
                    continue

                # Check Explanation
                expl_match = expl_pat.match(line)
                if expl_match:
                    current_q['explanation'] = expl_match.group(1)
                    continue  # Assuming explanation is the last part usually

                # Check Options
                # 处理一行可能有多个选项的情况 (e.g., A.xxx B.xxx)
                # 使用正则查找行内所有 "A. " 模式
                # Pattern look for Letter+Dot followed by content until next Letter+Dot or End
                inline_opts = list(re.finditer(r'([A-E])\s*[.．]\s*(.*?)(?=\s+[A-E]\s*[.．]|$)', line))

                if inline_opts:
                    for m in inline_opts:
                        key = m.group(1)
                        val = m.group(2).strip()
                        current_q['options'][key] = val
                elif not line.startswith("答案"):
                    # 如果不是选项开头，也不是答案，可能是题目内容的换行
                    # 但也要防止解析内容被误加
                    if not current_q['answer']:
                        # 还没找到答案，说明这行属于题目描述或者上一行选项的延续
                        # 简单的逻辑：如果没有选项，拼接到题目；如果有选项，拼接到最后一个选项
                        if not current_q['options']:
                            current_q['content'] += "\n" + line
                        else:
                            # 拼接到最后一个选项
                            last_key = sorted(current_q['options'].keys())[-1]
                            current_q['options'][last_key] += " " + line

        # Save the very last question
        if current_q:
            self._save_question(current_q)

        print(
            f"解析完成！共加载 {len(self.single_choice_questions)} 道单选题，{len(self.multi_choice_questions)} 道多选题。")

    def _save_question(self, q):
        if q['type'] == 'single':
            self.single_choice_questions.append(q)
        elif q['type'] == 'multi':
            self.multi_choice_questions.append(q)

    def run_quiz(self):
        print("\n" + "=" * 30)
        print("    习概题库随机刷题系统")
        print("=" * 30)

        while True:
            mode = input("\n请选择题型 (1: 单选题, 2: 多选题, 3: 混合模式, q: 退出): ").strip()
            if mode == 'q':
                break

            pool = []
            if mode == '1':
                pool = self.single_choice_questions
            elif mode == '2':
                pool = self.multi_choice_questions
            elif mode == '3':
                pool = self.single_choice_questions + self.multi_choice_questions
            else:
                print("无效输入")
                continue

            if not pool:
                print("当前题库为空，无法开始。")
                continue

            try:
                num = int(input(f"请输入刷题数量 (最大 {len(pool)}): "))
            except ValueError:
                num = 5

            num = min(num, len(pool))
            quiz_set = random.sample(pool, num)

            score = 0
            print(f"\n=== 开始测试 (共 {num} 题) ===")

            for idx, q in enumerate(quiz_set, 1):
                q_type_str = "单选" if q['type'] == 'single' else "多选"
                print(f"\n[{idx}/{num}] 【{q_type_str}】 {q['content']}")

                sorted_keys = sorted(q['options'].keys())
                for key in sorted_keys:
                    print(f"  {key}. {q['options'][key]}")

                user_ans = input("请输入答案: ").strip().upper()
                # 去除可能的空格或标点，只保留字母
                user_ans_clean = "".join(filter(str.isalpha, user_ans))
                # 多选题自动排序比较 (比如输入BA，自动变成AB进行比对)
                user_ans_sorted = "".join(sorted(user_ans_clean))
                correct_ans_sorted = "".join(sorted(q['answer']))

                if user_ans_sorted == correct_ans_sorted:
                    print("✅ 回答正确！")
                    score += 1
                else:
                    print(f"❌ 回答错误。正确答案是: {q['answer']}")
                    if q['explanation']:
                        print(f"   解析: {q['explanation']}")

            print(f"\n测试结束！你的得分: {score}/{num} ({(score / num) * 100:.1f}%)")


if __name__ == "__main__":
    app = QuizSystem()
    if app.load_file():
        app.parse_questions()
        app.run_quiz()

    input("\n按回车键退出...")
