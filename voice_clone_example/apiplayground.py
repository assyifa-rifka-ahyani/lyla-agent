import base64
import os
import numpy as np
import soundfile as sf
from openai import OpenAI
from pathlib import Path

# SECURITY: read the key from MIMO_API_KEY (.env, gitignored). Never inline a
# literal. ROTATE the MiMo key in the Xiaomi console — a key leaked via git history.
API_KEY = os.environ.get("MIMO_API_KEY", "")
if not API_KEY:
    raise SystemExit("Set MIMO_API_KEY in your environment (.env) before running this example.")

audio_reference_file = Path(__file__).parent / "bmo_voice_sample.mp3"
output_file = Path(__file__).parent / "bmo_mimo_native.wav"

client = OpenAI(
    api_key=API_KEY,
    base_url=os.environ.get("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1"),
)


print("1. Membaca dan melakukan encode suara referensi...")
# Base64 Encode File MP3
try:
    with open(audio_reference_file, "rb") as f:
        voice_bytes = f.read()
        voice_base64 = base64.b64encode(voice_bytes).decode("utf-8")
except FileNotFoundError:
    print(f"❌ Error: File {audio_reference_file} tidak ditemukan.")
    exit()

print("2. Mengirim request voice cloning ke server Xiaomi MiMo...")
try:
    # 3. Request ke Endpoint Chat Completions
    completion = client.chat.completions.create(
        model="mimo-v2.5-tts-voiceclone",
        messages=[
            {
                "role": "user",
                "content": "Report good news to the leader in a brisk and upbeat tone, speaking at a slightly faster pace, with the uncontrollable excitement and a touch of pride after learning the results, and a bright and energetic voice." 
            },
            {
                "role": "assistant",
                "content": "Hello, i found a fascinating game earlier. Will u play it with me?"

            }
        ],
        audio={
            "format": "wav",
            # Wajib format data URI seperti di bawah
            "voice": f"data:audio/mpeg;base64,{voice_base64}", 
        },
        stream=True
    )

    print("3. Menerima dan memproses stream audio...")
    # 4. Parsing dan Merakit Audio Chunk (24kHz PCM16LE mono)
    collected_chunks: np.ndarray = np.array([], dtype=np.float32)
    
    for chunk in completion:
        if not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        audio = getattr(delta, "audio", None)
        
        if audio is not None:
            assert isinstance(audio, dict), f"Expected audio to be a dict, got {type(audio)}"
            
            # Decode chunk base64 ke Float32
            pcm_bytes = base64.b64decode(audio["data"])
            np_pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            collected_chunks = np.concatenate((collected_chunks, np_pcm))
            # print(f"Received audio chunk of size {len(pcm_bytes)} bytes") # Uncomment untuk debugging

    # 5. Simpan Hasil ke WAV
    sf.write(output_file, collected_chunks, samplerate=24000)
    print(f"✅ Sukses! File audio berhasil dirender di: {output_file}")

except Exception as e:
    print(f"❌ Terjadi kesalahan pada infrastruktur/koneksi: {e}")

