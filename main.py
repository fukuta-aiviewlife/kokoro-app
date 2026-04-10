import ui_manager
import data_manager
import audio_manager

CSV_FILE = 'kokoro_test.csv'

def main():
    # ターミナルの文字化け対策
    ui_manager.init_terminal()
    
    print("=== Kokoro 読み上げ一括生成システム ===")
    
    # 1. データの読み込み
    df = data_manager.load_csv(CSV_FILE)
    if df is None:
        print(f"エラー: {CSV_FILE} が見つかりません。")
        return
        
    # 2. ユーザーへ処理設定を質問 (対話形式)
    target_cols = ui_manager.ask_target_columns(df)
    target_indices = ui_manager.ask_target_rows(df)
    output_mode = ui_manager.ask_output_mode()
    
    # 3. 対象データのみを抽出して整理
    processing_data = data_manager.extract_target_data(df, target_indices, target_cols)
    
    # 4. 音声の生成と保存
    try:
        audio_manager.generate_and_save_audio(processing_data, output_mode)
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
