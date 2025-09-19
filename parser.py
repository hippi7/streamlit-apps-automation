# parser.py

import re
from typing import List, Dict, Any, Tuple

def parse_md_content(content: str, debug: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    マークダウンコンテンツを解析し、質問オブジェクトのリストとデバッグログを返す。
    問題文と選択肢の分離ロジックを強化し、安定性を向上させたバージョン。
    """
    problem_blocks = content.split('---')
    questions = []
    debug_log = []

    if debug:
        debug_log.append("--- PARSER DEBUG LOG START ---")
        debug_log.append(f"Found {len(problem_blocks)} blocks to process.")

    for i, block in enumerate(problem_blocks):
        block = block.strip()
        if not block:
            continue
            
        q_id = None
        log_prefix = f"[Block {i+1}]"

        try:
            no_match = re.search(r"### <a name=\"no(\d+)\"></a>\*\*NO\.(\d+)\*\*", block)
            if not no_match:
                if debug: debug_log.append(f"{log_prefix} SKIPPED: No question ID found.")
                continue
            q_id = int(no_match.group(1))
            log_prefix = f"[Block {i+1} | Q{q_id}]"

            if debug: debug_log.append(f"\n{log_prefix} Processing...")

            explanation_match = re.search(r"\*\*解説:\*\*\n([\s\S]*)", block, re.S)
            explanation = explanation_match.group(1).strip() if explanation_match else "解説はありません。"

            is_order = "正しい順序に並べてください" in block and "[提示された手順]" in block
            is_match = "一致させてください" in block

            if is_order:
                if debug: debug_log.append(f"{log_prefix} Keyword '正しい順序に並べてください' found. Parsing as 'order'.")
                question_text_match = re.search(r"### <a name=\"no\d+\"></a>\*\*NO\.\d+\*\* \n([\s\S]+?)(?=\n\n\*\*\[提示された手順\]\*\*)", block, re.S)
                question_text = question_text_match.group(1).strip() if question_text_match else f"NO.{q_id}"
                
                provided_steps_match = re.search(r"\*\*\[提示された手順\]\*\*\n([\s\S]+?)(?=\n\n\*\*正解:\*\*)", block, re.S)
                correct_order_match = re.search(r"\*\*正解:\*\*\n([\s\S]+?)(?=\n---|\Z)", block, re.S)
                if provided_steps_match and correct_order_match:
                    provided_steps = [s.strip('* ') for s in provided_steps_match.group(1).strip().split('\n')]
                    # ↓↓↓ この行で、strip() を strip(' *') に変更しています
                    correct_answers = [line.split(':', 1)[-1].strip(' *') for line in correct_order_match.group(1).strip().split('\n') if re.match(r"\d+\.\s+\*\*ステップ\d+:\*\*", line)]
                    # ↑↑↑ この行の後に、正しく改行が入っていることを確認してください
                    questions.append({'id': q_id, 'question_type': 'order', 'question': question_text, 'options': provided_steps, 'correct_answers': correct_answers, 'explanation': explanation})
                    if debug: debug_log.append(f"{log_prefix} SUCCESS: Parsed as 'order'.")
                else:
                    if debug: debug_log.append(f"{log_prefix} FAILED: 'order' components not found. Classifying as 'unknown'.")
                    questions.append({'id': q_id, 'question_type': 'unknown', 'question': f"Q{q_id}: (順序問題の解析に失敗)\n{question_text}", 'options': {}, 'correct_answers': [], 'explanation': explanation})
                continue
                
            if is_match:
                if debug: debug_log.append(f"{log_prefix} Keyword '一致させてください' found. Trying to parse as 'match'.")
                
                tasks_header_pattern = r"\*\*(?:タスク \(Tasks\)|問題 \(Issues\))\*\*"
                procs_header_pattern = r"\*\*(?:手順/ツール \(Procedures/Tools\)|トラブルシューティング手順 \(Troubleshooting Steps\))\*\*"
                
                tasks_match = re.search(f"{tasks_header_pattern}\n([\\s\\S]+?)(?=\\n\\n)", block, re.S)
                procedures_match = re.search(f"{procs_header_pattern}\n([\\s\\S]+?)(?=\\n\\n)", block, re.S)
                correct_match = re.search(r"\*\*正解:\*\*\n([\s\S]+?)(?=\n---|\Z)", block, re.S)

                question_text_match = re.search(r"### <a name=\"no\d+\"></a>\*\*NO\.\d+\*\* \n([\s\S]+?)(?=\n\n\*\*)", block, re.S)
                question_text = question_text_match.group(1).strip() if question_text_match else f"NO.{q_id}"
                
                if tasks_match and procedures_match and correct_match:
                    tasks = {m.group(1): m.group(2).strip() for line in tasks_match.group(1).strip().split('\n') if (m := re.match(r"\*\s*(\d+)\.\s*(.+)", line))}
                    procedures = {m.group(1): m.group(2).strip() for line in procedures_match.group(1).strip().split('\n') if (m := re.match(r"\*\s*([A-Z])\.\s*(.+)", line))}
                    correct_answers = {m.group(1): m.group(2) for line in correct_match.group(1).strip().split('\n') if (m := re.search(r"\*\s*\*\*(\d+)\..*?->\s*\*\*([A-Z])\.", line))}
                    
                    if tasks and procedures and correct_answers:
                        questions.append({'id': q_id, 'question_type': 'match', 'question': question_text, 'options': {'tasks': tasks, 'procedures': procedures}, 'correct_answers': correct_answers, 'explanation': explanation})
                        if debug: debug_log.append(f"{log_prefix} SUCCESS: Parsed as 'match'.")
                        continue
                    else:
                        if debug: debug_log.append(f"{log_prefix} FAILED: 'match' inner components missing. Fallback.")
                else:
                     if debug: debug_log.append(f"{log_prefix} FAILED: 'match' structural components not found. Fallback.")
            
            main_content_match = re.search(r"### <a name=\"no\d+\"></a>\*\*NO\.\d+\*\*([\s\S]+?)\*\*正解:", block, re.S)
            if not main_content_match:
                if debug: debug_log.append(f"{log_prefix} FAILED: Main content area not found. Marking as 'unknown'.")
                questions.append({'id': q_id, 'question_type': 'unknown', 'question': f"Q{q_id}: (問題本文の解析に失敗)\n{block[:200]}...", 'options': {}, 'correct_answers': [], 'explanation': explanation})
                continue
            
            main_content = main_content_match.group(1).strip()
            
            lines = main_content.split('\n')
            first_option_index = -1
            for idx, line in enumerate(lines):
                if re.match(r"^[A-Z]\.", line.strip()):
                    first_option_index = idx
                    break
            
            if first_option_index != -1:
                question_text = "\n".join(lines[:first_option_index]).strip()
                option_lines = lines[first_option_index:]
                options = {m.group(1): m.group(2).strip() for line in option_lines if (m := re.match(r"^\s*([A-Z])\.(.*)", line.strip()))}
            else:
                question_text = main_content
                options = {}
            
            correct_answer_match = re.search(r"\*\*正解:\s*([A-Z, ]+)\*\*", block, re.IGNORECASE)

            if question_text and options and correct_answer_match:
                if debug: debug_log.append(f"{log_prefix} Basic components found. Parsing as 'single/multiple'.")
                correct_answers = sorted([ans.strip() for ans in correct_answer_match.group(1).split(',')])
                is_multiple = len(correct_answers) > 1 or re.search(r'（\d+つ選択）', question_text)
                q_type = 'multiple' if is_multiple else 'single'
                questions.append({'id': q_id, 'question_type': q_type, 'question': question_text, 'options': options, 'correct_answers': correct_answers, 'explanation': explanation})
                if debug: debug_log.append(f"{log_prefix} SUCCESS: Parsed as '{q_type}'.")
            else:
                if debug:
                    debug_log.append(f"{log_prefix} FAILED: Could not classify. Marking as 'unknown'.")
                    debug_log.append(f"{log_prefix}   - Got question_text? {'Yes' if question_text else 'No'}")
                    debug_log.append(f"{log_prefix}   - Got options? {'Yes' if options else 'No'}")
                    debug_log.append(f"{log_prefix}   - Got correct_answer_match? {'Yes' if correct_answer_match else 'No'}")
                questions.append({'id': q_id, 'question_type': 'unknown', 'question': f"Q{q_id}: (この問題は解析できませんでした)\n{block[:200]}...", 'options': {}, 'correct_answers': [], 'explanation': explanation})

        except Exception as e:
            if debug: debug_log.append(f"{log_prefix} FATAL ERROR: {e}. Marking as 'unknown'.")
            questions.append({'id': q_id if q_id else 9999, 'question_type': 'unknown', 'question': f"Q{q_id if q_id else '??'}: (解析中に致命的なエラー)\n{block[:200]}...", 'options': {}, 'correct_answers': [], 'explanation': str(e)})
            continue
    
    if debug: debug_log.append("\n--- PARSER DEBUG LOG END ---")
    return questions, debug_log