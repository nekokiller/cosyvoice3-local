#!/bin/bash
# CosyVoice3 launcher（由 launchd 透過 bash 啟動，bash 有 TCC 完整磁碟存取）
exec /opt/homebrew/Caskroom/miniforge/base/envs/cosyvoice3/bin/python \
  /Users/nekokiller/cosyvoice3_server.py
