import os
import db_manager
import numpy as np
import soundfile as sf
import re
import time
import subprocess
import onnxruntime as rt
from kokoro_onnx import Kokoro
from text_processor import apply_rules
from misaki.ja import JAG2P

# デフォルト設定
MODEL_PATH = 'model_slim.onnx'
VOICES_PATH = 'voices.bin'
SAMPLE_RATE = 24000
OUTPUT_DIR = 'kokoro'

# AIが認識できない特殊な記号の置換テーブル（モジュールレベルで定義し、毎回生成しない）
PHONEME_MAP = {
    "ᶄ": "ky", "ᶀ": "by", "ᶁ": "dy", "ᶃ": "gy",
    "ᶆ": "my", "ᶈ": "py", "ᶉ": "ry", "ç": "hy",
    "ƫ": "ty", "g": "ɡ"
}

class AudioManagerONNX:
    def __init__(self):
        print(f"ONNXモデルをロード中... ({MODEL_PATH})")
        if not os.path.exists(MODEL_PATH) or not os.path.exists(VOICES_PATH):
            raise FileNotFoundError("モデルファイルまたは音声データが見つかりません。")

        # ONNX Runtimeの設定最適化 (8コア・一括推論用)
        options = rt.SessionOptions()
        options.intra_op_num_threads = 8 
        options.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL

        # 最適化したセッションからKokoroを初期化
        session = rt.InferenceSession(MODEL_PATH, sess_options=options, providers=["CPUExecutionProvider"])
        self.kokoro = Kokoro.from_session(session, VOICES_PATH)

        # 日本語解析器 (G2P) の初期化
        print("日本語解析エンジンをロード中...")
        self.g2p = JAG2P(version='pyopenjtalk')

        # 辞書の初期化
        db_manager.init_db()
        self.rules = db_manager.load_all_rules()

        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _to_phonemes(self, text):
        """日本語テキストをAIに渡せる音素文字列に変換する"""
        full, _ = self.g2p(text)
        raw = full[:len(full) // 2]
        clean = raw
        for old, new in PHONEME_MAP.items():
            clean = clean.replace(old, new)
        clean = clean.replace(" ", ",")
        if not clean.endswith("."):
            clean += "."
        return "j" + clean

    def generate_and_save(self, processing_data, output_mode):
        print("\n" + "="*60)
        print("【ONNXモデルによる音声生成を開始します】")
        print("="*60)

        total_computation_time = 0.0

        voice_map = {
            "jf_alpha": "jf_alpha",
            "jf_gongitsune": "jf_gongitsune",
            "jf_nezumi": "jf_nezumi",
            "jf_tebukuro": "jf_tebukuro",
            "jm_kumo": "jm_kumo"
        }

        combined_audio = []
        row_silence = np.zeros(int(SAMPLE_RATE * 2.0))

        for item in processing_data:
            start_time = time.time()

            index = item['row_index']
            text_parts = item['text_parts']
            reading_parts = item['reading_parts']
            row_voice_raw = item.get('voice', 'jf_gongitsune')
            row_voice = voice_map.get(row_voice_raw, "jf_gongitsune")
            row_speed = item.get('speed', 1.1)
            repeat_count = item.get('repeat_count', 1)

            # テキストの結合（助詞の後は読点を打たない）
            raw_reading = ""
            for p in reading_parts:
                raw_reading += p
                if p and p[-1] not in "のなどはを。、,.-":
                    raw_reading += "、"

            processed_body = apply_rules(raw_reading, self.rules)
            full_text = f"お知らせします。{processed_body}。"

            print(f"データ{index+1:2d}行目 (声: {row_voice}, 速さ: {row_speed}, 繰返: {repeat_count}回)")

            try:
                # 【一括推論】全文を1回でAIに渡す（最速）
                phonemes = self._to_phonemes(full_text)
                samples, _ = self.kokoro.create(
                    phonemes,
                    voice=row_voice,
                    speed=row_speed,
                    is_phonemes=True
                )
                samples = samples.squeeze()

                # リピートがある場合は本文のみ別途1回推論し、あとはコピーで賄う
                if repeat_count > 1:
                    gap_silence = np.zeros(int(SAMPLE_RATE * 1.0))
                    body_phonemes = self._to_phonemes(f"{processed_body}。")
                    body_samples, _ = self.kokoro.create(
                        body_phonemes,
                        voice=row_voice,
                        speed=row_speed,
                        is_phonemes=True
                    )
                    body_samples = body_samples.squeeze()
                    chunks = [samples]
                    for _ in range(repeat_count - 1):
                        chunks.append(gap_silence)
                        chunks.append(body_samples)
                    samples = np.concatenate(chunks)

                duration = time.time() - start_time
                total_computation_time += duration
                print(f"  ⏱ 変換時間: {duration:.2f} 秒")

                # 出力モードに応じた処理
                if output_mode == '1':  # 結合モード
                    combined_audio.append(samples)
                    combined_audio.append(row_silence)
                    print(f"  ➔ 結合キューに追加")
                else:  # 個別保存モード
                    safe_parts = [re.sub(r'[\\/:*?"<>|]', '', str(p)) for p in text_parts]
                    base_name = "_".join(safe_parts)[:80]
                    out_filename = os.path.join(OUTPUT_DIR, f"{index+1:02d}_{base_name}.wav")
                    sf.write(out_filename, samples, SAMPLE_RATE)
                    print(f"  ➔ 保存完了 [{out_filename}]")

                # スピーカー再生（プレビュー）
                try:
                    temp_wav = os.path.abspath(os.path.join(OUTPUT_DIR, f"temp_onnx_{index}.wav"))
                    sf.write(temp_wav, samples, SAMPLE_RATE)
                    win_path = subprocess.check_output(['wslpath', '-w', temp_wav]).decode().strip()
                    subprocess.run(['powershell.exe', '-c', f'(New-Object Media.SoundPlayer "{win_path}").PlaySync()'])
                    if os.path.exists(temp_wav):
                        os.remove(temp_wav)
                except:
                    pass

            except Exception as e:
                print(f"  ⚠️ 生成エラー ({index+1}行目): {e}")

        # 結合モードの最終書き出し
        if output_mode == '1' and combined_audio:
            final_file = os.path.join(OUTPUT_DIR, 'combined_onnx_results.wav')
            final_samples = np.concatenate(combined_audio)
            sf.write(final_file, final_samples, SAMPLE_RATE)
            print(f"\n✨ 結合完了！: {final_file}")

        print("\n" + "="*60)
        print(f"⏱ 総変換時間: {total_computation_time:.2f} 秒")
        print("="*60)
