# app.py

import streamlit as st
import random
import pandas as pd
import altair as alt
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

import parser
import database

APP_VERSION = "v1.5.0"

database.init_db()

# --- セッション状態の管理 ---
def initialize_session_state():
    if 'page' not in st.session_state: st.session_state.page = 'start'
    if 'questions' not in st.session_state: st.session_state.questions = []
    if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
    if 'user_answers' not in st.session_state: st.session_state.user_answers = {}
    if 'all_questions_from_file' not in st.session_state: st.session_state.all_questions_from_file = None
    if 'raw_content' not in st.session_state: st.session_state.raw_content = None
    if 'parser_debug_log' not in st.session_state: st.session_state.parser_debug_log = None
    if 'ui_debug_log' not in st.session_state: st.session_state.ui_debug_log = []
    if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False
    if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0
    if 'is_study_mode' not in st.session_state: st.session_state.is_study_mode = False
    if 'start_question_id' not in st.session_state: st.session_state.start_question_id = 1
    if 'excluded_question_ids' not in st.session_state: st.session_state.excluded_question_ids = set()

def reset_test_state():
    st.session_state.page = 'start'
    st.session_state.questions = []
    st.session_state.user_answers = {}
    st.session_state.current_q_index = 0
    st.session_state.confirm_reset = False
    st.session_state.is_study_mode = False
    st.session_state.start_question_id = 1
    st.rerun()

initialize_session_state()

# --- ヘルパー関数 ---
def start_session(questions: List[Dict[str, Any]], is_study_mode: bool = False):
    st.session_state.questions = [q for q in questions if q.get('question_type') != 'unknown']
    st.session_state.current_q_index = 0
    st.session_state.is_study_mode = is_study_mode
    st.session_state.user_answers = {}
    st.session_state.ui_debug_log = []
    st.session_state.page = 'study' if is_study_mode else 'test'
    st.rerun()

def calculate_score():
    score = 0
    details = []
    for q in st.session_state.questions:
        user_ans, q_type = st.session_state.user_answers.get(q['id']), q.get('question_type', 'single')
        is_correct = False
        if user_ans is None: user_ans = {} if q_type in ['order', 'match'] else []
        if q_type == 'order': is_correct = ([user_ans.get(str(i)) for i in range(1, len(q['correct_answers']) + 1)] == q['correct_answers'])
        elif q_type == 'match': is_correct = (user_ans == q['correct_answers'])
        else: is_correct = (sorted(user_ans) == q['correct_answers'])
        if is_correct: score += 1
        details.append({'id': q['id'], 'question_type': q_type, 'question': q['question'], 'options': q['options'], 'user_answer': user_ans, 'correct_answer': q['correct_answers'], 'is_correct': is_correct, 'explanation': q['explanation']})
    return score, details

# --- ページ描画関数 ---
def render_start_page():
    st.title("模擬試験アプリ")
    
    tab1, tab2, tab3, tab4 = st.tabs(["開始", "学習履歴", "苦手問題", "更新履歴"])

    with tab1:
        st.header("学習の準備")
        source_option = st.radio("問題ファイルの選択方法:", ('フォルダから選択', 'ファイルをアップロード'), horizontal=True, key='source_option')
        loaded_file_id = None
        
        if source_option == 'フォルダから選択':
            QUESTIONS_DIR = Path("questions")
            if not QUESTIONS_DIR.exists():
                QUESTIONS_DIR.mkdir(); st.info(f"`{QUESTIONS_DIR}` フォルダを作成しました。このフォルダに問題ファイル（.md）を置いてください。"); return
            question_files = sorted(list(QUESTIONS_DIR.glob("*.md")))
            if not question_files:
                st.warning(f"`{QUESTIONS_DIR}` フォルダに問題ファイル（.md）が見つかりません。ファイルを置いてからページを更新してください。")
            else:
                file_names = [f.name for f in question_files]
                options = ["-- 選択してください --"] + file_names
                default_index = 0
                if 'selected_file' in st.session_state and st.session_state.selected_file in options:
                    default_index = options.index(st.session_state.selected_file)
                selected_file_name = st.selectbox("問題集ファイルを選択してください:", options, index=default_index)
                st.session_state.selected_file = selected_file_name
                if selected_file_name != "-- 選択してください --":
                    selected_file_path = QUESTIONS_DIR / selected_file_name
                    if st.session_state.get('loaded_file_path') != str(selected_file_path):
                        with st.spinner(f"「{selected_file_name}」を読み込んでいます..."):
                            content = selected_file_path.read_text(encoding="utf-8")
                            st.session_state.raw_content = content
                            st.session_state.all_questions_from_file, _ = parser.parse_md_content(content, debug=False)
                            st.session_state.loaded_file_path = str(selected_file_path)
                        if not st.session_state.all_questions_from_file: st.error("問題ファイルから問題を読み込めませんでした。")
                        st.rerun()
                    loaded_file_id = selected_file_name
        elif source_option == 'ファイルをアップロード':
            uploaded_file = st.file_uploader("問題集ファイル（.md）をアップロード", type=['md'], key=f"uploader_{st.session_state.uploader_key}")
            if uploaded_file:
                if st.session_state.get('loaded_file_path') != uploaded_file.name:
                    with st.spinner(f"「{uploaded_file.name}」を読み込んでいます..."):
                        content = uploaded_file.read().decode("utf-8")
                        st.session_state.raw_content = content
                        st.session_state.all_questions_from_file, _ = parser.parse_md_content(content, debug=False)
                        st.session_state.loaded_file_path = uploaded_file.name
                    if not st.session_state.all_questions_from_file: st.error("問題ファイルから問題を読み込めませんでした。")
                    st.rerun()
                loaded_file_id = uploaded_file.name

        if st.session_state.get('all_questions_from_file'):
            if not loaded_file_id and st.session_state.get('loaded_file_path'):
                loaded_file_id = Path(st.session_state.loaded_file_path).name

            st.success(f"問題ファイルを読み込み済みです: **{loaded_file_id}** （{len(st.session_state.all_questions_from_file)}問）")
            
            with st.expander("出題対象の問題を管理"):
                all_questions = st.session_state.get('all_questions_from_file', [])

                st.markdown("##### 一括操作")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("すべての問題を除外する", use_container_width=True):
                        all_ids = {q['id'] for q in all_questions}
                        st.session_state.excluded_question_ids.update(all_ids); st.rerun()
                with col2:
                    if st.button("すべての問題を対象に戻す", use_container_width=True):
                        st.session_state.excluded_question_ids.clear(); st.rerun()

                if all_questions:
                    st.markdown("##### 範囲指定で一括変更")
                    q_ids = [q['id'] for q in all_questions]
                    min_q_id, max_q_id = min(q_ids), max(q_ids)
                    
                    range_col1, range_col2 = st.columns(2)
                    start_num = range_col1.number_input("開始番号", min_value=min_q_id, max_value=max_q_id, value=min_q_id)
                    end_num = range_col2.number_input("終了番号", min_value=min_q_id, max_value=max_q_id, value=max_q_id)
                    
                    range_btn_col1, range_btn_col2 = st.columns(2)
                    if range_btn_col1.button("この範囲を除外", use_container_width=True):
                        ids_to_exclude = {q['id'] for q in all_questions if start_num <= q['id'] <= end_num}
                        st.session_state.excluded_question_ids.update(ids_to_exclude); st.rerun()
                    if range_btn_col2.button("この範囲を対象に戻す", use_container_width=True):
                        ids_to_include = {q['id'] for q in all_questions if start_num <= q['id'] <= end_num}
                        st.session_state.excluded_question_ids.difference_update(ids_to_include); st.rerun()

                st.divider()
                st.markdown("##### 個別操作")
                st.write("チェックを入れた問題がテスト・学習の対象から**除外**されます。")
                for q in sorted(all_questions, key=lambda x: x['id']):
                    q_id = q['id']
                    is_excluded = q_id in st.session_state.excluded_question_ids
                    newly_excluded = st.checkbox(f"**Q{q_id}:** {q['question'].splitlines()[0][:80]}...", value=is_excluded, key=f"manage_exclude_{q_id}")
                    if newly_excluded and not is_excluded: st.session_state.excluded_question_ids.add(q_id)
                    elif not newly_excluded and is_excluded: st.session_state.excluded_question_ids.remove(q_id)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("管理者機能"): st.session_state.page = 'admin_debug'; st.rerun()
            with col2:
                if st.button("ファイルをクリア"):
                    keys_to_reset = ['all_questions_from_file', 'raw_content', 'parser_debug_log', 'ui_debug_log', 'loaded_file_path', 'selected_file', 'excluded_question_ids']
                    for key in keys_to_reset:
                        if key in st.session_state: del st.session_state[key]
                    initialize_session_state(); st.session_state.uploader_key += 1; st.rerun()

            st.subheader("モードを選択"); session_mode = st.radio("実施したいモードを選んでください:", ('テストモード', '学習モード'), horizontal=True)
            problem_mode = st.radio("出題形式:", ('すべての問題を順番通り', 'すべての問題をランダムに', '指定した問題数をランダムに', '指定した問題番号から開始'), key='problem_mode', horizontal=True)
            
            excluded_ids = st.session_state.excluded_question_ids
            valid_questions = [q for q in st.session_state.all_questions_from_file if q.get('question_type') != 'unknown' and q['id'] not in excluded_ids]
            
            total_valid_qs = len(valid_questions)
            st.info(f"出題対象の問題数: **{total_valid_qs}**問 (うち{len(excluded_ids)}問が除外中)")

            num_questions = 0
            if total_valid_qs > 0:
                if problem_mode == '指定した問題数をランダムに':
                    num_questions = st.number_input('出題数:', min_value=1, max_value=total_valid_qs, value=min(10, total_valid_qs))
                elif problem_mode == '指定した問題番号から開始':
                    min_q_id = min([q['id'] for q in valid_questions]) if valid_questions else 1
                    max_q_id = max([q['id'] for q in valid_questions]) if valid_questions else 1
                    st.session_state.start_question_id = st.number_input('開始する問題番号:', min_value=min_q_id, max_value=max_q_id, value=st.session_state.start_question_id, key='start_q_id_input')
            else:
                st.warning("出題できる問題がありません。除外設定を確認してください。")

            button_label = "テスト開始" if session_mode == 'テストモード' else "学習開始"
            if st.button(button_label, type="primary", disabled=(total_valid_qs == 0)):
                questions_to_start = []
                if problem_mode == 'すべての問題を順番通り': 
                    questions_to_start = sorted(valid_questions, key=lambda x: x['id'])
                elif problem_mode == 'すべての問題をランダムに': 
                    questions_to_start = random.sample(valid_questions, total_valid_qs)
                elif problem_mode == '指定した問題数をランダムに':
                    if num_questions > 0: questions_to_start = random.sample(valid_questions, num_questions)
                elif problem_mode == '指定した問題番号から開始':
                    filtered_questions = [q for q in valid_questions if q['id'] >= st.session_state.start_question_id]
                    if not filtered_questions:
                        st.error(f"問題番号 {st.session_state.start_question_id} 以降の出題可能な問題が見つかりませんでした。")
                    else:
                        questions_to_start = sorted(filtered_questions, key=lambda x: x['id'])

                if questions_to_start: start_session(questions_to_start, is_study_mode=(session_mode == '学習モード'))
                elif total_valid_qs > 0: st.error("出題できる問題がありません。設定を確認してください。")
        
        st.divider()
        st.caption(f"アプリバージョン: {APP_VERSION}")

    with tab2:
        st.header("学習履歴")
        history = database.get_all_test_results()
        if history:
            df_history = pd.DataFrame(history, columns=['timestamp', 'score', 'total_questions', 'correct_rate'])
            df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
            st.subheader("正答率の推移")
            chart = alt.Chart(df_history).mark_line(point=True).encode(x=alt.X('timestamp:T', title='テスト実施日時'), y=alt.Y('correct_rate:Q', title='正答率', axis=alt.Axis(format='%')), tooltip=['timestamp:T', 'correct_rate:Q']).interactive()
            st.altair_chart(chart, use_container_width=True)
            st.subheader("全テスト履歴")
            df_table = df_history.copy()
            df_table['正答率'] = df_table['correct_rate'].map('{:.1%}'.format)
            st.dataframe(df_table[['timestamp', 'score', 'total_questions', '正答率']].rename(columns={'timestamp': '日時', 'score': '正解数', 'total_questions': '問題数'}), hide_index=True)
            if st.button("全学習履歴をリセット", key="reset_hist_tab"): st.session_state.confirm_reset = True
        else: st.info("まだテスト履歴がありません。")

    with tab3:
        st.header("苦手問題ランキング TOP 5")
        ranking = database.get_wrong_answer_ranking(limit=5)
        if ranking:
            df_ranking = pd.DataFrame(ranking, columns=['問題ID', '問題文', '間違い回数'])
            df_ranking['問題文'] = df_ranking['問題文'].str.replace('\n', ' ').str.slice(0, 50) + '...'
            st.dataframe(df_ranking, hide_index=True)
        else: st.info("まだ間違えた問題はありません。")

    with tab4:
        st.header("更新履歴")
        st.markdown(f"**現在のバージョン: {APP_VERSION}**")
        st.markdown("---")
        st.subheader(f"v1.5.0 ({datetime.now().strftime('%Y/%m/%d')})")
        st.markdown("- **機能追加:** 問題番号の範囲を指定して、一括で出題対象から除外／復帰させる機能を追加しました。\n- **機能削除:** ユーザーごとの設定保存機能（簡易ログイン）を削除し、セッション内でのみ設定を保持する仕様に戻しました。")
        st.subheader("v1.3.0")
        st.markdown("- **機能改善:** Streamlitサーバーの設定 (`.streamlit/config.toml`) により、非アクティブな状態でもセッションがタイムアウトしないようにしました。")
        st.subheader("v1.2.0")
        st.markdown("- **機能追加:** アプリのバージョンと更新履歴を確認できるタブを追加しました。\n- **機能改善:** 開始ページに、問題一覧から直接チェックを入れて出題対象から除外できる管理機能を追加しました。\n- **機能改善:** 除外管理機能に「すべて除外」「すべて対象に戻す」ボタンを追加し、一括操作を可能にしました。")
        st.subheader("v1.1.0")
        st.markdown("- **機能追加:** 学習モードおよびテスト結果画面で、理解した問題を次回から除外するチェックボックス機能を追加しました。")
        st.subheader("v1.0.0")
        st.markdown("- **初期リリース**")

    if st.session_state.get('confirm_reset', False):
        st.warning("本当によろしいですか？この操作は取り消せません。")
        col1, col2 = st.columns(2)
        if col1.button("はい、リセットします", type="primary"):
            database.reset_all_history(); st.session_state.confirm_reset = False; st.success("学習履歴をリセットしました。"); st.rerun()
        if col2.button("キャンセル"):
            st.session_state.confirm_reset = False; st.rerun()

def render_admin_debug_page():
    st.title("管理者向け：デバッグ機能")
    if not st.session_state.get('raw_content'):
        st.error("問題ファイルがアップロードされていません。トップページに戻ってファイルをアップロードしてください。")
        if st.button("トップページに戻る"): st.session_state.page = 'start'; st.rerun()
        return
    st.header("1. パーサーデバッグ")
    if st.button("パーサーデバッグログを生成"):
        with st.spinner("パーサーをデバッグモードで実行中..."):
            _, debug_log = parser.parse_md_content(st.session_state.raw_content, debug=True)
            st.session_state.parser_debug_log = debug_log
        st.success("パーサーデバッグログが生成されました。")
    if st.session_state.get('parser_debug_log'):
        st.download_button("ログをダウンロード", "\n".join(st.session_state.parser_debug_log), "parser_debug_log.txt", "text/plain")
    st.header("2. UI描画デバッグ")
    if st.session_state.get('ui_debug_log'):
        st.download_button("UI描画デバッグログをダウンロード", "\n".join(st.session_state.ui_debug_log), "ui_debug_log.txt", "text/plain")
        with st.expander("UIログプレビュー"): st.code("\n".join(st.session_state.ui_debug_log))
    else: st.info("UIデバッグログはまだありません。")
    st.divider()
    st.header("問題判定チェック")
    questions = st.session_state.all_questions_from_file
    if questions:
        data = [{"問題ID": q['id'], "判定タイプ": "判定できませんでした" if q.get('question_type') == 'unknown' else q.get('question_type'), "質問文 (先頭)": q['question'].replace('\n', ' ')[:100] + "..."} for q in sorted(questions, key=lambda x: x['id'])]
        st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    if st.button("トップページに戻る"): st.session_state.page = 'start'; st.rerun()

def render_test_page():
    q = st.session_state.questions[st.session_state.current_q_index]
    q_id = q['id']
    q_type = q.get('question_type', 'single')
    st.title(f"問題 {st.session_state.current_q_index + 1}/{len(st.session_state.questions)}")
    st.progress((st.session_state.current_q_index + 1) / len(st.session_state.questions))
    st.markdown(f"**Q{q_id}:**"); st.markdown(q['question']); st.markdown("---")
    if q_id not in st.session_state.user_answers:
        st.session_state.user_answers[q_id] = {} if q_type in ['order', 'match'] else []
    current_answers = st.session_state.user_answers[q_id].copy()
    if q_type == 'order':
        st.write("**提示された手順:**"); [st.write(f"- {opt}") for opt in q['options']]
        st.divider(); st.write("**回答欄:**")
        new_answers = {}
        for i in range(1, len(q['correct_answers']) + 1):
            step_key = str(i)
            current_selection = current_answers.get(step_key)
            other_selected_values = set(current_answers.values()) - {current_selection}
            available_options = [opt for opt in q['options'] if opt not in other_selected_values]
            choices = ["--選択してください--"] + available_options
            try: index = choices.index(current_selection) if current_selection else 0
            except ValueError: index = 0
            selection = st.selectbox(f"**ステップ {i}** に配置する手順:", choices, key=f"selectbox_{q_id}_{step_key}", index=index)
            if selection != "--選択してください--": new_answers[step_key] = selection
        if new_answers != current_answers: st.session_state.user_answers[q_id] = new_answers; st.rerun()
    elif q_type == 'match':
        tasks, procedures = q['options']['tasks'], q['options']['procedures']
        proc_text_to_key = {v: k for k, v in procedures.items()}
        st.markdown("**タスク (Tasks)**"); [st.markdown(f"- **{k}.** {t}") for k, t in tasks.items()]
        st.markdown("**手順/ツール (Procedures/Tools)**"); [st.markdown(f"- **{k}.** {t}") for k, t in procedures.items()]
        st.divider(); st.markdown("**回答欄:**")
        new_answers = {}
        for task_key, task_text in tasks.items():
            st.markdown(f"**タスク {task_key}:** {task_text}")
            current_selection_key = current_answers.get(task_key)
            current_selection_text = procedures.get(current_selection_key)
            other_selected_keys = set(current_answers.values()) - {current_selection_key}
            other_selected_texts = {procedures[key] for key in other_selected_keys if key in procedures}
            available_options = [text for text in list(procedures.values()) if text not in other_selected_texts]
            choices = ["--選択してください--"] + available_options
            try: index = choices.index(current_selection_text) if current_selection_text else 0
            except ValueError: index = 0
            selection_text = st.selectbox("対応する手順/ツールを選択:", options=choices, key=f"selectbox_{q_id}_{task_key}", index=index)
            if selection_text != "--選択してください--": new_answers[task_key] = proc_text_to_key.get(selection_text)
        if new_answers != current_answers: st.session_state.user_answers[q_id] = new_answers; st.rerun()
    else:
        user_answer_list = current_answers
        if q_type == 'multiple':
            st.session_state.user_answers[q_id] = [key for key, text in q['options'].items() if st.checkbox(f"{key}: {text}", key=f"q_{q_id}_{key}", value=(key in user_answer_list))]
        else:
            option_keys = list(q['options'].keys())
            try: index = option_keys.index(user_answer_list[0]) if user_answer_list else None
            except (ValueError, IndexError): index = None
            selected_key = st.radio("回答:", options=option_keys, format_func=lambda k: f"{k}: {q['options'][k]}", key=f"q_{q_id}_single", index=index)
            st.session_state.user_answers[q_id] = [selected_key] if selected_key else []
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    if col1.button("前の問題へ", disabled=(st.session_state.current_q_index == 0)): st.session_state.current_q_index -= 1; st.rerun()
    if col2.button("次の問題へ", disabled=(st.session_state.current_q_index >= len(st.session_state.questions) - 1)): st.session_state.current_q_index += 1; st.rerun()
    if col3.button("回答一覧へ", type="secondary"): st.session_state.page = 'summary'; st.rerun()

def render_summary_page():
    st.title("回答一覧")
    col1, col2 = st.columns(2)
    if col1.button("テストを続ける", use_container_width=True): st.session_state.page = 'test'; st.rerun()
    if col2.button("テストを終了して採点", type="primary", use_container_width=True): st.session_state.page = 'result'; st.rerun()
    st.divider()
    for i, q in enumerate(st.session_state.questions):
        user_ans = st.session_state.user_answers.get(q['id'])
        with st.expander(f"問題 {i+1} (ID: {q['id']}) - {q.get('question_type', 'N/A')}"):
            st.markdown(f"**問題:**\n{q['question']}"); st.markdown("---")
            if user_ans:
                ans_str = ""
                if isinstance(user_ans, list): ans_str = ', '.join(user_ans)
                elif isinstance(user_ans, dict): ans_str = ", ".join([f"{k}:{v}" for k, v in sorted(user_ans.items())])
                st.write(f"**あなたの回答:** {ans_str}")
            else:
                st.warning("この問題はまだ回答されていません。")
                if st.button("この問題を解く", key=f"jump_{q['id']}"): st.session_state.current_q_index = i; st.session_state.page = 'test'; st.rerun()

def render_result_page():
    st.title("テスト結果")
    score, details = calculate_score()
    total = len(st.session_state.questions)
    correct_rate = score / total if total > 0 else 0
    if total > 0: database.save_test_result(score, total, correct_rate, details)
    st.header("成績"); col1, col2 = st.columns(2); col1.metric("正解数", f"{score} / {total}"); col2.metric("正答率", f"{correct_rate:.1%}")
    st.divider();
    if st.button("トップページに戻る", type="primary"): reset_test_state()
    st.divider()
    st.header("問題ごとの詳細")
    for detail in details:
        result_icon = "✅ 正解" if detail['is_correct'] else "❌ 不正解"
        with st.expander(f"{result_icon} - Q{detail['id']} ({detail['question_type']})"):
            st.markdown(f"**問題:**\n{detail['question']}"); st.markdown("---")
            q_type = detail['question_type']
            if q_type == 'order':
                st.subheader("あなたの回答 vs 正解")
                data = [{"ステップ": str(i+1), "あなたの回答": detail['user_answer'].get(str(i+1), "*(未回答)*"), "正解": correct, "判定": "✅" if detail['user_answer'].get(str(i+1)) == correct else "❌"} for i, correct in enumerate(detail['correct_answer'])]
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            elif q_type == 'match':
                st.subheader("あなたの回答 vs 正解")
                tasks, procs = detail['options']['tasks'], detail['options']['procedures']
                data = [{"タスク": f"{tk}. {tasks.get(tk, '')}", "あなたの回答": f"{detail['user_answer'].get(tk, '未')}: {procs.get(detail['user_answer'].get(tk), '')}", "正解": f"{detail['correct_answer'].get(tk)}: {procs.get(detail['correct_answer'].get(tk), '')}", "判定": "✅" if detail['user_answer'].get(tk) == detail['correct_answer'].get(tk) else "❌"} for tk in sorted(tasks.keys())]
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.subheader("選択肢の正誤")
                for key, text in detail['options'].items():
                    is_correct_opt = key in detail['correct_answer']
                    is_user_choice = key in detail['user_answer']
                    if is_correct_opt and is_user_choice: st.success(f"✅ {key}: {text} (あなたの正解)")
                    elif is_correct_opt and not is_user_choice: st.info(f"⚪️ {key}: {text} (正解)")
                    elif not is_correct_opt and is_user_choice: st.error(f"❌ {key}: {text} (あなたの誤答)")
                    else: st.write(f"&nbsp;&nbsp;&nbsp;&nbsp; {key}: {text}", unsafe_allow_html=True)
            st.markdown("---"); st.subheader("解説"); st.info(detail['explanation'])
            q_id = detail['id']
            is_excluded = q_id in st.session_state.excluded_question_ids
            exclude_q = st.checkbox("この問題を理解したので、次回から除外する", value=is_excluded, key=f"exclude_{q_id}_result")
            if exclude_q and not is_excluded:
                st.session_state.excluded_question_ids.add(q_id); st.toast(f"Q{q_id}を除外しました。")
            elif not exclude_q and is_excluded:
                st.session_state.excluded_question_ids.remove(q_id); st.toast(f"Q{q_id}を再度対象に含めました。")

def render_study_page():
    q = st.session_state.questions[st.session_state.current_q_index]
    q_id = q['id']
    q_type = q.get('question_type', 'single')
    st.title(f"学習モード: 問題 {st.session_state.current_q_index + 1}/{len(st.session_state.questions)}")
    st.progress((st.session_state.current_q_index + 1) / len(st.session_state.questions))
    st.markdown(f"**Q{q_id}:**"); st.markdown(q['question']); st.markdown("---")
    st.subheader("正解")
    if q_type == 'order':
        [st.success(f"**ステップ {i+1}:** {step}") for i, step in enumerate(q['correct_answers'])]
    elif q_type == 'match':
        tasks, procs = q['options']['tasks'], q['options']['procedures']
        [st.success(f"**{tasks.get(tk, '')}** ->  **{pk}: {procs.get(pk, '')}**") for tk, pk in sorted(q['correct_answers'].items())]
    else:
        for key, text in q['options'].items():
            if key in q['correct_answers']: st.success(f"✅ {key}: {text} (正解)")
            else: st.write(f"&nbsp;&nbsp;&nbsp;&nbsp; {key}: {text}", unsafe_allow_html=True)
    st.markdown("---"); st.subheader("解説"); st.info(q['explanation'])
    st.markdown("---")
    is_excluded = q_id in st.session_state.excluded_question_ids
    exclude_q = st.checkbox("この問題を理解したので、次回から除外する", value=is_excluded, key=f"exclude_{q_id}_study")
    if exclude_q and not is_excluded:
        st.session_state.excluded_question_ids.add(q_id); st.toast(f"Q{q_id}を除外しました。")
    elif not exclude_q and is_excluded:
        st.session_state.excluded_question_ids.remove(q_id); st.toast(f"Q{q_id}を再度対象に含めました。")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    if col1.button("前の問題へ", disabled=(st.session_state.current_q_index == 0)): st.session_state.current_q_index -= 1; st.rerun()
    if col2.button("次の問題へ", disabled=(st.session_state.current_q_index >= len(st.session_state.questions) - 1)): st.session_state.current_q_index += 1; st.rerun()
    if col3.button("学習を終了", type="primary"): reset_test_state()

# --- メインのページルーティング ---
page = st.session_state.get('page', 'start')
if page == 'start': render_start_page()
elif page == 'test': render_test_page()
elif page == 'study': render_study_page()
elif page == 'summary': render_summary_page()
elif page == 'result': render_result_page()
elif page == 'admin_debug': render_admin_debug_page()
else: st.session_state.page = 'start'; st.rerun()