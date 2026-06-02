
import threading

import colorama
import pygame
import io
import soundfile as sf
from kokoro_onnx import Kokoro
import socket
import os
import urllib.request
import time
import numpy as np
import queue
import re
from  event_bus import broadcast_state


if not hasattr(np, "original_load"):
    np.original_load = np.load


def smart_load(*args, **kwargs):
    if 'allow_pickle' not in kwargs:
        kwargs['allow_pickle'] = True
    return np.original_load(*args, **kwargs)


np.load = smart_load


class TTS_Engine:
    _is_speaking = False
    _stop_event = threading.Event()
    _current_thread = None
    _kokoro = None

    def __init__(self):
        print(colorama.Fore.CYAN + "[TTS] Initializing Voice Engine...")

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        #  Model check karo, agar nahi hai toh download (With absolute paths)
        model_path, voices_path = self._ensure_models_exist()

        # Initialize Kokoro with Dynamic Paths
        if TTS_Engine._kokoro is None:
            try:
                start_time = time.time()
                TTS_Engine._kokoro = Kokoro(model_path, voices_path)
                print(
                    colorama.Fore.GREEN + f"[TTS] Voice Engine Loaded Successfully in {time.time() - start_time:.2f} seconds.")
            except Exception as e:
                print(colorama.Fore.RED + f"[Fatal Error] Failed to load TTS models: {e}")
                import sys
                sys.exit(1)

        self.hindi_voice = "af_bella"
        self.english_voice = "af_sarah"

    def _ensure_models_exist(self):
        # Universal safe folder approach (Jaise Whisper aur InsightFace ke liye kiya)
        user_home = os.path.expanduser("~")
        model_dir = os.path.join(user_home, ".cache", "naina_tts")
        os.makedirs(model_dir, exist_ok=True)

        files = ["kokoro-v0_19.onnx", "voices.bin"]
        base_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/"

        model_path = os.path.join(model_dir, files[0])
        voices_path = os.path.join(model_dir, files[1])

        missing_files = []
        if not os.path.exists(model_path): missing_files.append((files[0], model_path))
        if not os.path.exists(voices_path): missing_files.append((files[1], voices_path))

        if missing_files:
            print(colorama.Fore.YELLOW + "Voice Models (TTS) not found locally.")
            print(
                colorama.Fore.YELLOW + "[First boot] detected. Downloading Voice models (~100 MB)... Please keep internet ON.")

            # Live Progress Bar Generator Hook
            def progress_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = min(100.0, float(count * block_size * 100 / total_size))
                    print(f"\rDownloading: {percent:.1f}%", end="", flush=True)

            for file_name, save_path in missing_files:
                print(colorama.Fore.CYAN + f"\nFetching {file_name}...")
                try:
                    urllib.request.urlretrieve(base_url + file_name, save_path, reporthook=progress_hook)
                    print(colorama.Fore.GREEN + f"\n {file_name} downloaded securely.")
                except Exception as e:
                    print(colorama.Fore.RED + f"\n [Failed] to download {file_name}. Internet issue?")
                    print(colorama.Fore.RED + f"[Error] details: {e}")
                    import sys
                    sys.exit(1)

        return model_path, voices_path

    @classmethod
    def stop(cls):
        cls._is_speaking = False
        cls._stop_event.set()
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

    #  GENERATORS
    def _stream_generator(self, text_generator, audio_queue, target):
        sentence_buffer = ""
        sentence_endings = re.compile(r'(?<=[.?!])\s|\n|[,]')

        try:
            for chunk in text_generator:
                if TTS_Engine._stop_event.is_set(): break

                sentence_buffer += chunk
                parts = sentence_endings.split(sentence_buffer)

                if len(parts) > 1:
                    to_process = parts[:-1]
                    sentence_buffer = parts[-1]

                    for sentence in to_process:
                        if len(sentence.strip()) > 1:
                            if target == "local":
                                audio_data = self._generate_audio_bytes(sentence)
                            else:
                                audio_data = self._generate_audio_bytes_for_rpi(sentence)

                            if audio_data:
                                audio_queue.put((audio_data, sentence.strip()))

            if sentence_buffer.strip():
                if target == "local":
                    audio_data = self._generate_audio_bytes(sentence_buffer)
                else:
                    audio_data = self._generate_audio_bytes_for_rpi(sentence_buffer)

                if audio_data:
                    audio_queue.put((audio_data, sentence_buffer.strip()))

        except Exception as e:
            print(f"Streaming Gen Error: {e}")
        finally:
            audio_queue.put(None)

    def _generate_audio_bytes(self, text):
        """LOCAL (PC): Text -> WAV Bytes"""
        try:
            samples, sample_rate = TTS_Engine._kokoro.create(text, voice=self.english_voice, speed=1.0, lang="en-us")
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, samples, sample_rate, format='WAV')
            audio_buffer.seek(0)
            return audio_buffer
        except Exception as e:
            print(f"Gen Error: {e}")
            return None

    def _generate_audio_bytes_for_rpi(self, text):
        """EDGE (C++): Text -> Raw Float32 Bytes"""
        try:
            samples, sample_rate = TTS_Engine._kokoro.create(text, voice=self.english_voice, speed=1.0, lang="en-us")
            raw_float32_bytes = np.array(samples, dtype=np.float32).tobytes()
            return raw_float32_bytes
        except Exception as e:
            print(f"Gen Error: {e}")
            return None

    # PLAYERS
    def _stream_player(self, audio_queue):
        """LOCAL (PC): Plays audio using Pygame"""
        first_chunk = True
        start_time = time.perf_counter()
        while True:
            if TTS_Engine._stop_event.is_set(): break
            packet = audio_queue.get()
            if packet is None: break
            audio_data, text_segment = packet

            if first_chunk:
                print(f"[Streaming Started] (First Byte: {(time.perf_counter() - start_time) * 1000:.0f}ms)")
                first_chunk = False

            try:
                print(f"[Naina] : '{text_segment}'")
                broadcast_state("state", {"status": "speaking"})
                broadcast_state("naina_text", {"text": text_segment})
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if TTS_Engine._stop_event.is_set():
                        pygame.mixer.music.stop()
                        return
                    time.sleep(0.05)
            except Exception as e:
                print(f"Playback Error: {e}")
        TTS_Engine._is_speaking = False
        broadcast_state("state", {"status": "idle"})

    def _stream_player_for_rpi(self, audio_queue):
        """EDGE (C++): Sends raw bytes to C++ TCP Socket"""
        first_chunk = True
        start_time = time.perf_counter()
        TARGET_IP = '127.0.0.1'
        TARGET_PORT = 5000

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TARGET_IP, TARGET_PORT))
            print("[Connected] to C++ Audio Server!")
        except Exception as e:
            print(f"[Failed] to connect to C++ Audio Server: {e}")
            return

        while True:
            if TTS_Engine._stop_event.is_set(): break
            packet = audio_queue.get()
            if packet is None: break
            raw_audio_bytes, text_segment = packet

            if first_chunk:
                print(f"[Streaming] to C++ Started! (First Byte: {(time.perf_counter() - start_time) * 1000:.0f}ms)")
                first_chunk = False

            try:
                print(f"[Sending] to C++: '{text_segment}'")
                s.sendall(raw_audio_bytes)
            except Exception as e:
                print(f"[Error] in Network: {e}")
                break

        s.close()
        TTS_Engine._is_speaking = False


    def speak_stream(self, text_generator, target="local"):
        if TTS_Engine._kokoro is None: return
        TTS_Engine.stop()
        TTS_Engine._stop_event.clear()
        TTS_Engine._is_speaking = True

        audio_queue = queue.Queue()
        gen_thread = threading.Thread(target=self._stream_generator, args=(text_generator, audio_queue, target))
        player_func = self._stream_player if target == "local" else self._stream_player_for_rpi
        play_thread = threading.Thread(target=player_func, args=(audio_queue,))

        gen_thread.start()
        play_thread.start()

    def speak(self, text):
        def simple_gen(): yield text
        start_time = time.perf_counter()
        self.speak_stream(simple_gen(), target="local")
        end_time = time.perf_counter()
        print(colorama.Fore.LIGHTGREEN_EX + f"[TTS Time] : {(end_time - start_time) * 1000:.2f} ms")

    def speak_for_rpi(self, text):
        def simple_gen(): yield text

        self.speak_stream(simple_gen(), target="rpi")

    @property
    def is_speaking(self):
        return self._is_speaking