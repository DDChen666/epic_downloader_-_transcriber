#!/bin/bash

# Epic Downloader & Transcriber - 環境變數設置腳本
# 用於快速配置 Gemini API 環境變數

echo "🎵 Epic Downloader & Transcriber - 環境變數設置"
echo "=================================================="

# 檢查 .env 文件是否存在
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件"
    echo "請先從範本創建 .env 文件："
    echo "  cp .env.example .env"
    exit 1
fi

echo "📄 當前 .env 文件內容："
echo "----------------------------------------"
cat .env
echo "----------------------------------------"

# 檢查是否已經設置了有效的 API 金鑰
if grep -q "your_gemini_api_key_here" .env; then
    echo ""
    echo "⚠️  檢測到您還沒有設置真實的 API 金鑰"
    echo ""
    echo "請按以下步驟操作："
    echo "1. 訪問 https://aistudio.google.com/"
    echo "2. 創建或獲取您的 Gemini API 金鑰"
    echo "3. 編輯 .env 文件，將 'your_gemini_api_key_here' 替換為您的真實金鑰"
    echo ""
    echo "或者，如果您想現在就設置，可以輸入您的 API 金鑰："
    read -p "輸入您的 Gemini API 金鑰 (留空則跳過): " api_key

    if [ ! -z "$api_key" ]; then
        # 使用 sed 替換 API 金鑰
        sed -i.bak "s/your_gemini_api_key_here/$api_key/" .env
        rm .env.bak 2>/dev/null
        echo ""
        echo "✅ 已更新 .env 文件！"
        echo "📄 新的 .env 文件內容："
        echo "----------------------------------------"
        cat .env
        echo "----------------------------------------"
    fi
else
    echo ""
    echo "✅ 您的 .env 文件似乎已經配置好了！"
fi

echo ""
echo "🔍 測試環境變數配置："
echo "----------------------------------------"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if api_key and api_key != 'your_gemini_api_key_here':
    print('✅ GEMINI_API_KEY 已設置')
    print('   金鑰長度:', len(api_key))
    print('   金鑰前綴:', api_key[:20] + '...' if len(api_key) > 20 else api_key)
else:
    print('❌ GEMINI_API_KEY 未設置或使用預設值')
"

echo ""
echo "🎉 設置完成！"
echo ""
echo "現在您可以運行以下命令："
echo "  python gemini_transcribe.py    # 使用 Gemini 轉錄器"
echo "  python whisper_transcrbe.py    # 使用 Whisper 轉錄器"
echo "  python media_downloader.py     # 下載媒體文件"
