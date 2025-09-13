#!/usr/bin/env python3
"""
Whisper 音頻轉錄器 - 獨立的音頻轉錄工具

功能：
- 完全獨立的音頻轉錄程序，無需依賴其他腳本
- 掃描指定資料夾及其子目錄中的音頻文件
- 使用 mlx-community/whisper-large-v3-turbo 進行高品質轉錄
- 將轉錄結果保存為同名的 txt 文件，包含時間戳記
- 支持多種音頻格式：mp3、wav、m4a、flac、aac、ogg、webm、m4v
- 智能跳過已轉錄的文件，避免重複處理
- 完整的錯誤處理和狀態檢查

使用方法：
1. 確保已安裝依賴：pip install mlx-whisper
2. 將音頻文件放入 "下載資料夾" 目錄
3. 運行：python whisper_transcrbe.py
4. 轉錄結果將保存為同名的 .txt 文件

作者: AI Assistant
版本: 1.0.0
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whisper_transcrbe.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Whisper 音頻轉錄器類"""

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

        # Whisper 模型設定
        self.model_repo = "mlx-community/whisper-large-v3-turbo"

        # 轉錄設定 - 集中管理所有參數
        self.transcribe_config = {
            'temperature': 0.0,      # 確定性輸出 (0.0-1.0)
            'task': 'transcribe',     # 任務類型: transcribe 或 translate
            'verbose': False,         # 是否顯示詳細信息
            'language': None          # 指定語言，None為自動檢測
        }

        # 也可以輕鬆添加更多參數：
        # self.transcribe_config.update({
        #     'initial_prompt': '這是中文內容',  # 提供上下文提示
        #     'no_speech_threshold': 0.6,       # 無語音閾值
        #     'compression_ratio_threshold': 2.4  # 壓縮比閾值
        # })

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

    def transcribe_audio(self, audio_path: Path) -> Optional[dict]:
        """
        轉錄單個音頻文件

        Args:
            audio_path: 音頻文件路徑

        Returns:
            轉錄結果字典，如果失敗則返回 None
        """
        try:
            logger.info(f"開始轉錄: {audio_path}")

            # 動態導入 MLX Whisper
            try:
                import mlx_whisper as whisper
            except ImportError:
                raise ImportError("mlx_whisper 模塊未安裝，請先安裝: pip install mlx-whisper")

            # 使用 MLX Whisper 進行轉錄
            # 方式1: 直接參數傳遞 (原先方式)
            # result = whisper.transcribe(
            #     str(audio_path),
            #     path_or_hf_repo=self.model_repo,
            #     temperature=0.0,
            #     task="transcribe",
            #     verbose=False
            # )

            # 方式2: 使用配置字典展開 (當前方式)
            result = whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=self.model_repo,
                **self.transcribe_config
            )

            logger.info(f"轉錄完成: {audio_path}")
            return result

        except Exception as e:
            logger.error(f"轉錄失敗 {audio_path}: {e}")
            return None

    def save_transcript(self, audio_path: Path, result: dict) -> bool:
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
            transcript_content += f"檢測語言: {result.get('language', '未知')}\n"
            transcript_content += f"轉錄時間: {result.get('processing_time', '未知')}\n\n"

            # 添加完整文本
            text = result.get('text', '').strip()
            transcript_content += f"完整文本:\n{text}\n\n"

            # 添加分段信息（如果有）
            segments = result.get('segments', [])
            if segments:
                transcript_content += "詳細分段:\n"
                for i, segment in enumerate(segments, 1):
                    start_time = segment.get('start', 0)
                    end_time = segment.get('end', 0)
                    segment_text = segment.get('text', '').strip()

                    # 格式化時間
                    start_str = f"{int(start_time)//60:02d}:{int(start_time)%60:02d}"
                    end_str = f"{int(end_time)//60:02d}:{int(end_time)%60:02d}"

                    transcript_content += f"[{start_str} - {end_str}] {segment_text}\n"

            # 寫入文件
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_content)

            logger.info(f"轉錄結果已保存: {transcript_path}")
            return True

        except Exception as e:
            logger.error(f"保存轉錄結果失敗 {audio_path}: {e}")
            return False

    def get_status_info(self) -> dict:
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
            'supported_formats': list(self.audio_extensions)
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

            # 檢查音頻文件
            audio_files = self.find_audio_files()
            if not audio_files:
                print(f"⚠️  在目錄 {self.audio_dir} 中沒有找到支援的音頻文件")
                print(f"   支援的格式: {', '.join(self.audio_extensions)}")
            else:
                print(f"✓ 發現 {len(audio_files)} 個音頻文件")

            return True

        except Exception as e:
            print(f"❌ 設置驗證失敗: {e}")
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

        # 處理每個音頻文件
        for audio_path in audio_files:
            try:
                logger.info(f"處理文件: {audio_path}")

                # 檢查是否需要轉錄
                if not self.needs_transcription(audio_path):
                    logger.info(f"跳過已轉錄的文件: {audio_path}")
                    skipped_count += 1
                    continue

                # 進行轉錄
                result = self.transcribe_audio(audio_path)
                if not result:
                    logger.error(f"轉錄失敗，跳過: {audio_path}")
                    continue

                # 保存結果
                if self.save_transcript(audio_path, result):
                    processed_count += 1
                    logger.info(f"成功處理: {audio_path}")
                else:
                    logger.error(f"保存失敗: {audio_path}")

            except Exception as e:
                logger.error(f"處理文件時發生錯誤 {audio_path}: {e}")
                continue

        # 總結報告
        logger.info(f"處理完成! 新轉錄: {processed_count} 個, 跳過: {skipped_count} 個")

def main():
    """主函數"""
    print("Whisper 音頻轉錄器 v1.0.0")
    print("=" * 50)

    # 檢查依賴
    try:
        import mlx_whisper
        print("✓ mlx_whisper 模塊檢查通過")
    except ImportError:
        print("❌ 錯誤：缺少必要的依賴 mlx_whisper")
        print("請執行以下命令安裝:")
        print("  pip install mlx-whisper")
        print("或")
        print("  pip3 install mlx-whisper")
        return

    # 檢查其他依賴
    try:
        import torch
        print("✓ PyTorch 模塊檢查通過")
    except ImportError:
        print("⚠️  警告：未檢測到 PyTorch，可能影響性能")
        print("  如需最佳性能，請安裝: pip install torch")

    print()

    # 創建轉錄器實例
    transcriber = WhisperTranscriber()

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
