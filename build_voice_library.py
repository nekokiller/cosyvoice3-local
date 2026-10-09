#!/usr/bin/env python3
"""
CosyVoice3 音色庫批次建立工具
掃描 audios/ 下所有音色資料夾，提取 Speaker Embedding 並存為 .pt 音色檔

目錄結構：
  audios/<音色名>/<逐字稿>.wav  →  audios_pt/<音色名>.pt

prompt_text = "You are a helpful assistant.<|endofprompt|>" + WAV檔名（無副檔名）
"""

import glob
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

COSYVOICE3_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIOS_DIR = os.path.join(COSYVOICE3_DIR, "audios")
OUTPUT_DIR = os.path.join(COSYVOICE3_DIR, "audios_pt")
PROMPT_PREFIX = "You are a helpful assistant.<|endofprompt|>"

sys.path.insert(0, COSYVOICE3_DIR)
sys.path.insert(0, os.path.join(COSYVOICE3_DIR, "third_party/Matcha-TTS"))
os.chdir(COSYVOICE3_DIR)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def main():
    log("載入 CosyVoice3 模型...")
    import torch
    from cosyvoice.cli.cosyvoice import AutoModel
    model = AutoModel(model_dir="pretrained_models/Fun-CosyVoice3-0.5B")
    log(f"模型就緒  sample_rate={model.sample_rate}Hz\n")

    voices = sorted([
        d for d in os.listdir(AUDIOS_DIR)
        if os.path.isdir(os.path.join(AUDIOS_DIR, d)) and not d.startswith(".")
    ])

    n_total = len(voices)
    n_gen = n_skip = n_err = 0

    log(f"找到 {n_total} 個音色資料夾\n")

    total_start = time.time()

    for voice_name in voices:
        output_pt = os.path.join(OUTPUT_DIR, f"{voice_name}.pt")

        if os.path.exists(output_pt):
            n_skip += 1
            continue

        voice_dir = os.path.join(AUDIOS_DIR, voice_name)
        wav_files = (
            glob.glob(os.path.join(voice_dir, "*.wav")) +
            glob.glob(os.path.join(voice_dir, "*.mp3"))
        )
        if not wav_files:
            log(f"[ERR]  {voice_name}  找不到音頻檔案")
            n_err += 1
            continue

        wav_path = wav_files[0]
        transcript = os.path.splitext(os.path.basename(wav_path))[0]
        prompt_text = PROMPT_PREFIX + transcript

        try:
            t0 = time.time()
            model.add_zero_shot_spk(prompt_text, wav_path, voice_name)

            payload = dict(model.frontend.spk2info[voice_name])
            payload = {
                k: v.cpu() if isinstance(v, torch.Tensor) else v
                for k, v in payload.items()
            }
            payload["_prompt_text"] = transcript
            payload["_source_wav"] = wav_path

            torch.save(payload, output_pt)

            del model.frontend.spk2info[voice_name]

            elapsed = time.time() - t0
            n_gen += 1
            log(f"[GEN]  {voice_name:<16}  →  {voice_name}.pt  耗時: {elapsed:.1f}s")

        except Exception as e:
            log(f"[ERR]  {voice_name:<16}  提取失敗: {e}")
            n_err += 1

    total_elapsed = time.time() - total_start
    m, s = int(total_elapsed // 60), int(total_elapsed % 60)
    log(f"\n[完成] 生成 {n_gen} 個  跳過 {n_skip} 個  失敗 {n_err} 個  總耗時: {m:02d}m{s:02d}s")

    return n_err


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
