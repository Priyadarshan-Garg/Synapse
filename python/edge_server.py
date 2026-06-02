import colorama
import zmq
import numpy as np
import threading
import time
import cv2 as cv
import os
import scipy.signal

from  .main import Synapse


class EdgeBridge:
    def __init__(self):
        print("Starting Synapse Edge Bridge...")
        self.app = Synapse()

        self.VIDEO_PORT = "5555"
        self.AUDIO_PORT = "5556"

        self.PI_SAMPLE_RATE  = 48000
        self.STT_SAMPLE_RATE = 16000
        self.SILENCE_THRESHOLD = 0.01
        self.SILENCE_DURATION  = 1.0

        # Pi se aane wala latest frame yahan store hoga
        self.latest_frame = None
        self.frame_lock   = threading.Lock()

    def _resample_audio(self, audio_np):
        """48kHz Pi audio → 16kHz STT ke liye"""
        target_length = int(len(audio_np) * self.STT_SAMPLE_RATE / self.PI_SAMPLE_RATE)
        return scipy.signal.resample(audio_np, target_length).astype(np.float32)

    def process_command(self, command):
        """main.py ka exact flow — music remove, baki same"""
        if not command:
            return

        print(f"\n [Edge Heard]: {command}")
        start_time = time.perf_counter()
        command_lower = command.lower()

        # 1. Exit Check
        if self.app.check_exit(command_lower):
            self.app.mouth.speak_for_rpi("Goodbye! Shutting down.")
            end_time = time.perf_counter()
            total_time = end_time - start_time
            print(colorama.Fore.MAGENTA + f" [Total Time]: {total_time:.2f} ms")
            os._exit(0)

        # 2. Agentic Processing — same as main.py
        print(f"Processing: {command}")
        agentic_response = self.app.brain.run_agentic_llm(command)

        if agentic_response and "[REGISTER]" in agentic_response:
            try:
                clean_data  = agentic_response.replace("[REGISTER]", "").strip()
                name_part, info_part = clean_data.split("|", 1)
                print(f"Registration triggered: {name_part.strip()}")

                self.app.mouth.speak_for_rpi(f"Registering {name_part.strip()}.")
            except Exception as e:
                print(f"Registration Parse Error: {e}")
                self.app.mouth.speak_for_rpi("Registration failed.")
            return

        if agentic_response and "I encountered" not in agentic_response:
            print(f"Response: {agentic_response}")

            # testing
            self.app.mouth.speak(agentic_response)
            self.app.mouth.speak_for_rpi(agentic_response)
            end_time = time.perf_counter()
            total_time = end_time - start_time
            print(colorama.Fore.MAGENTA + f" [Total Time]: {total_time:.2f} ms")
            return

        # 3. Fallback
        print(f"Fallback Chat: {command}")
        ai_response = self.app.brain.chat(command)
        #testing
        self.app.mouth.speak(ai_response)
        self.app.mouth.speak_for_rpi(ai_response)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(colorama.Fore.MAGENTA + f" [Total Time]: {total_time:.2f} ms")


    def audio_listener(self):
        context      = zmq.Context()
        socket_audio = context.socket(zmq.SUB)
        socket_audio.connect(f"tcp://192.168.1.52:{self.AUDIO_PORT}")
        socket_audio.setsockopt_string(zmq.SUBSCRIBE, '')

        poller = zmq.Poller()
        poller.register(socket_audio, zmq.POLLIN)

        print(f"Audio Listening on port {self.AUDIO_PORT}...")

        audio_buffer     = []
        is_speaking      = False
        last_speech_time = time.time()

        while True:
            try:
                socks = dict(poller.poll(100))

                if socket_audio in socks:
                    packet = socket_audio.recv(flags=zmq.NOBLOCK)
                    chunk  = np.frombuffer(packet, dtype=np.float32)
                    volume = np.sqrt(np.mean(chunk ** 2))

                    if volume > self.SILENCE_THRESHOLD:
                        if not is_speaking:
                            print("Speaking...", end="\r")
                            is_speaking = True
                        audio_buffer.append(chunk)
                        last_speech_time = time.time()

                # Silence detect
                if is_speaking and (time.time() - last_speech_time) > self.SILENCE_DURATION:
                    print("\nTranscribing...")
                    full_audio = np.concatenate(audio_buffer)
                    resampled  = self._resample_audio(full_audio)
                    text       = self.app.ear.transcribe_raw(resampled)

                    if text:
                        self.process_command(text)

                    is_speaking  = False
                    audio_buffer = []
                    print("Listening...", end="\r")

            except Exception as e:
                print(f"Audio Error: {e}")
                break

    def video_listener(self):
        context      = zmq.Context()
        socket_video = context.socket(zmq.SUB)
        socket_video.subscribe(b"")
        socket_video.connect(f"tcp://192.168.1.52:{self.VIDEO_PORT}")
        print(f"Video Receiver on port {self.VIDEO_PORT}...")

        first_frame = True

        while True:
            try:
                packet = socket_video.recv(flags=zmq.NOBLOCK)
                np_arr = np.frombuffer(packet, dtype=np.uint8)
                frame  = cv.imdecode(np_arr, cv.IMREAD_COLOR)

                if frame is not None:
                    if first_frame:
                        print("\nFirst frame received from Pi!")
                        first_frame = False

                    # Pi ka frame Vision engine ko do
                    # Vision_Pro ka apna cap.read() bypass karke
                    with self.frame_lock:
                        self.latest_frame = frame.copy()

                    # Vision recognition Pi ke frame pe
                    results = self.app.vision.recognize(frame)
                    if results:
                        names = [r['name'] for r in results]
                        # LLM engine ko pata chale kaun dikh raha hai
                        if names:
                            self.app.brain.current_user = names[0].rstrip("0123456789")

                    cv.imshow("Synapse VISION", frame)

                if cv.waitKey(1) == ord('q'):
                    break

            except zmq.Again:
                pass
            except Exception as e:
                print(f"Video Error: {e}")

    def start(self):
        t_audio        = threading.Thread(target=self.audio_listener)
        t_audio.daemon = True
        t_audio.start()

        self.video_listener()  # Main thread


if __name__ == "__main__":
    bridge = EdgeBridge()
    bridge.start()