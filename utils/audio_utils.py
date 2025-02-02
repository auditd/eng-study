import sounddevice as sd
import soundfile as sf
import numpy as np
import wave

def record_audio(filename, duration=5, sample_rate=44100):
    """주어진 시간 동안 음성을 녹음하여 파일로 저장"""
    print("Recording...")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.int16)
    sd.wait()
    print("Finished recording.")

    # WAV 파일로 저장
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

def play_audio_from_bytes(audio_bytes, sample_rate=44100):
    """메모리에 있는 오디오 바이트 데이터를 재생"""
    sd.play(np.frombuffer(audio_bytes, dtype=np.int16), samplerate)
    sd.wait()

def play_audio(filename):
    """오디오 파일 재생"""
    data, fs = sf.read(filename, dtype='float32')
    sd.play(data, fs)
    sd.wait()