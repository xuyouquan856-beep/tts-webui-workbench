import wave
import struct

def get_audio_duration(file_path: str) -> float:
    """
    Tries to calculate the duration of the audio file.
    Supports WAV files natively. Falls back to 0.0 for others.
    """
    try:
        # Check if it's a WAV file by reading the header
        with open(file_path, 'rb') as f:
            header = f.read(12)
            if len(header) < 12:
                return 0.0
            # WAV files start with 'RIFF' and have 'WAVE' at offset 8
            if header[0:4] == b'RIFF' and header[8:12] == b'WAVE':
                # Re-open with wave module
                with wave.open(file_path, 'r') as wav:
                    frames = wav.getnframes()
                    rate = wav.getframerate()
                    if rate > 0:
                        return frames / float(rate)
    except Exception:
        pass
    return 0.0
