import math
import wave
import struct
from app.providers.base import BaseTTSProvider, ProviderRequest, ProviderResult

class DummyProvider(BaseTTSProvider):
    async def generate(self, request: ProviderRequest, output_path: str) -> ProviderResult:
        # Generate a simple 440Hz wave beep using the standard library wave module
        sample_rate = 22050
        duration = 1.0  # seconds
        frequency = 440.0
        
        # Open wave file
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)   # 16-bit (2 bytes)
            wav_file.setframerate(sample_rate)
            
            # Generate sine wave samples
            num_samples = int(sample_rate * duration)
            for i in range(num_samples):
                # Calculate sample value (-32767 to 32767)
                value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
                data = struct.pack('<h', value)
                wav_file.writeframesraw(data)
                
        return ProviderResult(
            audio_path=output_path,
            format="wav",
            metadata={"dummy": True, "text": request.text, "frequency": frequency},
            duration=duration
        )
