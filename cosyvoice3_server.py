#!/usr/bin/env python
"""CosyVoice3 常駐 HTTP TTS 服務（給 Hermes command provider 用）
模型只在啟動時載入一次。
  POST /tts  body=要唸的文字(UTF-8)，回傳 audio/wav (24000Hz)
  GET  /tts?text=..
  GET  /health

環境變數：
  COSYVOICE3_DIR       專案根目錄（預設 /Volumes/AcasisRaid2TB/CosyVoice3）
  COSYVOICE3_PROMPT_WAV  參考音頻路徑（預設 asset/zero_shot_prompt.wav）
  COSYVOICE3_PROMPT_TEXT 參考音頻的文字轉寫（CosyVoice3 格式，需含 <|endofprompt|>）
  COSYVOICE3_MODE      zero_shot 或 instruct2（預設 zero_shot）
  COSYVOICE3_INSTRUCT  instruct2 模式的指令文字（需含 <|endofprompt|>）
  COSYVOICE_PORT       監聽埠（預設 8765）
"""
import io, os, sys, warnings
import torch, torchaudio
from flask import Flask, request, Response, jsonify

warnings.filterwarnings('ignore')

COSYVOICE3_DIR = os.environ.get(
    "COSYVOICE3_DIR",
    "/Volumes/AcasisRaid2TB/CosyVoice3"
)
PROMPT_WAV = os.environ.get(
    "COSYVOICE3_PROMPT_WAV",
    os.path.join(COSYVOICE3_DIR, "asset/zero_shot_prompt.wav")
)
# CosyVoice3 格式：system prompt + <|endofprompt|> + 參考音頻逐字稿
PROMPT_TEXT = os.environ.get(
    "COSYVOICE3_PROMPT_TEXT",
    "You are a helpful assistant.<|endofprompt|>希望你以后能够做的比我还好呦。"
)
INSTRUCT_TEXT = os.environ.get(
    "COSYVOICE3_INSTRUCT",
    "You are a helpful assistant. 請用自然親切的語調說話。<|endofprompt|>"
)
MODE = os.environ.get("COSYVOICE3_MODE", "zero_shot")  # zero_shot | instruct2
PORT = int(os.environ.get("COSYVOICE_PORT", "8765"))
VOICES_DIR = os.path.join(COSYVOICE3_DIR, "audios_pt")

sys.path.insert(0, COSYVOICE3_DIR)
sys.path.insert(0, os.path.join(COSYVOICE3_DIR, "third_party/Matcha-TTS"))
os.chdir(COSYVOICE3_DIR)

print("[cosyvoice3_server] 載入模型中...", flush=True)
from cosyvoice.cli.cosyvoice import AutoModel
model = AutoModel(model_dir="pretrained_models/Fun-CosyVoice3-0.5B")
print(
    f"[cosyvoice3_server] 模型就緒 sample_rate={model.sample_rate} "
    f"mode={MODE} prompt_wav={PROMPT_WAV}",
    flush=True
)

app = Flask(__name__)

# 已載入的音色名稱集合（避免重複讀 .pt）
_voice_cache: set = set()


def _load_voice(voice_name: str) -> None:
    if voice_name in _voice_cache:
        return
    pt_path = os.path.join(VOICES_DIR, f"{voice_name}.pt")
    if not os.path.exists(pt_path):
        raise FileNotFoundError(f"音色檔不存在：{pt_path}")
    payload = torch.load(pt_path, map_location="cpu", weights_only=False)
    model.frontend.spk2info[voice_name] = {
        k: v for k, v in payload.items() if not k.startswith("_")
    }
    _voice_cache.add(voice_name)
    print(f"[cosyvoice3_server] 音色載入：{voice_name}", flush=True)


def _generate(text: str, voice_name: str = "") -> bytes:
    if voice_name:
        _load_voice(voice_name)
        outputs = list(model.inference_zero_shot(
            tts_text=text,
            prompt_text="",
            prompt_wav="",
            zero_shot_spk_id=voice_name,
            stream=False,
        ))
    elif MODE == "instruct2":
        outputs = list(model.inference_instruct2(
            tts_text=text,
            instruct_text=INSTRUCT_TEXT,
            prompt_wav=PROMPT_WAV,
            stream=False,
        ))
    else:
        outputs = list(model.inference_zero_shot(
            tts_text=text,
            prompt_text=PROMPT_TEXT,
            prompt_wav=PROMPT_WAV,
            stream=False,
        ))
    combined = torch.cat([o["tts_speech"] for o in outputs], dim=1)
    buf = io.BytesIO()
    torchaudio.save(buf, combined, model.sample_rate, format="wav")
    buf.seek(0)
    return buf.read()


@app.route("/health")
def health():
    return jsonify(
        status="ok",
        version="cosyvoice3",
        mode=MODE,
        sample_rate=model.sample_rate,
        prompt_wav=PROMPT_WAV,
    )


@app.route("/tts", methods=["POST", "GET"])
def tts():
    text = (
        request.get_data(as_text=True)
        if request.method == "POST"
        else request.args.get("text", "")
    )
    text = (text or "").strip()
    if not text:
        return Response("empty text", status=400)
    voice_name = request.args.get("voice", "").strip()
    try:
        data = _generate(text, voice_name)
        return Response(data, mimetype="audio/wav")
    except FileNotFoundError as e:
        print(f"[cosyvoice3_server] voice not found: {e}", flush=True)
        return Response(str(e), status=404)
    except Exception as e:
        print(f"[cosyvoice3_server] error: {e}", flush=True)
        return Response(str(e), status=500)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, threaded=False)
