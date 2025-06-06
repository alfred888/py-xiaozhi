import platform

from src.utils.config_manager import ConfigManager

config = ConfigManager.get_instance()


class ListeningMode:
    """监听模式"""

    ALWAYS_ON = "always_on"
    AUTO_STOP = "auto_stop"
    MANUAL = "manual"


class AbortReason:
    """中止原因"""

    NONE = "none"
    WAKE_WORD_DETECTED = "wake_word_detected"
    USER_INTERRUPTION = "user_interruption"


class DeviceState:
    """设备状态"""

    IDLE = "idle"
    CONNECTING = "connecting"
    LISTENING = "listening"
    SPEAKING = "speaking"


class EventType:
    """事件类型"""

    SCHEDULE_EVENT = "schedule_event"
    AUDIO_INPUT_READY_EVENT = "audio_input_ready_event"
    AUDIO_OUTPUT_READY_EVENT = "audio_output_ready_event"


def is_official_server(ws_addr: str) -> bool:
    """判断是否为小智官方的服务器地址

    Args:
        ws_addr (str): WebSocket 地址

    Returns:
        bool: 是否为小智官方的服务器地址
    """
    return "api.tenclass.net" in ws_addr


def get_frame_duration() -> int:
    """
    获取设备的帧长度（优化版：避免独立PyAudio实例创建）

    返回:
        int: 帧长度(毫秒)
    """
    try:
        # 检查是否为官方服务器
        ota_url = config.get_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL")
        if not is_official_server(ota_url):
            return 60

        import platform

        system = platform.system()

        if system == "Windows":
            # Windows通常支持较小的缓冲区
            return 20
        elif system == "Linux":
            # Linux可能需要稍大的缓冲区以减少延迟(如果发现不行改为60)
            return 25
        elif system == "Darwin":  # macOS
            # macOS通常有良好的音频性能
            return 20
        else:
            # 其他系统使用保守值
            return 60

    except Exception:
        return 20  # 如果获取失败，返回默认值20ms


class AudioConfig:
    """音频配置类"""

    INPUT_SAMPLE_RATE = 16000
    OUTPUT_SAMPLE_RATE = 24000 if is_official_server(config.get_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL")) else 16000
    CHANNELS = 1

    # ✅ 固定帧时长为 20ms（推荐值）
    FRAME_DURATION = 20

    # ✅ 合法的 Opus 编码帧尺寸
    INPUT_FRAME_SIZE = int(INPUT_SAMPLE_RATE * FRAME_DURATION / 1000)  # 960

    OUTPUT_FRAME_SIZE = (
        4096 if platform.system() == "Linux" else int(OUTPUT_SAMPLE_RATE * FRAME_DURATION / 1000)
    )

    OPUS_APPLICATION = 2049  # OPUS_APPLICATION_AUDIO
    OPUS_FRAME_SIZE = INPUT_FRAME_SIZE
