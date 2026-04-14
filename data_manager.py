import pandas as pd
import os

def load_csv(filepath):
    """CSVファイルを読み込む"""
    if not os.path.exists(filepath):
        return None
    try:
        return pd.read_csv(filepath, encoding='utf-8-sig', header=0)
    except:
        return pd.read_csv(filepath, encoding='shift_jis', header=0)

def extract_target_data(df, target_indices, target_cols):
    """対象の行と列を抽出し、自然な文章（助詞付き）を作成して返す"""
    processing_data = []
    total = len(target_indices)
    
    # 女性ボイス4種のマッピング設定
    voice_map = {
        "女性1": "jf_alpha",
        "女性2": "jf_gongitsune",
        "女性3": "jf_nezumi",
        "女性4": "jf_tebukuro"
    }
    
    for i, index in enumerate(target_indices):
        row = df.iloc[index]
        text_parts = []     # 生のデータ（ファイル名や画面表示用）
        reading_parts = []  # 音声化するデータ（助詞付き）
        
        # 特殊チェック1：対象の行の「動作」列に文字が入力されているか（全列から探す）
        has_action = False
        action_col = next((c for c in df.columns if c == "動作"), None)
        if action_col:
            action_item = row[action_col]
            if not pd.isna(action_item) and str(action_item).strip():
                has_action = True
                
        # 特殊チェック2：行ごとの「スピード」を取得（速さ・速度・話速どれでもOK）
        row_speed = 1.1
        speed_col = None
        for name in ["速さ", "速度", "話速"]:
            if name in df.columns:
                speed_col = name
                break
                
        if speed_col and not pd.isna(row[speed_col]):
            try:
                row_speed = float(row[speed_col])
            except ValueError:
                pass
                
        # 特殊チェック3：行ごとの「ボイス」を取得
        row_voice = 'jf_gongitsune'  # 空白だった場合のデフォルト（女性2）
        if "ボイス" in df.columns and not pd.isna(row["ボイス"]):
            val = str(row["ボイス"]).strip()
            if val:
                row_voice = voice_map.get(val, val)
                
        # 特殊チェック4：行ごとの「回数」を取得
        repeat_count = 1  # 空白だった場合のデフォルトは1回
        if "回数" in df.columns and not pd.isna(row["回数"]):
            try:
                val_float = float(row["回数"])
                if val_float >= 1:
                    repeat_count = int(val_float)
            except ValueError:
                pass

        for col in target_cols:
            # ★ 修正ポイント：「ボイス」「速さ」「回数」などの列はシステム設定値なので読み上げをスキップする
            if col in ["ボイス", "速さ", "速度", "話速", "回数"]:
                continue

            item = row[col]
            if pd.isna(item): continue
            val = str(item).strip()
            if val:
                text_parts.append(val)
                
                # 列名に応じて、自動的に「てにをは」を調整する
                if col in ["ベッド名"]:
                    reading_parts.append(f"{val}の")
                elif col in ["名前"]:
                    suffix = "が" if has_action else ""
                    if val.endswith("様") or val.endswith("さま"):
                        reading_parts.append(f"{val}{suffix}")
                    else:
                        reading_parts.append(f"{val}さま{suffix}")
                elif col in ["ルーム", "ステーション名", "動作"]:
                    reading_parts.append(f"{val}")
                else:
                    reading_parts.append(val)

        processing_data.append({
            'row_index': index,
            'current_count': i + 1,
            'total_count': total,
            'text_parts': text_parts,         
            'reading_parts': reading_parts,   
            'voice': row_voice,               
            'speed': row_speed,
            'repeat_count': repeat_count
        })
        
    return processing_data
