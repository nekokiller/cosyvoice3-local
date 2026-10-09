# cosyvoice3-local

本機 **CosyVoice3** 語音合成服務的自訂部分備份（私人 repo）。

官方專案（[FunAudioLLM/CosyVoice](https://github.com/FunAudioLLM/CosyVoice)）與模型體積龐大且公開可得，**不在此 repo 內**；這裡只放自己寫的服務程式、啟動設定與音色檔。

## 內容

| 檔案 | 說明 |
|---|---|
| `cosyvoice3_server.py` | 常駐 HTTP TTS 服務（Flask）。模型只在啟動時載入一次 |
| `build_voice_library.py` | 掃描 `audios/<音色名>/<逐字稿>.wav`，萃取 speaker embedding 存成 `audios_pt/<音色名>.pt` |
| `run_cosyvoice3.sh` | 啟動腳本（由 launchd 透過 bash 呼叫，以取得磁碟存取權限） |
| `launchd/com.nekokiller.cosyvoice.plist` | LaunchAgent 設定（開機常駐、`KeepAlive`，埠 8765） |
| `audios_pt/*.pt` | 17 個音色檔（音色名＝檔名） |
| `environment.yml` | conda 環境 `cosyvoice3`（Python 3.10、torch 2.3.1）匯出 |

> 原始參考音檔 `audios/` **未納入**（內含動畫、影視等作品片段，有版權疑慮）。已建好的 `.pt` 足以直接合成；若要新增音色，才需要自備音檔重新執行 `build_voice_library.py`。

## 服務介面

監聽 `127.0.0.1:8765`（僅本機）。

| 方法 | 路徑 | 說明 |
|---|---|---|
| `POST` | `/tts?voice=<音色名>` | body 為要唸的文字（UTF-8），回傳 `audio/wav`（24000 Hz） |
| `GET` | `/tts?text=...&voice=<音色名>` | 同上 |
| `GET` | `/health` | 服務狀態 |

不帶 `voice` 時，使用預設的 zero-shot 參考音。單執行緒，一次只處理一個請求；合成約 2.7 秒的語音需 10 秒左右。

環境變數：`COSYVOICE3_DIR`（官方專案根目錄）、`COSYVOICE3_PROMPT_WAV`、`COSYVOICE3_PROMPT_TEXT`、`COSYVOICE3_MODE`（`zero_shot`／`instruct2`）、`COSYVOICE3_INSTRUCT`、`COSYVOICE_PORT`。

## 重建環境（換機器或重灌時）

1. 取得官方專案，放在外接碟（或自訂路徑）：
   ```bash
   git clone https://github.com/FunAudioLLM/CosyVoice.git /Volumes/AcasisRaid2TB/CosyVoice3
   git -C /Volumes/AcasisRaid2TB/CosyVoice3 checkout 074ca6d   # 備份當時的版本
   git -C /Volumes/AcasisRaid2TB/CosyVoice3 submodule update --init --recursive
   ```
2. 依官方 README 下載模型 **Fun-CosyVoice3-0.5B** 到 `pretrained_models/Fun-CosyVoice3-0.5B`（約 9 GB）。
3. 建立 conda 環境：
   ```bash
   conda env create -f environment.yml
   ```
4. 放回本 repo 的檔案：
   ```bash
   cp cosyvoice3_server.py build_voice_library.py ~/ ; cp run_cosyvoice3.sh ~/ 
   cp build_voice_library.py /Volumes/AcasisRaid2TB/CosyVoice3/
   cp audios_pt/*.pt /Volumes/AcasisRaid2TB/CosyVoice3/audios_pt/   # 需先建立 audios_pt 目錄
   ```
5. 安裝常駐服務（plist 內有寫死的路徑與使用者名稱，視情況修改）：
   ```bash
   cp launchd/com.nekokiller.cosyvoice.plist ~/Library/LaunchAgents/
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nekokiller.cosyvoice.plist
   curl http://127.0.0.1:8765/health
   ```

## 注意

- 模型與音色目錄在外接碟 `/Volumes/AcasisRaid2TB`，**碟未掛載時服務無法運作**。
- 本機的 [smart-voice-clock](https://github.com/nekokiller/smart-voice-clock) 整點報時會呼叫此服務，並在失敗時自動退回 macOS `say`。
- 備份時的官方專案版本：`074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc`。
