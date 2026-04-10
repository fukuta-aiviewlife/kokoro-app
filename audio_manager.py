import os
import json
import numpy as np
import soundfile as sf
import re
import subprocess  # ★ 追加：Windowsの機能を呼び出すためのライブラリ
from kokoro import KPipeline
from text_processor import apply_rules

# 全体のデフォルト設定
VOICE = 'jf_gongitsune'
SPEED = 1.1
SAMPLE_RATE = 24000
OUTPUT_DIR = 'kokoro'

def generate_and_save_audio(processing_data, output_mode):
    """Kokoroエンジンで音声を生成し、WAVとして保存・再生する"""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    print(f"\nAIモデルをロード中... (CPUモード / デフォルトボイス: {VOICE})")
    
    pipeline = KPipeline(lang_code='j', repo_id='hexgrad/Kokoro-82M', device='cpu')
    
    with open('rules.json', 'r', encoding='utf-8-sig') as f:
        rules = json.load(f)
        
    combined_audio = []
    row_silence = np.zeros(int(SAMPLE_RATE * 2.0))

    print("\n" + "="*60)
    print("【音声生成を開始します】")
    print("="*60)

    for item in processing_data:
        index = item['row_index']
        text_parts = item['text_parts']
        reading_parts = item['reading_parts']
        
        row_voice = item.get('voice', VOICE)
        row_speed = item.get('speed', SPEED)
        repeat_count = item.get('repeat_count', 1)
        
        # 本文のベースを作成
        raw_reading = "、".join(reading_parts)
        processed_body = apply_rules(raw_reading, rules)
        
        # 1回目の完全な文章（以前と同じ自然なイントネーション）
        full_text = f"お知らせします。{processed_body}。"
        # 2回目以降繰り返すための文章（本文のみ）
        body_text = f"{processed_body}。"
        
        print(f"データ{index+1:2d}行目 [{item['current_count']}/{item['total_count']}] (声: {row_voice}, 速さ: {row_speed}, 繰返: {repeat_count}回)")
        print(f"  文章: {full_text}")
        
        # 1. まずは今まで通り、フルの文章で自然な音声を生成する
        full_generator = pipeline(full_text, voice=row_voice, speed=row_speed)
        full_chunks = [audio for _, (_, _, audio) in enumerate(full_generator)]
        single_audio = np.concatenate(full_chunks) if full_chunks else np.array([])
        
        # 2. リピート指定がある場合のみ、本文を追加生成してくっつける
        if repeat_count > 1 and len(single_audio) > 0:
            body_generator = pipeline(body_text, voice=row_voice, speed=row_speed)
            body_chunks = [audio for _, (_, _, audio) in enumerate(body_generator)]
            body_audio = np.concatenate(body_chunks) if body_chunks else np.array([])
            
            gap_silence = np.zeros(int(SAMPLE_RATE * 1.0)) # 1秒の空白データ
            repeated_chunks = [single_audio]
            
            # リピート回数分、本文の音声を足していく
            for _ in range(repeat_count - 1):
                repeated_chunks.append(gap_silence)
                repeated_chunks.append(body_audio)
                
            single_audio = np.concatenate(repeated_chunks)
            
        # 波形データが正常に作られていれば、再生および保存を行う
        if len(single_audio) > 0:
            # ★ WSL用の裏技：一時ファイルに保存してWindowsのPowerShell経由で強引に鳴らす
            print("  🎵 スピーカーで再生中 (Windowsバックグラウンド経由)...")
            temp_wav = os.path.abspath(os.path.join(OUTPUT_DIR, f"temp_play_{index}.wav"))
            sf.write(temp_wav, single_audio, SAMPLE_RATE)
            try:
                # WSLのLinuxパスをWindowsのパス（\\wsl.localhost\...）に変換
                win_path = subprocess.check_output(['wslpath', '-w', temp_wav]).decode().strip()
                # Windows標準のメディアプレイヤー機能を使ってPlaySync（終わるまで待機）で鳴らす
                subprocess.run(['powershell.exe', '-c', f'(New-Object Media.SoundPlayer "{win_path}").PlaySync()'])
            except Exception as e:
                print(f"  ⚠️ 再生エラー: {e}")
            
            # 再生が終わったら一時ファイルをこっそり削除しておく
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            
            # === 以下は通常の保存処理 ===
            if output_mode == '1':
                combined_audio.append(single_audio)
                combined_audio.append(row_silence)
                print(f"  ➔ 結合キューに追加完了")
            else:
                safe_parts = [re.sub(r'[\\/:*?"<>|]', '', str(p)) for p in text_parts]
                base_name = "_".join(safe_parts)[:80]
                out_filename = os.path.join(OUTPUT_DIR, f"{index+1:02d}_{base_name}.wav")
                
                sf.write(out_filename, single_audio, SAMPLE_RATE)
                print(f"  ➔ 保存完了 [{out_filename}]")

    if output_mode == '1' and combined_audio:
        output_file = os.path.join(OUTPUT_DIR, 'data_test_results.wav')
        final_output = np.concatenate(combined_audio)
        sf.write(output_file, final_output, SAMPLE_RATE)
        print(f"\n✨ 生成完了！ 1つのファイルに結合しました: {output_file}")
    elif output_mode == '2':
        print(f"\n✨ 生成完了！ ファイル名を自動生成して「{OUTPUT_DIR}」フォルダ内に分割書き出ししました。")

