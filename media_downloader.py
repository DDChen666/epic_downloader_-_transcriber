#!/usr/bin/env python3
"""
媒體下載器 - 支持多種媒體格式的下載和轉碼工具

功能：
- 讀取 download_list.txt 中的鏈接
- 自動檢測媒體類型 (YouTube, Apple Podcast, 等)
- 創建或讀取現有目錄結構
- 優先下載最高品質檔案
- 轉碼為 PCM 16-bit / 單聲道 / 16 kHz
- 清理原始檔案

作者: AI Assistant
版本: 1.0.0
"""

import os
import re
import json
import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, List
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('downloader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MediaDownloader:
    """媒體下載器主類"""

    def __init__(self, download_list_path: str = "download_list.txt",
                 download_dir: str = "下載資料夾"):
        """
        初始化下載器

        Args:
            download_list_path: 下載列表文件路徑
            download_dir: 下載目錄
        """
        self.download_list_path = Path(download_list_path)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

        # 支援的媒體類型及其URL模式
        self.media_patterns = {
            'youtube': [
                r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)',
                r'youtube\.com/watch\?v=',
                r'youtu\.be/',
                r'youtube\.com/playlist\?list='
            ],
            'apple_podcast': [
                r'(?:https?://)?podcasts\.apple\.com',
                r'podcasts\.apple\.com/.+/podcast/.+/id\d+'
            ],
            'spotify': [
                r'(?:https?://)?open\.spotify\.com',
                r'spotify\.com/episode/',
                r'spotify\.com/show/'
            ],
            'soundcloud': [
                r'(?:https?://)?(?:www\.)?soundcloud\.com'
            ],
            'vimeo': [
                r'(?:https?://)?(?:www\.)?vimeo\.com'
            ],
            'bilibili': [
                r'(?:https?://)?(?:www\.)?bilibili\.com'
            ],
            'twitch': [
                r'(?:https?://)?(?:www\.)?twitch\.tv'
            ]
        }

        # 音頻轉碼設定
        self.audio_format = {
            'format': 'mp3',
            'codec': 'libmp3lame',
            'sample_rate': 16000,
            'channels': 1,  # 單聲道
            'bitrate': 128000  # 128kbps，對於語音內容來說足夠
        }

    def detect_media_type(self, url: str) -> str:
        """
        檢測URL的媒體類型

        Args:
            url: 媒體URL

        Returns:
            媒體類型字符串
        """
        for media_type, patterns in self.media_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return media_type

        # 如果無法識別，返回通用類型
        return 'generic'

    def get_channel_name(self, url: str, media_type: str) -> str:
        """
        從URL中提取頻道/節目名稱

        Args:
            url: 媒體URL
            media_type: 媒體類型

        Returns:
            頻道/節目名稱
        """
        try:
            # 特殊處理 Apple Podcast - 從URL直接提取Podcast名稱和ID
            if media_type == 'apple_podcast':
                parsed = urlparse(url)
                path_parts = parsed.path.strip('/').split('/')

                # 查找 podcast 路徑段
                if 'podcast' in path_parts:
                    podcast_index = path_parts.index('podcast')
                    if podcast_index + 1 < len(path_parts):
                        podcast_slug = path_parts[podcast_index + 1]

                        # 從URL中提取Podcast ID
                        id_match = re.search(r'id(\d+)', url)
                        if id_match:
                            podcast_id = id_match.group(1)

                            # 解碼URL編碼的Podcast名稱
                            try:
                                from urllib.parse import unquote
                                decoded_name = unquote(podcast_slug)
                                # 清理名稱，移除多餘的資訊
                                clean_name = re.sub(r'-.*$', '', decoded_name).strip()
                                return f"{clean_name}_apple_podcast"
                            except:
                                # 如果解碼失敗，使用原始名稱
                                clean_name = re.sub(r'-.*$', '', podcast_slug).replace('-', ' ').strip()
                                return f"{clean_name}_apple_podcast"

            # 對於其他媒體類型，使用 yt-dlp 獲取元數據
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                '--quiet',
                url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )

            if result.returncode == 0:
                metadata = json.loads(result.stdout.strip())
                uploader = metadata.get('uploader', '')
                channel = metadata.get('channel', '')
                title = metadata.get('title', '')

                # 對於非Apple Podcast，使用頻道名稱
                if media_type != 'apple_podcast':
                    name = uploader or channel or title
                else:
                    # 如果yt-dlp返回了頻道資訊，也可以使用
                    name = channel or uploader or title

                # 清理名稱中的無效字符
                name = re.sub(r'[<>:"/\\|?*]', '', name)
                name = re.sub(r'\s+', ' ', name).strip()

                if name:
                    # 為不同媒體類型添加後綴
                    suffix = ""
                    if media_type == 'youtube':
                        suffix = "_youtube"
                    elif media_type == 'spotify':
                        suffix = "_spotify"
                    elif media_type == 'soundcloud':
                        suffix = "_soundcloud"

                    return f"{name}{suffix}"

            # 如果yt-dlp失敗，使用通用備用方案
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return f"{domain}_{hash(url) % 10000}"

        except Exception as e:
            logger.warning(f"獲取頻道名稱失敗: {e}")
            # 使用URL的hash作為備用名稱
            return f"unknown_channel_{hash(url) % 10000}"

    def create_download_directory(self, channel_name: str) -> Path:
        """
        創建或獲取下載目錄

        Args:
            channel_name: 頻道名稱

        Returns:
            下載目錄路徑
        """
        channel_dir = self.download_dir / channel_name
        channel_dir.mkdir(exist_ok=True)
        return channel_dir

    def get_expected_output_path(self, url: str, output_dir: Path) -> Optional[Path]:
        """
        獲取預期的輸出文件路徑（用於去重檢查）

        Args:
            url: 媒體URL
            output_dir: 輸出目錄

        Returns:
            預期的輸出文件路徑，如果無法獲取則返回None
        """
        try:
            # 使用 yt-dlp 獲取元數據來預測文件名
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-download',
                '--quiet',
                url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )

            if result.returncode == 0:
                metadata = json.loads(result.stdout.strip())
                title = metadata.get('title', '')

                if title:
                    # 清理文件名中的無效字符
                    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
                    clean_title = re.sub(r'\s+', ' ', clean_title).strip()

                    # 預測最終的輸出文件名：{title}_processed.mp3
                    expected_filename = f"{clean_title}_processed.mp3"
                    return output_dir / expected_filename

        except Exception as e:
            logger.warning(f"獲取預期輸出路徑失敗 {url}: {e}")

        return None

    def is_already_processed(self, url: str, output_dir: Path) -> bool:
        """
        檢查URL是否已經被處理過

        Args:
            url: 媒體URL
            output_dir: 輸出目錄

        Returns:
            如果已經處理過則返回True
        """
        try:
            # 首先嘗試精確匹配
            expected_path = self.get_expected_output_path(url, output_dir)
            if expected_path and expected_path.exists():
                logger.info(f"檢測到已處理的文件，跳過: {expected_path}")
                return True

            # 如果精確匹配失敗，嘗試寬鬆匹配：查找任何包含原始標題且以 _processed.mp3 結尾的文件
            if expected_path:
                base_title = expected_path.stem.replace('_processed', '')
                # 查找匹配的文件
                for file_path in output_dir.glob('*_processed.mp3'):
                    if base_title in file_path.stem:
                        logger.info(f"檢測到已處理的文件（寬鬆匹配），跳過: {file_path}")
                        return True

        except Exception as e:
            logger.warning(f"檢查處理狀態時發生錯誤 {url}: {e}")

        return False

    def download_media(self, url: str, output_dir: Path) -> Optional[str]:
        """
        下載媒體文件

        Args:
            url: 媒體URL
            output_dir: 輸出目錄

        Returns:
            下載的文件路徑，如果失敗則返回None
        """
        try:
            # 確保輸出目錄存在
            output_dir.mkdir(parents=True, exist_ok=True)

            # 構建 yt-dlp 命令 - 使用相對路徑避免嵌套問題
            cmd = [
                'yt-dlp',
                '--format', 'bestaudio/best',  # 優先下載最高品質音頻
                '--output', '%(title)s.%(ext)s',  # 使用相對路徑
                '--no-playlist',  # 不下載播放列表中的所有項目
                '--extract-audio',  # 提取音頻
                '--audio-format', 'mp3',  # 輸出為MP3格式
                '--audio-quality', '128K',  # 128kbps，平衡品質和檔案大小
                '--quiet',  # 安靜模式
                '--no-warnings',  # 不顯示警告
                url
            ]

            logger.info(f"開始下載: {url}")
            logger.info(f"輸出目錄: {output_dir}")
            result = subprocess.run(
                cmd,
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            if result.returncode == 0:
                # 查找下載的文件，優先查找MP3文件
                downloaded_files = list(output_dir.glob('*.mp3'))
                if downloaded_files:
                    return str(downloaded_files[0])

                # 如果沒有找到MP3文件，查找其他音頻文件
                audio_files = list(output_dir.glob('*'))
                audio_extensions = ['.wav', '.m4a', '.webm', '.flac', '.aac']
                for file in audio_files:
                    if file.suffix.lower() in audio_extensions:
                        return str(file)

            logger.error(f"下載失敗: {result.stderr}")
            return None

        except Exception as e:
            logger.error(f"下載過程中發生錯誤: {e}")
            return None

    def convert_audio_format(self, input_file: str, output_file: str) -> bool:
        """
        轉換音頻格式為 MP3 128kbps / 單聲道 / 16 kHz

        Args:
            input_file: 輸入文件路徑
            output_file: 輸出文件路徑

        Returns:
            轉換是否成功
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-acodec', 'libmp3lame',  # MP3 編碼器
                '-b:a', '128k',  # 128kbps 比特率
                '-ar', '16000',  # 16 kHz
                '-ac', '1',  # 單聲道
                '-y',  # 覆蓋輸出文件
                '-loglevel', 'error',  # 只顯示錯誤
                output_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"音頻轉換成功: {output_file}")
                return True
            else:
                logger.error(f"音頻轉換失敗: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"音頻轉換過程中發生錯誤: {e}")
            return False

    def process_download_list(self) -> None:
        """處理下載列表中的所有鏈接"""
        if not self.download_list_path.exists():
            logger.error(f"下載列表文件不存在: {self.download_list_path}")
            return

        with open(self.download_list_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

        if not urls:
            logger.warning("下載列表為空")
            return

        logger.info(f"找到 {len(urls)} 個下載鏈接")

        for url in urls:
            try:
                logger.info(f"處理鏈接: {url}")

                # 檢測媒體類型
                media_type = self.detect_media_type(url)
                logger.info(f"檢測到媒體類型: {media_type}")

                # 獲取頻道名稱
                channel_name = self.get_channel_name(url, media_type)
                logger.info(f"頻道名稱: {channel_name}")

                # 創建下載目錄
                download_path = self.create_download_directory(channel_name)
                logger.info(f"下載目錄: {download_path}")

                # 檢查是否已經處理過（去重機制）
                if self.is_already_processed(url, download_path):
                    logger.info(f"跳過已處理的URL: {url}")
                    continue

                # 下載媒體
                downloaded_file = self.download_media(url, download_path)
                if not downloaded_file:
                    logger.error(f"下載失敗，跳過: {url}")
                    continue

                # 轉換音頻格式
                input_path = Path(downloaded_file)
                output_path = input_path.with_stem(f"{input_path.stem}_processed").with_suffix('.mp3')

                if self.convert_audio_format(str(input_path), str(output_path)):
                    # 刪除原始文件
                    input_path.unlink()
                    logger.info(f"已刪除原始文件: {input_path}")
                else:
                    logger.warning(f"音頻轉換失敗，保留原始文件: {downloaded_file}")

                logger.info(f"成功處理: {url}")

            except Exception as e:
                logger.error(f"處理鏈接時發生錯誤 {url}: {e}")
                continue

    def cleanup_empty_directories(self) -> None:
        """清理空的目錄"""
        for dir_path in self.download_dir.rglob('*'):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    logger.info(f"刪除空目錄: {dir_path}")
                except Exception as e:
                    logger.warning(f"無法刪除空目錄 {dir_path}: {e}")

def main():
    """主函數"""
    print("媒體下載器 v1.0.0")
    print("=" * 50)

    # 檢查依賴
    required_commands = ['yt-dlp', 'ffmpeg']
    missing_commands = []

    for cmd in required_commands:
        if not shutil.which(cmd):
            missing_commands.append(cmd)

    if missing_commands:
        print(f"錯誤：缺少必需的命令: {', '.join(missing_commands)}")
        print("\n請安裝以下依賴：")
        print("- yt-dlp: pip install yt-dlp 或 brew install yt-dlp")
        print("- ffmpeg: brew install ffmpeg")
        return

    # 創建下載器實例
    downloader = MediaDownloader()

    try:
        # 處理下載列表
        downloader.process_download_list()

        # 清理空目錄
        downloader.cleanup_empty_directories()

        print("\n下載完成！")
        print(f"請查看目錄: {downloader.download_dir}")

    except KeyboardInterrupt:
        print("\n用戶中斷下載")
    except Exception as e:
        logger.error(f"程序執行錯誤: {e}")
        print(f"錯誤: {e}")

if __name__ == "__main__":
    main()
