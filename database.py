# database.py

import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = 'quiz_history.db'

def init_db():
    """データベースとテーブルを初期化する"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_rate REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answer_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                question_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES test_sessions (id)
            )
        ''')
        conn.commit()

def save_test_result(score, total_questions, correct_rate, answer_details):
    """テスト結果と各問題の回答ログを保存する"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute(
            'INSERT INTO test_sessions (timestamp, score, total_questions, correct_rate) VALUES (?, ?, ?, ?)',
            (timestamp, score, total_questions, correct_rate)
        )
        session_id = cursor.lastrowid
        
        for detail in answer_details:
            cursor.execute(
                'INSERT INTO answer_logs (session_id, question_id, question_text, is_correct) VALUES (?, ?, ?, ?)',
                (session_id, detail['id'], detail['question'], 1 if detail['is_correct'] else 0)
            )
        conn.commit()

def get_all_test_results():
    """過去のすべてのテスト結果を取得する"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp, score, total_questions, correct_rate FROM test_sessions ORDER BY timestamp ASC')
        return cursor.fetchall()

def get_wrong_answer_ranking(limit=5):
    """間違えた問題のランキングを取得する（デフォルトで上位5件）"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT question_id, question_text, COUNT(*) as wrong_count
            FROM answer_logs
            WHERE is_correct = 0
            GROUP BY question_id, question_text
            ORDER BY wrong_count DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

def reset_all_history():
    """すべての学習履歴（両方のテーブル）を削除する"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM answer_logs')
        cursor.execute('DELETE FROM test_sessions')
        conn.commit()