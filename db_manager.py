import sqlite3
import json
import os

DB_PATH = "dictionary.db"
JSON_PATH = "rules.json"

def init_db():
    """データベースの初期化と必要に応じたデータのインポート"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # テーブル作成
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pronunciation_rules (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alphabet_map (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # DBが空の場合、rules.jsonからデータをインポートする
    cursor.execute("SELECT count(*) FROM pronunciation_rules")
    if cursor.fetchone()[0] == 0 and os.path.exists(JSON_PATH):
        print(f"Info: {JSON_PATH} からデータを移行中...")
        try:
            with open(JSON_PATH, 'r', encoding='utf-8-sig') as f:
                rules = json.load(f)
                
                # 辞書ルールのインポート
                for k, v in rules.get('pronunciation_rules', {}).items():
                    cursor.execute("INSERT OR REPLACE INTO pronunciation_rules (key, value) VALUES (?, ?)", (k, v))
                
                # アルファベットマップのインポート
                for k, v in rules.get('alphabet_map', {}).items():
                    cursor.execute("INSERT OR REPLACE INTO alphabet_map (key, value) VALUES (?, ?)", (k, v))
            
            conn.commit()
            print(f"Success: {JSON_PATH} からの移行が完了しました。")
        except Exception as e:
            print(f"Error while importing json: {e}")

    conn.close()

def load_all_rules():
    """DBからすべてのルールを読み込み、従来の辞書形式で返す"""
    rules = {
        "pronunciation_rules": {},
        "alphabet_map": {}
    }
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 辞書ルールの取得
    cursor.execute("SELECT key, value FROM pronunciation_rules")
    for k, v in cursor.fetchall():
        rules["pronunciation_rules"][k] = v
        
    # アルファベットマップの取得
    cursor.execute("SELECT key, value FROM alphabet_map")
    for k, v in cursor.fetchall():
        rules["alphabet_map"][k] = v
        
    conn.close()
    return rules

def add_or_update_rule(table_type, key, value):
    """ルールの追加または更新（将来の拡張用）
    table_type: 'dict' (辞書) または 'alpha' (アルファベット)
    """
    table_name = "pronunciation_rules" if table_type == "dict" else "alphabet_map"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"INSERT OR REPLACE INTO {table_name} (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
