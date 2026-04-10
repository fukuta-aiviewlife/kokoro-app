import sys

def init_terminal():
    """ターミナルの日本語表示崩れを防ぐ設定"""
    if sys.platform != 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

def ask_target_columns(df):
    """ユーザーに読み上げたい列を選択させる"""
    print("\n読み上げる『列』の組み合わせを選択してください:")
    for i, col in enumerate(df.columns):
        print(f"{i+1}: {col}")
    
    while True:
        col_input = input("出力したい列番号をカンマ区切りで入力（Enterのみで全列出力 / 例: 4,5）> ").strip()
        if not col_input:
            print("➔ 処理対象: すべての列")
            return df.columns.tolist()
            
        tmp_cols = []
        valid = True
        try:
            for part in col_input.split(','):
                part = part.strip()
                if not part: continue
                idx = int(part) - 1
                if 0 <= idx < len(df.columns):
                    tmp_cols.append(df.columns[idx])
                else:
                    valid = False
        except:
            valid = False
            
        if valid and tmp_cols:
            print(f"➔ 処理対象: {', '.join(tmp_cols)}")
            return tmp_cols
        else:
            print("入力形式が正しくありません。リストにある番号をカンマ区切りで入力してください。")

def ask_target_rows(df):
    """ユーザーに処理する行を選択させる"""
    print("\n出力する『行』を選択してください:")
    print("1: すべての行を出力する")
    print("2: 特定の行（一部）のみを出力する")
    while True:
        row_mode = input("選択 (1 または 2) > ").strip()
        if row_mode in ['1', '2']:
            break
        print("1 か 2 を半角で入力してください。")

    if row_mode == '1':
        return list(range(len(df)))
        
    while True:
        print(f"\n出力したい行番号（データ行の 1 ～ {len(df)}）を入力してください。")
        print("※ カンマ区切り（例: 1,3,5）やハイフンでの範囲指定（例: 2-5）が可能です。")
        target_input = input("行番号を入力 > ").strip()
        
        tmp_indices = set()
        try:
            for part in target_input.split(','):
                part = part.strip()
                if not part: continue
                if '-' in part:
                    start_str, end_str = part.split('-')
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    for i in range(start, end + 1):
                        tmp_indices.add(i - 1)
                else:
                    tmp_indices.add(int(part) - 1)
            
            target_indices = sorted([i for i in tmp_indices if 0 <= i < len(df)])
            
            if target_indices:
                print(f"➔ 処理対象: {[i+1 for i in target_indices]} 行目")
                return target_indices
            else:
                print(f"有効な行番号が見つかりませんでした。1～{len(df)} の間で入力してください。")
        except Exception:
            print("入力形式が正しくありません。数字、カンマ、ハイフンのみを使用してください。")

def ask_output_mode():
    """WAVファイルの結合か分割かを選択させる"""
    print("\n出力フォーマットを選択してください:")
    print("1: まとめて『1つのWAVファイル』に出力する")
    print("2: 各行ごとに『別々のWAVファイル（ファイル名自動生成）』に分割する")
    while True:
        output_mode = input("選択 (1 または 2) > ").strip()
        if output_mode in ['1', '2']:
            return output_mode
        print("1 か 2 を半角で入力してください。")
