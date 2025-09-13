#!/usr/bin/env python3
"""
Gemini 音頻轉錄器 - 使用 Google Gemini 進行音頻轉錄

功能：
- 完全獨立的音頻轉錄程序，無需依賴其他腳本
- 掃描指定資料夾及其子目錄中的音頻文件
- 使用 Google Gemini 2.5 Flash 進行高品質轉錄
- 智能音頻分割：超過30分鐘的音頻自動分割處理
- 並行處理分割後的音頻區塊，提高處理效率
- 按順序合併轉錄結果，保持時間戳連續性
- 將轉錄結果保存為同名的 txt 文件，包含時間戳記
- 支持多種音頻格式：mp3、wav、m4a、flac、aac、ogg、webm、m4v
- 智能跳過已轉錄的文件，避免重複處理
- 完整的錯誤處理和狀態檢查

使用方法：
1. 確保已安裝依賴：pip install google-genai python-dotenv
2. 配置 API 金鑰：
   - 編輯 .env 文件：GEMINI_API_KEY="your_api_key_here"
   - 或設置環境變數：export GEMINI_API_KEY="your_api_key_here"
3. 將音頻文件放入 "下載資料夾" 目錄
4. 運行：python gemini_transcribe.py
5. 轉錄結果將保存為同名的 .txt 文件

作者: AI Assistant
版本: 1.0.0
"""

import os
import json
import logging
import asyncio
import base64
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 加載環境變數
try:
    from dotenv import load_dotenv
    load_dotenv()  # 從 .env 文件加載環境變數
except ImportError:
    # 如果沒有安裝 python-dotenv，使用系統環境變數
    pass

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_transcribe.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GeminiTranscriber:
    """Gemini 音頻轉錄器類"""

    def __init__(self, audio_dir: str = "下載資料夾"):
        """
        初始化轉錄器

        Args:
            audio_dir: 音頻文件所在資料夾路徑
        """
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(exist_ok=True)

        # 支援的音頻格式
        self.audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.webm', '.m4v'}

        # Gemini 配置
        self.model_name = "gemini-2.0-flash-exp"  # 使用支持音頻的模型
        self.max_segment_duration = 30 * 60  # 30分鐘，單位為秒
        self.max_workers = 5  # 並行處理的最大數量

        # API 配置
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("請設置環境變數 GEMINI_API_KEY")

        # 重試配置
        self.max_retries = 3
        self.retry_delay = 2  # 秒

        # 轉錄提示詞
        self.transcription_prompt = """
請將這個音頻內容轉錄成完整的逐字稿。要求如下：

1. 請完整記錄所有對話內容，不要遺漏任何部分
2. 請盡可能準確地記錄每個人的說話內容
3. 如果有背景音樂或其他音效，請適當標註
4. 如果有停頓或語氣變化，請在括號中標註
5. 請按照時間順序整理內容
6. 輸出的格式應該是：
   - 首先是完整的文字內容
   - 然後是分段內容（如果可能的話，包括時間戳）

請確保轉錄的準確性和完整性。
"""

    def find_audio_files(self) -> List[Path]:
        """
        遞歸查找所有音頻文件

        Returns:
            音頻文件路徑列表
        """
        audio_files = []

        # 遞歸遍歷所有文件
        for file_path in self.audio_dir.rglob('*'):
            if (file_path.is_file() and
                file_path.suffix.lower() in self.audio_extensions and
                not file_path.name.startswith('.')):  # 過濾隱藏文件
                audio_files.append(file_path)

        return audio_files

    def get_transcript_path(self, audio_path: Path) -> Path:
        """
        獲取轉錄文件路徑

        Args:
            audio_path: 音頻文件路徑

        Returns:
            對應的轉錄文件路徑
        """
        return audio_path.with_suffix('.txt')

    def needs_transcription(self, audio_path: Path) -> bool:
        """
        檢查音頻文件是否需要轉錄

        Args:
            audio_path: 音頻文件路徑

        Returns:
            如果需要轉錄則返回 True
        """
        transcript_path = self.get_transcript_path(audio_path)
        return not transcript_path.exists()

    def get_audio_duration(self, audio_path: Path) -> float:
        """
        獲取音頻文件時長（秒）

        Args:
            audio_path: 音頻文件路徑

        Returns:
            音頻時長（秒）
        """
        try:
            # 使用 ffprobe 獲取音頻信息
            import subprocess

            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(audio_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                return duration
            else:
                logger.warning(f"無法獲取音頻時長: {audio_path}")
                return 0.0

        except Exception as e:
            logger.error(f"獲取音頻時長失敗 {audio_path}: {e}")
            return 0.0

    def split_audio_file(self, audio_path: Path) -> List[Tuple[Path, float, float]]:
        """
        如果音頻超過30分鐘，分割成多個區塊

        Args:
            audio_path: 音頻文件路徑

        Returns:
            分割後的文件列表，每個元組包含 (文件路徑, 開始時間, 結束時間)
        """
        duration = self.get_audio_duration(audio_path)

        if duration <= self.max_segment_duration:
            # 不需要分割
            return [(audio_path, 0.0, duration)]

        # 需要分割
        segments = []
        current_time = 0.0

        while current_time < duration:
            end_time = min(current_time + self.max_segment_duration, duration)
            segment_path = self._create_segment_file(audio_path, current_time, end_time)

            if segment_path:
                segments.append((segment_path, current_time, end_time))

            current_time = end_time

        logger.info(f"音頻文件 {audio_path} 被分割為 {len(segments)} 個區塊")
        return segments

    def _create_segment_file(self, audio_path: Path, start_time: float, end_time: float) -> Optional[Path]:
        """
        創建音頻分割文件

        Args:
            audio_path: 原始音頻文件路徑
            start_time: 開始時間（秒）
            end_time: 結束時間（秒）

        Returns:
            分割後的文件路徑，如果失敗則返回 None
        """
        try:
            # 生成分割文件名
            stem = audio_path.stem
            suffix = audio_path.suffix
            segment_index = int(start_time // self.max_segment_duration) + 1
            segment_name = f"{segment_index:03d}{suffix}"

            segment_path = audio_path.parent / segment_name

            # 使用 ffmpeg 進行音頻分割
            import subprocess

            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-c', 'copy',  # 複製編碼，無需重新編碼
                '-y',  # 覆蓋輸出文件
                str(segment_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"創建分割文件: {segment_path}")
                return segment_path
            else:
                logger.error(f"分割音頻失敗: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"創建分割文件失敗: {e}")
            return None

    def encode_audio_to_base64(self, audio_path: Path) -> Optional[str]:
        """
        將音頻文件編碼為 base64 字符串

        Args:
            audio_path: 音頻文件路徑

        Returns:
            base64 編碼的字符串，如果失敗則返回 None
        """
        try:
            with open(audio_path, 'rb') as f:
                audio_data = f.read()

            # 將音頻數據編碼為 base64
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            return encoded_audio

        except Exception as e:
            logger.error(f"編碼音頻文件失敗 {audio_path}: {e}")
            return None

    async def transcribe_segment_async(self, segment_info: Tuple[Path, float, float]) -> Optional[Dict]:
        """
        異步轉錄單個音頻區塊

        Args:
            segment_info: (文件路徑, 開始時間, 結束時間)

        Returns:
            轉錄結果字典，如果失敗則返回 None
        """
        segment_path, start_time, end_time = segment_info

        try:
            logger.info(f"開始轉錄區塊: {segment_path} ({start_time:.1f}s - {end_time:.1f}s)")

            # 編碼音頻
            encoded_audio = self.encode_audio_to_base64(segment_path)
            if not encoded_audio:
                return None

            # 動態導入 Google GenAI
            try:
                from google import genai
                from google.genai import types
            except ImportError:
                raise ImportError("google-genai 模塊未安裝，請先安裝: pip install google-genai")

            # 創建客戶端
            client = genai.Client(api_key=self.api_key)

            # 準備請求內容
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=self.transcription_prompt),
                        types.Part.from_bytes(
                            data=base64.b64decode(encoded_audio),
                            mime_type=self._get_mime_type(segment_path)
                        ),
                    ],
                ),
            ]

            # 配置生成參數
            generate_content_config = types.GenerateContentConfig(
                temperature=0.1,  # 低溫以獲得更確定性的輸出
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0,
                ),
            )

            # 調用 API (帶重試機制)
            full_text = self._call_gemini_api_with_retry(
                client, self.model_name, contents, generate_content_config
            )

            if not full_text:
                logger.warning(f"API 返回空內容: {segment_path}")
                return None

            result = {
                'text': full_text.strip(),
                'start_time': start_time,
                'end_time': end_time,
                'segment_path': str(segment_path),
                'processing_time': time.time()
            }

            logger.info(f"區塊轉錄完成: {segment_path}")
            return result

        except Exception as e:
            logger.error(f"轉錄區塊失敗 {segment_path}: {e}")
            # 對於臨時文件，記錄但不刪除，讓調用者決定如何處理
            return None

    def _call_gemini_api_with_retry(self, client, model_name: str, contents: list, config) -> Optional[str]:
        """
        帶重試機制的 Gemini API 調用

        Args:
            client: Gemini 客戶端
            model_name: 模型名稱
            contents: 請求內容
            config: 配置對象

        Returns:
            API 響應文本，如果失敗則返回 None
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API 調用嘗試 {attempt + 1}/{self.max_retries}")

                # 調用 API (使用流式響應)
                full_text = ""
                for chunk in client.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=config,
                ):
                    if chunk.text:
                        full_text += chunk.text

                if full_text.strip():
                    return full_text.strip()
                else:
                    logger.warning(f"API 返回空內容 (嘗試 {attempt + 1})")

            except Exception as e:
                logger.warning(f"API 調用失敗 (嘗試 {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay * (attempt + 1))  # 指數退避
                else:
                    logger.error(f"API 調用最終失敗，已重試 {self.max_retries} 次")

        return None

    def _get_mime_type(self, audio_path: Path) -> str:
        """
        根據文件擴展名獲取 MIME 類型

        Args:
            audio_path: 音頻文件路徑

        Returns:
            MIME 類型字符串
        """
        mime_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.flac': 'audio/flac',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
            '.webm': 'audio/webm',
            '.m4v': 'audio/mp4'
        }

        return mime_types.get(audio_path.suffix.lower(), 'audio/mpeg')

    async def transcribe_audio_parallel(self, segments: List[Tuple[Path, float, float]]) -> List[Dict]:
        """
        並行轉錄所有音頻區塊

        Args:
            segments: 音頻區塊列表

        Returns:
            轉錄結果列表
        """
        logger.info(f"開始並行轉錄 {len(segments)} 個區塊")

        # 創建任務列表
        tasks = []
        for segment in segments:
            task = self.transcribe_segment_async(segment)
            tasks.append(task)

        # 並行執行任務
        results = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)

        # 按時間順序排序
        results.sort(key=lambda x: x['start_time'])

        logger.info(f"並行轉錄完成，共處理 {len(results)} 個區塊")
        return results

    def merge_transcription_results(self, results: List[Dict]) -> Dict:
        """
        合併多個轉錄結果

        Args:
            results: 轉錄結果列表

        Returns:
            合併後的轉錄結果
        """
        if not results:
            return {'text': '', 'segments': []}

        # 合併完整文本
        full_text = ""
        merged_segments = []

        for i, result in enumerate(results):
            segment_text = result.get('text', '').strip()
            if segment_text:
                # 添加區塊標記
                if len(results) > 1:
                    start_time = result['start_time']
                    end_time = result['end_time']
                    full_text += f"\n\n--- 區塊 {i+1} ({start_time:.0f}s - {end_time:.0f}s) ---\n"
                full_text += segment_text

                # 添加分段信息
                merged_segments.append({
                    'start': result['start_time'],
                    'end': result['end_time'],
                    'text': segment_text
                })

        return {
            'text': full_text.strip(),
            'segments': merged_segments,
            'total_segments': len(results),
            'processing_time': time.time()
        }

    def save_transcript(self, audio_path: Path, result: Dict) -> bool:
        """
        保存轉錄結果到文件

        Args:
            audio_path: 音頻文件路徑
            result: 轉錄結果

        Returns:
            保存是否成功
        """
        try:
            transcript_path = self.get_transcript_path(audio_path)

            # 準備保存的內容
            transcript_content = f"音頻文件: {audio_path.name}\n"
            transcript_content += f"轉錄時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            transcript_content += f"使用模型: {self.model_name}\n"
            transcript_content += f"處理區塊數: {result.get('total_segments', 1)}\n\n"

            # 添加完整文本
            text = result.get('text', '').strip()
            transcript_content += f"完整文本:\n{text}\n\n"

            # 添加分段信息（如果有）
            segments = result.get('segments', [])
            if segments and len(segments) > 1:
                transcript_content += "詳細分段:\n"
                for i, segment in enumerate(segments, 1):
                    start_time = segment.get('start', 0)
                    end_time = segment.get('end', 0)
                    segment_text = segment.get('text', '').strip()

                    # 格式化時間
                    start_str = f"{int(start_time)//60:02d}:{int(start_time)%60:02d}"
                    end_str = f"{int(end_time)//60:02d}:{int(end_time)%60:02d}"

                    transcript_content += f"[區塊 {i}] {start_str} - {end_str}\n{segment_text}\n\n"

            # 寫入文件
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_content)

            logger.info(f"轉錄結果已保存: {transcript_path}")
            return True

        except Exception as e:
            logger.error(f"保存轉錄結果失敗 {audio_path}: {e}")
            return False

    def cleanup_segments(self, segments: List[Tuple[Path, float, float]], original_path: Path):
        """
        清理臨時分割文件

        Args:
            segments: 音頻區塊列表
            original_path: 原始音頻文件路徑
        """
        for segment_path, _, _ in segments:
            try:
                # 只刪除分割後的臨時文件，不刪除原始文件
                if segment_path != original_path and segment_path.exists():
                    segment_path.unlink()
                    logger.info(f"清理臨時文件: {segment_path}")
            except Exception as e:
                logger.warning(f"清理臨時文件失敗 {segment_path}: {e}")

    def get_status_info(self) -> Dict:
        """
        獲取程序狀態信息

        Returns:
            狀態信息字典
        """
        audio_files = self.find_audio_files()
        transcript_files = []

        for audio_path in audio_files:
            transcript_path = self.get_transcript_path(audio_path)
            if transcript_path.exists():
                transcript_files.append(transcript_path)

        return {
            'total_audio_files': len(audio_files),
            'transcribed_files': len(transcript_files),
            'pending_files': len(audio_files) - len(transcript_files),
            'audio_dir': str(self.audio_dir),
            'supported_formats': list(self.audio_extensions),
            'model': self.model_name,
            'max_segment_duration': self.max_segment_duration
        }

    def validate_setup(self) -> bool:
        """
        驗證設置是否正確

        Returns:
            如果設置正確則返回 True
        """
        try:
            # 檢查目錄是否存在
            if not self.audio_dir.exists():
                print(f"❌ 音頻目錄不存在: {self.audio_dir}")
                return False

            # 檢查目錄是否可寫
            test_file = self.audio_dir / ".test_write"
            try:
                test_file.write_text("test")
                test_file.unlink()
                print("✓ 目錄寫入權限檢查通過")
            except Exception as e:
                print(f"❌ 目錄寫入權限檢查失敗: {e}")
                return False

            # 檢查 API 金鑰
            if not self.api_key:
                print("❌ 未設置 GEMINI_API_KEY 環境變數")
                print("請執行: export GEMINI_API_KEY='your_api_key_here'")
                return False
            print("✓ Gemini API 金鑰檢查通過")

            # 檢查音頻文件
            audio_files = self.find_audio_files()
            if not audio_files:
                print(f"⚠️  在目錄 {self.audio_dir} 中沒有找到支援的音頻文件")
                print(f"   支援的格式: {', '.join(self.audio_extensions)})")
            else:
                print(f"✓ 發現 {len(audio_files)} 個音頻文件")

            # 檢查 ffmpeg
            try:
                import subprocess
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
                if result.returncode == 0:
                    print("✓ FFmpeg 檢查通過")
                else:
                    print("❌ FFmpeg 未安裝或不可用")
                    return False
            except FileNotFoundError:
                print("❌ FFmpeg 未安裝，請先安裝: brew install ffmpeg")
                return False

            return True

        except Exception as e:
            print(f"❌ 設置驗證失敗: {e}")
            return False

    async def process_audio_file_async(self, audio_path: Path) -> bool:
        """
        異步處理單個音頻文件

        Args:
            audio_path: 音頻文件路徑

        Returns:
            處理是否成功
        """
        try:
            logger.info(f"開始處理音頻文件: {audio_path}")

            # 檢查是否需要轉錄
            if not self.needs_transcription(audio_path):
                logger.info(f"跳過已轉錄的文件: {audio_path}")
                return True

            # 分割音頻文件
            segments = self.split_audio_file(audio_path)
            if not segments:
                logger.error(f"音頻分割失敗: {audio_path}")
                return False

            # 並行轉錄所有區塊
            results = await self.transcribe_audio_parallel(segments)

            if not results:
                logger.error(f"所有區塊轉錄失敗: {audio_path}")
                return False

            # 合併結果
            merged_result = self.merge_transcription_results(results)

            # 保存結果
            if self.save_transcript(audio_path, merged_result):
                logger.info(f"成功處理音頻文件: {audio_path}")

                # 清理臨時文件
                self.cleanup_segments(segments, audio_path)

                return True
            else:
                logger.error(f"保存轉錄結果失敗: {audio_path}")
                return False

        except Exception as e:
            logger.error(f"處理音頻文件時發生錯誤 {audio_path}: {e}")
            return False

    def process_all_audio_files(self) -> None:
        """處理所有音頻文件"""
        logger.info("開始掃描音頻文件...")

        # 查找所有音頻文件
        audio_files = self.find_audio_files()
        logger.info(f"發現 {len(audio_files)} 個音頻文件")

        if not audio_files:
            logger.warning("沒有找到音頻文件")
            return

        # 統計信息
        processed_count = 0
        skipped_count = 0
        failed_count = 0

        # 處理每個音頻文件
        async def process_all():
            nonlocal processed_count, skipped_count, failed_count

            for audio_path in audio_files:
                try:
                    logger.info(f"處理文件: {audio_path}")

                    # 檢查是否需要轉錄
                    if not self.needs_transcription(audio_path):
                        logger.info(f"跳過已轉錄的文件: {audio_path}")
                        skipped_count += 1
                        continue

                    # 異步處理文件
                    if await self.process_audio_file_async(audio_path):
                        processed_count += 1
                        logger.info(f"成功處理: {audio_path}")
                    else:
                        failed_count += 1
                        logger.error(f"處理失敗: {audio_path}")

                except Exception as e:
                    logger.error(f"處理文件時發生錯誤 {audio_path}: {e}")
                    failed_count += 1
                    continue

        # 運行異步處理
        asyncio.run(process_all())

        # 總結報告
        logger.info(f"處理完成! 新轉錄: {processed_count} 個, 跳過: {skipped_count} 個, 失敗: {failed_count} 個")


def main():
    """主函數"""
    print("Gemini 音頻轉錄器 v1.0.0")
    print("=" * 50)

    # 檢查依賴
    try:
        from google import genai
        print("✓ google-genai 模塊檢查通過")
    except ImportError:
        print("❌ 錯誤：缺少必要的依賴 google-genai")
        print("請執行以下命令安裝:")
        print("  pip install google-genai")
        print("或")
        print("  pip3 install google-genai")
        return

    try:
        import ffmpeg
        print("✓ ffmpeg-python 模塊檢查通過")
    except ImportError:
        print("⚠️  警告：未檢測到 ffmpeg-python，可能影響分割功能")
        print("  如需音頻分割功能，請安裝: pip install ffmpeg-python")

    print()

    # 創建轉錄器實例
    try:
        transcriber = GeminiTranscriber()
    except ValueError as e:
        print(f"❌ 初始化失敗: {e}")
        return

    # 驗證設置
    print("正在驗證設置...")
    if not transcriber.validate_setup():
        print("設置驗證失敗，請檢查上述錯誤信息")
        return
    print()

    try:
        # 顯示狀態信息
        print("正在檢查音頻文件狀態...")
        status = transcriber.get_status_info()
        print(f"音頻資料夾: {status['audio_dir']}")
        print(f"發現音頻文件: {status['total_audio_files']} 個")
        print(f"已轉錄文件: {status['transcribed_files']} 個")
        print(f"待轉錄文件: {status['pending_files']} 個")
        print(f"支援格式: {', '.join(status['supported_formats'])}")
        print(f"使用模型: {status['model']}")
        print(f"最大區塊時長: {status['max_segment_duration'] // 60} 分鐘")
        print()

        if status['pending_files'] == 0:
            print("所有音頻文件都已轉錄完成！")
            return

        # 處理所有音頻文件
        print("開始轉錄未處理的音頻文件...")
        transcriber.process_all_audio_files()

        print("\n轉錄完成！")
        print(f"請查看資料夾: {transcriber.audio_dir}")

    except KeyboardInterrupt:
        print("\n用戶中斷轉錄")
    except Exception as e:
        logger.error(f"程序執行錯誤: {e}")
        print(f"錯誤: {e}")


if __name__ == "__main__":
    main()
