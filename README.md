# Epic Downloader & Transcriber 🎵

一個功能完整的Python程序套件，用於下載多種媒體格式、自動轉碼，以及使用AI進行音頻轉錄。

## ⚠️ 重要提醒：環境變數配置

在使用 Gemini 轉錄器之前，您需要配置環境變數：

### 方法1：使用設置腳本（最簡單）
```bash
# 運行互動式設置腳本
./setup_env.sh
```

### 方法2：手動創建 `.env` 文件
```bash
# 複製範本
cp .env.example .env

# 編輯 .env 文件，將 your_gemini_api_key_here 替換為您的真實 API 金鑰
GEMINI_API_KEY=您的真實API金鑰
```

### 方法3：設置系統環境變數
```bash
export GEMINI_API_KEY="您的真實API金鑰"
```

**詳細配置指南請參閱 `.env.readme.md` 文件**

## 功能特點

### 📥 媒體下載器 (Media Downloader)
- ✅ 支持多種媒體平台（YouTube, Apple Podcast, Spotify, SoundCloud等）
- ✅ 自動檢測媒體類型並分類下載
- ✅ 優先下載最高品質音頻
- ✅ 自動創建頻道/節目目錄結構
- ✅ 統一轉碼為 MP3 128kbps / 單聲道 / 16 kHz格式
- ✅ 自動清理原始文件
- ✅ 智能去重，避免重複下載
- ✅ 詳細的日誌記錄
- ✅ 錯誤處理和恢復機制

### 🎙️ AI 音頻轉錄器 (AI Audio Transcriber)

#### Whisper 轉錄器 (推薦)
- ✅ 使用 `mlx-community/whisper-large-v3-turbo` 模型（Apple Silicon 優化）
- ✅ 自動檢測語言（支持中文、英文、日文等多語言）
- ✅ 支持多種音頻格式（MP3, WAV, M4A, FLAC, AAC等）
- ✅ 批量處理整個下載目錄及其子目錄
- ✅ 智能跳過已轉錄文件，避免重複處理
- ✅ 轉錄結果保存為結構化的 txt 文件
- ✅ 包含時間戳、分段信息和完整文本

#### Gemini 轉錄器 (強大且免費)
- ✅ 使用 Google Gemini 2.5 Flash 模型
- ✅ 智能音頻分割：自動處理超過30分鐘的長音頻
- ✅ 並行處理分割後的音頻區塊，提高處理效率
- ✅ 按順序合併轉錄結果，保持時間戳連續性
- ✅ 支持多種音頻格式和完整的錯誤處理
- ✅ 需要設置 `GEMINI_API_KEY` 環境變數

## 系統要求

### Python 版本
- Python 3.8+

### 外部依賴
需要安裝以下命令行工具：

#### macOS (使用 Homebrew)
```bash
brew install yt-dlp ffmpeg
```

#### AI 轉錄依賴

**Whisper 轉錄器**:
```bash
pip install mlx-whisper
```
**注意**: mlx-whisper 需要 Apple Silicon (M1/M2/M3) Mac 電腦才能運行。如需在其他平台使用，請考慮其他 Whisper 實現。

**Gemini 轉錄器**:
```bash
pip install google-genai python-dotenv
```
需要設置環境變數:
```bash
export GEMINI_API_KEY="your_api_key_here"
```
或創建 `.env` 文件：
```
GEMINI_API_KEY=your_api_key_here
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip ffmpeg
pip3 install yt-dlp
```

#### Windows
1. 安裝 Python 3.8+ (https://python.org)
2. 下載 ffmpeg (https://ffmpeg.org/download.html) 並添加到 PATH
3. 安裝 yt-dlp:
   ```bash
   pip install yt-dlp
   ```

## 安裝步驟

1. **克隆或下載此項目**
2. **安裝依賴**：
   ```bash
   pip install -r requirements.txt
   ```
3. **安裝系統依賴**：
   - yt-dlp
   - ffmpeg

## 使用方法

### 1. 準備下載列表

編輯 `download_list.txt` 文件，每行一個媒體鏈接：

```
https://www.youtube.com/watch?v=VIDEO_ID
https://podcasts.apple.com/us/podcast/podcast-name/id123456789
https://open.spotify.com/episode/EPISODE_ID
https://soundcloud.com/user/track-name
```

### 2. 運行程序

```bash
python media_downloader.py
```

### 3. 查看結果

下載的檔案將按照以下結構組織：

```
下載資料夾/
├── YouTube頻道名稱/
│   ├── 影片標題_processed.mp3
│   ├── 影片標題_processed.txt  # AI 轉錄結果
│   └── 另一個影片_processed.mp3
├── Podcast名稱/
│   ├── 節目名稱_processed.mp3
│   ├── 節目名稱_processed.txt  # AI 轉錄結果
│   └── 另一集_processed.mp3
└── 其他媒體/
    └── ...
```

### 4. 運行 AI 音頻轉錄

下載音頻後，可以使用以下 AI 轉錄器將音頻轉換為文字：

#### 使用 Whisper 轉錄器（推薦）
```bash
# 轉錄所有下載的音頻文件
python whisper_transcrbe.py
```

#### 使用 Gemini 轉錄器
```bash
# 設置 API 金鑰
export GEMINI_API_KEY="your_api_key_here"

# 轉錄所有下載的音頻文件
python gemini_transcribe.py
```

#### 比較表

| 特性 | Whisper | Gemini |
|------|---------|--------|
| 平台要求 | Apple Silicon Mac | 全平台 |
| API 金鑰 | 不需要 | 需要 |
| 長音頻處理 | 不支持 | 自動分割 |
| 並行處理 | 不支持 | 支持 |
| 費用 | 免費 | 免費額度內 |
| 準確度 | 高 | 很高 |

## 支持的媒體平台

- **YouTube** - 視頻和播放列表
- **Apple Podcasts** - Podcast 節目
- **Spotify** - Podcast 和節目
- **SoundCloud** - 音頻和播放列表
- **Vimeo** - 視頻
- **Bilibili** - 視頻
- **Twitch** - 直播和視頻
- **通用媒體** - 其他支持的格式

## 音頻格式規格

所有下載的音頻都會被轉換為統一格式：
- **格式**: MP3
- **編碼**: libmp3lame
- **比特率**: 128 kbps
- **採樣率**: 16 kHz
- **聲道**: 單聲道 (Mono)

**為什麼選擇 MP3？**
- 相比 WAV 格式，大幅減小檔案大小（約 50-70% 節省）
- 保持良好的音質，適合語音內容
- 廣泛的兼容性

## AI 音頻轉錄器詳解

### 支持的音頻格式
- MP3, WAV, M4A, FLAC, AAC, OGG 等常見格式
- 自動跳過系統隱藏文件（以 `.` 開頭的文件）

### 轉錄結果格式

每個音頻文件會生成對應的 `.txt` 文件，包含：

```
音頻文件: 節目名稱_processed.mp3
檢測語言: zh
轉錄時間: 未知

完整文本:
[這裡是完整的轉錄文本...]

詳細分段:
[00:00:00 - 00:00:05] 你好，這是測試音頻...
[00:00:05 - 00:00:10] 這裡是第二段內容...
...
```

### AI 模型說明

使用 `mlx-community/whisper-large-v3-turbo` 模型：
- **優點**: 準確度高，支持多語言自動檢測
- **適用平台**: 主要適用於 Apple Silicon Mac
- **處理速度**: 在 M1/M2/M3 芯片上運行快速
- **語言支持**: 中文、英文、日文等多種語言

### 批量處理特點

- 自動掃描整個 `下載資料夾/` 及其子目錄
- 智能跳過已存在轉錄文件的音頻
- 支持中斷恢復（重新運行會繼續處理未完成的）
- 詳細的進度顯示和錯誤處理

## 日誌和調試

程序會生成詳細的日誌文件：
- `downloader.log` - 媒體下載日誌
- `whisper_transcrbe.log` - Whisper AI 轉錄日誌
- `gemini_transcribe.log` - Gemini AI 轉錄日誌

日誌包含：
- 下載/轉錄進度
- 錯誤信息和詳細錯誤追蹤
- 處理統計和性能指標
- API 調用記錄（Gemini）

## 配置選項

可以在 `MediaDownloader` 類中修改以下配置：

```python
# 音頻輸出格式
self.audio_format = {
    'format': 'wav',
    'codec': 'pcm_s16le',
    'sample_rate': 16000,  # 16 kHz
    'channels': 1,         # 單聲道
    'bit_depth': 16
}

# 自定義下載目錄
downloader = MediaDownloader(
    download_list_path="my_download_list.txt",
    download_dir="my_downloads"
)
```

## 故障排除

### 常見問題

**1. "yt-dlp: command not found"**
- 確保已正確安裝 yt-dlp
- 檢查 PATH 環境變數

**2. "ffmpeg: command not found"**
- 安裝 ffmpeg
- 確保在 PATH 中

**3. "Permission denied"**
- 確保對下載目錄有寫入權限
- 檢查文件是否被其他程序佔用

**4. 下載失敗**
- 檢查網址是否正確
- 某些內容可能需要登錄或有地理限制
- 查看 `downloader.log` 獲取詳細錯誤信息

**5. Gemini API 錯誤**
- 確保已設置正確的 `GEMINI_API_KEY`
- 檢查 API 金鑰是否有效且有足夠額度
- 查看 `gemini_transcribe.log` 獲取詳細錯誤信息

**6. Whisper 模型下載失敗**
- 確保網路連接正常
- mlx-whisper 僅適用於 Apple Silicon Mac
- 檢查磁盤空間是否足夠

### 獲取幫助

如果遇到問題：
1. 查看 `downloader.log` 日誌文件
2. 檢查控制台輸出
3. 確認所有依賴都已正確安裝

## 進階用法

### 自定義音頻品質

修改 `download_media` 方法中的格式選項：

```python
'--format', 'bestaudio[ext=m4a]/bestaudio/best',  # 優先 M4A 格式
```

### 添加新媒體平台支持

在 `media_patterns` 中添加新的URL模式：

```python
self.media_patterns['new_platform'] = [
    r'https?://newplatform\.com'
]
```

## 版本歷史

- **v3.0.0** - 🎉 重大更新！添加 Gemini AI 轉錄器，提供強大的長音頻處理能力
  - 新增 `gemini_transcribe.py` Gemini AI 轉錄器
  - 支持自動音頻分割處理超過30分鐘的長音頻
  - 實現並行處理提高轉錄效率
  - 按順序合併結果保持時間戳連續性
  - 支持全平台運行（不限Apple Silicon）
- **v2.0.0** - 🎉 大幅更新！添加 AI 音頻轉錄功能，支持使用 Whisper 模型自動轉錄音頻為文字
  - 新增 `whisper_transcrbe.py` AI 轉錄器
  - 改進音頻格式為 MP3（大幅減小檔案大小）
  - 支持批量處理和智能跳過已轉錄文件
  - 新增統一運行腳本 `run_downloader.sh`
- **v1.2.0** - 修復嵌套目錄問題，解決yt-dlp下載時創建多層目錄結構的問題
- **v1.1.0** - 修復Apple Podcast目錄整合問題，相同Podcast的所有節目現在會下載到統一目錄中
- **v1.0.0** - 初始版本，支持多平台下載和統一音頻轉碼

## 已知問題與修復

### v1.2.0 修復的嵌套目錄問題
**問題描述**: 在某些情況下，yt-dlp會創建嵌套的目錄結構，如：
```
下載資料夾/
└── 頻道名稱/
    └── 下載資料夾/
        └── 頻道名稱/
            └── 音頻文件.wav
```

**根本原因**: `download_media`方法中同時使用了絕對路徑的`--output`參數和`cwd`參數，導致yt-dlp在工作目錄內再次創建目錄結構。

**解決方案**: 修改`--output`參數使用相對路徑，避免與`cwd`參數衝突。

## 授權

此項目僅供個人使用，請遵守各媒體平台的服務條款。

## 免責聲明

此工具僅用於個人學習和研究目的。請確保您有權下載和使用相關內容。
