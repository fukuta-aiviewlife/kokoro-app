import torch
from kokoro import KPipeline
from kokoro.model import KModel, KModelForONNX
import os

def export():
    # 1. Initialize pipeline to download/load model
    print("AIモデルをロード中...")
    # 既にダウンロード済みのパスを再利用するように、repo_idを指定
    pipeline = KPipeline(lang_code='j', repo_id='hexgrad/Kokoro-82M', device='cpu')
    
    # 【★注記】最新のPyTorchエクスポートでSDPAの形状チェックに引っかかるのを防ぐため、
    # 内部のAlbertモデルのAttention実装を標準的な 'eager' 方式に強制します。
    if hasattr(pipeline.model.bert.config, "_attn_implementation"):
        pipeline.model.bert.config._attn_implementation = "eager"
        print("Set attention implementation to 'eager' for compatibility.")

    kmodel = pipeline.model
    
    # 2. Wrap for ONNX
    onnx_model = KModelForONNX(kmodel)
    onnx_model.eval()
    
    # 3. Dummy inputs
    # input_ids: [1, seq_len] (例えば 50 文字程度のダミー)
    # ref_s: [1, 256]
    dummy_input_ids = torch.randint(0, 50, (1, 30), dtype=torch.long)
    dummy_ref_s = torch.randn(1, 256)
    
    # Define file name
    onnx_path = "kokoro-v1.0.onnx"
    
    print(f"ONNX形式へエクスポート中: {onnx_path} ... (この処理には数分かかる場合があります)")
    
    # Export
    try:
        # speedは定数として渡すか、テンソル化して動的入力にする
        # 今回は一旦 float 定数 1.0 として扱う
        torch.onnx.export(
            onnx_model,
            (dummy_input_ids, dummy_ref_s, 1.0),
            onnx_path,
            export_params=True,
            opset_version=17,
            do_constant_folding=True,
            input_names=['input_ids', 'ref_s', 'speed'],
            output_names=['audio', 'pred_dur'],
            dynamic_axes={
                'input_ids': {1: 'seq_len'},
                'audio': {0: 'audio_len'}
            }
        )
        print(f"Success: エクスポート完了！ -> {onnx_path}")
        
        # モデルサイズ確認
        size_mb = os.path.getsize(onnx_path) / (1024 * 1024)
        print(f"モデルサイズ: {size_mb:.2f} MB")
        
    except Exception as e:
        print(f"\n[エクスポート失敗]")
        print(f"原因: {e}")
        print("\n補足: Kokoroモデル内の一部の動的な処理(repeat_interleave等)が静的グラフエクスポートと競合している可能性があります。")

if __name__ == "__main__":
    export()
