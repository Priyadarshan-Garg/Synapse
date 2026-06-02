"""This is the main file of the project.
It initializes the necessary components and starts the main loop."""

import signal
import pyaudio
import pygame

from  assistant_state_manager import AssistantState
from  dynamic_db_engine import DynamicDBEngine
from  music_engine import MusicEngine
from  reminder_engine import ReminderEngine
from  weather_system import Wheather_Engine
from  stt_engine import STT_Engine
from  tts_engine import TTS_Engine
from  llm_engine import LLM_Engine
from  event_bus import broadcast_state, UI_STATE_QUEUE

import os

import threading
import numpy as np

from openwakeword import Model

from  vision_pro import Vision_Pro
import colorama
import time

import queue
import asyncio
from fastapi import FastAPI, WebSocket, BackgroundTasks

import uvicorn
import json





app = FastAPI()



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Frontend Connected!")

    # Ek background task jo Queue se message nikal kar UI ko bhejega
    async def send_updates_to_ui():
        while True:
            if not UI_STATE_QUEUE.empty():
                msg = UI_STATE_QUEUE.get()
                await websocket.send_json(msg)
            await asyncio.sleep(0.05)

    asyncio.create_task(send_updates_to_ui())

    try:
        while True:
            data = await websocket.receive_text()
            user_data = json.loads(data)
            user_text = user_data.get("text")

            broadcast_state("user_text", {"text": user_text})
            broadcast_state("state", {"status": "thinking"})


    except Exception as e:
        print(f"[UI Disconnected] : {e}")

import sys
import logging

# App jahan install hui hai, wahi error.log banegi
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

log_path = os.path.join(BASE_DIR, 'naina_crash.log')

logging.basicConfig(filename=log_path, level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def global_exception_handler(exctype, value, traceback):
    logging.error("Uncaught Exception", exc_info=(exctype, value, traceback))
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = global_exception_handler

def kill_server_safely():
    time.sleep(1)
    print("Releasing all resources")
    os.kill(os.getpid(), signal.SIGINT)
@app.post("/shutdown")
async def shutdown_system(background_tasks: BackgroundTasks):
    print(colorama.Fore.RED + "\n[System] Shutdown signal received from UI!")
    try:
        # Graceful hardware release
        if 'synapse_app' in globals() and hasattr(synapse_app, 'vision'):
            synapse_app.vision.close_camera()
            print("Waiting 1.5s for hardware to power down...")
            time.sleep(1.5)
    except Exception as e:
        print(f"Error during hardware release: {e}")

    background_tasks.add_task(kill_server_safely())
    return {"message": "Shutting down"}

class Synapse:
    def __init__(self):
        print(colorama.Fore.CYAN + f"Initializing Synapse AI ..")
        self.db = DynamicDBEngine()
        self.vision = Vision_Pro()
        self.mouth = TTS_Engine()
        self.ear = STT_Engine()
        self.music = MusicEngine()  # Create ONCE
        self.weather = Wheather_Engine()
        self.reminder = ReminderEngine(mouth=self.mouth)
        # Pass the music engine to brain
        self.brain = LLM_Engine(music_engine=self.music, vision_engine=self.vision,
                                reminder_engine=self.reminder)  # SHARE the same instance

        self.MIC_INDEX = 1
        self.manual_music_mode = False
        
        # FIX Wakeword model path for bundled exe
        if getattr(sys, 'frozen', False):
             models_path = os.path.join(os.path.dirname(sys.executable), "src", "hey_jarvis.onnx")
        else:
             models_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "hey_jarvis.onnx")

        # Fallback agar file na ho (It'll download default ones from openwakeword)
        try:
             self.model = Model(wakeword_models=[models_path])
        except Exception as e:
             print(colorama.Fore.YELLOW + f"Wakeword model {models_path} not found. Falling back to default wake words...")
             self.model = Model()

        self.mouth.speak("Hi there")

    def check_exit(self, text):
        if any(word in text for word in ["music", "song", "gana", "playing"]):
            return False
        exit_phrases = ["exit", "quit", "stop", "terminate", "bye", "adios", "chal thik hai", "milte hai"]
        if any(phrase in text.lower() for phrase in exit_phrases):
            return True
        return False

    def start(self):
        state = AssistantState()
        while True:
            try:
                # Safe check for TTS status
                if hasattr(self.mouth, '_is_speaking') and self.mouth._is_speaking:
                    time.sleep(0.05)
                    continue

                state.set_listening(True)

                audio, command = self.ear.listen()
                state.set_listening(False)

                if command:
                    print(f"[Heard] : {command}")
                    broadcast_state("user_text", {"text": command})
                    main_start_time = time.perf_counter()  # stopwatch

                    if self.check_exit(command.lower()):
                        self.mouth.speak("Goodbye!")
                        while hasattr(self.mouth, '_is_speaking') and self.mouth._is_speaking:
                            time.sleep(0.1)
                        try:
                            self.vision.close_camera()
                            time.sleep(2.5)
                        except Exception as e:
                            print(e)
                        print("Releasing all resources")
                        os.kill(os.getpid(), signal.SIGINT)
                        return

                    print(f"[Processing] : {command}")
                    broadcast_state("state", {"status": "thinking"})
                    llm_start_time = time.perf_counter()
                    agentic_response = self.brain.run_agentic_llm(command)

                    if agentic_response and "[REGISTER]" in agentic_response:
                        try:
                            clean_data = agentic_response.replace("[REGISTER]", "").strip()
                            name_part, info_part = clean_data.split("|", 1)
                            self.handle_registration_flow(
                                pre_name=name_part.strip(),
                                pre_info=info_part.strip()
                            )
                        except Exception as e:
                            print(f"Registration Error: {e}")
                        continue

                    if agentic_response and "I encountered" not in agentic_response:
                        print(f"[Response] : {agentic_response}")

                        self.mouth.speak(agentic_response)

                        main_end_time = time.perf_counter()
                        processing_time = (main_end_time - main_start_time) * 1000
                        llm_end_time = time.perf_counter()
                        llm_processing_time = (llm_end_time - llm_start_time) * 1000
                        print(colorama.Fore.LIGHTBLUE_EX + f" [LLM Processing Time]: {llm_processing_time:.2f} ms")
                        print(colorama.Fore.MAGENTA + f" [PC Processing Time]: {processing_time:.2f} ms")
                        continue

                    # Fallback
                    print(f"[Fallback Chat] : {command}")
                    ai_response = self.brain.chat(command)
                    llm_end_time = time.perf_counter()
                    llm_processing_time = (llm_end_time - llm_start_time) * 1000
                    print(colorama.Fore.LIGHTBLUE_EX + f" [LL Processing Time]: {llm_processing_time:.2f} ms")

                    self.mouth.speak(ai_response)
                    main_end_time = time.perf_counter()
                    processing_time = (main_end_time - main_start_time) * 1000
                    print(colorama.Fore.MAGENTA + f" [PC Processing Time]: {processing_time:.2f} ms")

            except KeyboardInterrupt:
                print("\nStopping...")
                break
            except Exception as e:
                print(f"Critical Error: {e}")
                time.sleep(1)

    def handle_registration_flow(self, auto_trigger=False, pre_name=None, pre_info=None):
        """
        Handles registration flow.
        - Supports Auto-trigger (When unknown face is seen)
        - Supports Agent-trigger (When user says 'Register Ankit')
        """

        # Initialize variables from Agent arguments (if any)
        final_name = pre_name
        final_info = pre_info if pre_info else ""

        def wait_for_sarah():
            """Helper to pause execution while TTS is speaking"""
            time.sleep(0.5)
            # Safe check in case mouth is busy
            while hasattr(self.mouth, '_is_speaking') and self.mouth._is_speaking:
                time.sleep(0.1)

        #  AUTO TRIGGER (Unknown Face Detected)
        # Sirf tab chalega jab auto_trigger True ho aur Agent ne naam na diya ho
        if auto_trigger and not final_name:
            self.mouth.speak("I see someone new. Do you want me to remember them?")
            wait_for_sarah()

            print("[System] Waiting for User Decision (Yes/No)...")
            decision_made = False

            # 3 Attempts denge user ko jawab dene ke liye
            for _ in range(3):
                response = self.ear.listen()
                if not response: continue

                if any(w in response.lower() for w in ["yes", "haan", "yep", "sure", "ok"]):
                    decision_made = True
                    break
                elif any(w in response.lower() for w in ["no", "nah", "nahi", "cancel"]):
                    self.mouth.speak("Okay, ignoring.")
                    return  # Exit function

            if not decision_made:
                self.mouth.speak("No response. Ignoring for now.")
                return

        #  NAME GATHERING (Only if Agent/Auto didn't give a name)
        if not final_name:
            self.mouth.speak("Okay, tell me their name.")
            wait_for_sarah()

            attempts = 0
            while attempts < 3:
                print(f"[System] Listening for Name (Attempt {attempts + 1})...")
                user_input = self.ear.listen()

                if not user_input:
                    self.mouth.speak("I didn't hear anything. Please say the name.")
                    wait_for_sarah()
                    continue

                if "cancel" in user_input.lower():
                    self.mouth.speak("Registration cancelled.")
                    return

                # Brain processing (Your original logic to clean name)
                person_data = self.brain.process_name_info(user_input)
                extracted_name = person_data.get("name", user_input)
                temp_info = person_data.get("info", "")

                if extracted_name == "Unknown":
                    self.mouth.speak("I couldn't understand the name. Please try again.")
                    wait_for_sarah()
                    continue

                # Smart Confirmation
                self.mouth.speak(f"I heard {extracted_name}. Is that correct?")
                wait_for_sarah()
                confirm = self.ear.listen()

                if confirm and any(w in confirm.lower() for w in ["yes", "haan", "sahi", "right", "correct"]):
                    final_name = extracted_name
                    if len(temp_info) > 2:
                        final_info = temp_info
                    break
                else:
                    self.mouth.speak("Sorry. Please say the name again.")
                    wait_for_sarah()

                attempts += 1

        # Check if we still don't have a name after loops
        if not final_name:
            self.mouth.speak("I am struggling to hear. Let's try later.")
            return

        #   EXISTING USER CHECK
        # Vision engine check: Kya ye naam pehle se DB me hai?
        existing_info = self.db.check_person_exists(final_name)

        if existing_info:
            current_details = existing_info.get("details", "No details provided")
            self.mouth.speak(f"Wait, I already know {final_name}. You told me: {current_details}.")
            wait_for_sarah()
            self.mouth.speak("Do you want to update this information?")
            wait_for_sarah()

            update_response = self.ear.listen()

            if update_response and any(w in update_response.lower() for w in ["yes", "haan", "update", "change"]):
                # If Agent provided new info, use it directly
                if pre_info and len(pre_info) > 5:
                    new_details = pre_info
                else:
                    self.mouth.speak(f"Okay, tell me, who is {final_name} now?")
                    wait_for_sarah()
                    new_details = self.ear.listen()

                if new_details:
                    new_info_dict = {"details": new_details, "added_on": time.strftime("%Y-%m-%d"), "updated": True}
                    if self.vision.update_person_info(final_name, new_info_dict):
                        self.mouth.speak(f"Done. I have updated the information for {final_name}.")
                    else:
                        self.mouth.speak("Failed to update database.")
                else:
                    self.mouth.speak("I didn't hear anything. Keeping old info.")
            else:
                self.mouth.speak("Okay, keeping the existing information.")

            return  # Exit, no photo needed for update

        # MANDATORY INFO (Only if info is missing)
        if len(final_info) < 5:
            self.mouth.speak(f"Got it, {final_name}. Now, tell me, who is he? What do you want me to remember?")
            wait_for_sarah()

            details_input = self.ear.listen()
            if details_input and len(details_input) > 2:
                final_info = details_input
            else:
                final_info = "Just a friend."
                self.mouth.speak("Okay, I'll just remember him as a friend.")
                wait_for_sarah()

        #   VISION REGISTRATION (Photo Session)
        self.mouth.speak(f"Registering {final_name}. Please look at the camera.")
        wait_for_sarah()

        # Use the vision object from self (Shared object)
        # Note: Hum naya frame read kar rahe hain taaki latest pose capture ho
        ret, frame = self.vision.cap.read()
        if ret:
            info_dict = {"details": final_info, "added_on": time.strftime("%Y-%m-%d")}

            # Pass 'self.mouth' so Vision can give voice instructions (Left/Right turn etc.)
            success = self.vision.register_face(frame, final_name, info_dict, self.mouth)

            if not success:
                self.mouth.speak("Face capture failed.")
        else:
            self.mouth.speak("Camera error.")


if __name__ == "__main__":
    import threading
    import uvicorn

    try:
        # Initialize Synapse (AI Engine)
        synapse_app = Synapse()

        # Start AI Engine in a Background Thread
        print(colorama.Fore.YELLOW + "Starting AI Brain in Background...")
        ai_thread = threading.Thread(target=synapse_app.start, daemon=True)
        ai_thread.start()

        # Start FastAPI Server on the Main Thread (Blocking)
        print(colorama.Fore.GREEN + "Starting API Server on port 8000...")
        uvicorn.run(app, host="0.0.0.0", port=8000)

    except KeyboardInterrupt:
        print(f"Interrupted by user")
