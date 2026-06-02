"""This class is responsible for handling the AI's responses.
It uses the Ollama API to generate responses based on user input.
It also handles the user's input and decides which tool to use."""

import json
import sys
import time
import re


import colorama
import ollama
import threading
from datetime import datetime


from  chat_manager import ChatManager
from  dynamic_db_engine import DynamicDBEngine
from  identity_manager import IdentityManager
from  vision_pro import Vision_Pro
from  music_engine import MusicEngine
from  weather_system import Wheather_Engine


class LLM_Engine:
    def __init__(self, music_engine=None, vision_engine=None, reminder_engine=None):
        # Naina System Prompt (Strict Language Enforcer)
        print(colorama.Fore.YELLOW + "[LLM] Initializing AI Brain...")
        self.reminder_engine = reminder_engine

        # Use provided music engine
        if music_engine:
            self.music = music_engine
        else:
            self.music = MusicEngine()

        # REUSE the vision engine passed from Main
        if vision_engine:
            self.vision = vision_engine
        else:
            self.vision = Vision_Pro()

        self.weather = Wheather_Engine()
        self.dynamicDb = DynamicDBEngine()
        self.chat_db = ChatManager()
        self.current_session_id = self.chat_db.create_session(title="Coding Session")
        self.id_manager = IdentityManager(self.dynamicDb)
        self.active_context = ""
        self.current_user = "Unknown"
        self.model_name = "qwen2.5:3b-instruct"

        try:
            start_time = time.time()
            models_response = ollama.list()

            # OLLAMA API
            existing_models = []
            if hasattr(models_response, 'models'):  # Agar naya ollama package hai (Object based)
                existing_models = [getattr(m, 'model', getattr(m, 'name', '')) for m in models_response.models]
            else:  # Agar purana ollama package hai (Dict based)
                existing_models = [m.get('model', m.get('name', '')) for m in models_response.get('models', [])]


            if self.model_name not in existing_models:
                print(colorama.Fore.YELLOW + f"AI Brain '{self.model_name}' not found locally.")
                print(
                    colorama.Fore.YELLOW + " [First boot] detected. Downloading language model (~1.9 GB)... Please do not close.")
                for progress in ollama.pull(self.model_name, stream=True):
                    status = progress.get('status', '')
                    completed = progress.get('completed', 0)
                    total = progress.get('total', 1)
                    if total > 1:
                        percent = (completed / total) * 100
                        print(f"\rDownloading: {status} - {percent:.1f}%", end="", flush=True)
                    else:
                        print(f"\rProcessing: {status}...", end="", flush=True)
                print(colorama.Fore.GREEN + f"\n [LLM] Model '{self.model_name}' downloaded successfully")
            else:
                print(colorama.Fore.CYAN + f"[LLM] Local brain '{self.model_name}' found.")

        except Exception as e:
            print(colorama.Fore.RED + "\n [Fatal Error] Failed to connect to Ollama backend")
            print(colorama.Fore.RED + "Please make sure Ollama is installed and running on background")
            print(colorama.Fore.RED + f"Error details: {e}")
            import sys
            sys.exit(1)

        system_instructions = """
                You are Naina, a witty conversational AI. 

                STRICT RULES:
                1. LANGUAGE: Speak ONLY in English or Hindi (Hinglish).
                2. NO HALLUCINATIONS: If input is gibberish, say "Can you repeat that?".
                3. FORMAT: Break responses into short, punchy sentences. Use new lines for pauses.
                4. Do NOT start sentences with "The user said" or "You said".
                5. Do not output long paragraphs.
                """

        self.history = [
            {"role": "system", "content": system_instructions}
        ]

        print(colorama.Fore.GREEN + f"[LLM] Engine initialized successfully in {time.time() - start_time:.2f} seconds")

    def run_agentic_llm(self, text):
        """
        It processes the user input and decides which agentic tool is suitable for using it.
        Args:
            text: user input

        Returns:
            agent response

        """
        # PRE-PROCESSING
        text = text.lower().replace("pre-edarsion", "priyadarshan").replace("predation", "priyadarshan")

        #  INJECT VISION CONTEXT 
        visual_user = self.get_active_context()
        vision_info_str = ""

        if visual_user and visual_user not in ["unknown", "camera error", "none"]:
            if self.id_manager.current_user.lower() != visual_user:
                print(f"Vision Override: Switching ID Manager to {visual_user}")
                self.id_manager.switch_user(visual_user)

            user_mem = self.dynamicDb.find_user(visual_user)
            vision_info_str = f"VISUAL REALITY: I can currently see '{visual_user}' in front of me. Memory: {user_mem}"

        elif visual_user == "unknown":
            vision_info_str = "VISUAL REALITY: I see a person in front of me, but I do not recognize them."
        else:
            vision_info_str = "VISUAL REALITY: No one is clearly visible to the camera."

        # User Change Detection
        new_user = self.id_manager.detect_user_change(text)
        if new_user:
            past_info = self.id_manager.switch_user(new_user)
            if past_info:
                self.active_context = f"You are talking to {new_user}. Memory: {past_info}"
                return f"Hello {new_user}! Long time no see. I remember {past_info}"
            else:
                self.active_context = f"You are talking to {new_user}. (New User)"
                return f"Hello {new_user}! Nice to meet you. I will remember you now."

        self.id_manager.add_to_buffer(text)

        # Check for music stop
        if "stop" in text and ("music" in text or "song" in text):
            self.music.stop()
            return "Stopping the music."

        tools_desc = """
            Available Tools:
            - Weather: 'Call : Weather <Location>'
            - Music: 'Call : Music <Song Name>'
            - Search: 'Call : Search <Query>' (Use this for 'Who is X', 'Developer', 'Creator')
            - Vision: 'Call : Vision <Query>' (Use for 'What do you see?', 'Who is this?')
            - Add to DB: 'Call : Add <Name> <Info>'
            - Update DB: 'Call : Update <Name> <Info>'
            - Final Answer: 'Final Answer : <Reply>'
            - Reminder Set: 'Call : RemindMe <task> | <YYYY-MM-DD HH:MM>'
            - Reminder List: 'Call : RemindList check'
            - Reminder Cancel: 'Call : RemindCancel <task name>'
            """


        now = datetime.now()
        current_time_str = now.strftime("%Y-%m-%d %H:%M")
        current_date_str = now.strftime("%d %B %Y")

        system_context = f"""
            You are Naina. Your Creator is 'Priyadarshan, Prerak, Akit'.  
            {vision_info_str}
        
            TOOL USAGE GUIDELINES (STRICT):
            1. VISUAL AWARENESS: Use the 'VISUAL REALITY' data above. If it says you see someone (e.g., '{visual_user}'), ACKNOWLEDGE THEM. Do not say "I don't see anyone".
            2. VISION TOOL: Use 'Call : Vision check' if user asks "What do you see?" or "Who am I?". Or any sentence that requires visual context.
            3. SEARCH: Use 'Call : Search <query>' ONLY if the user asks "Who is X?" or "What do you know about X?". Or any sentence that requires context from the database.
            4. ADD (MEMORY): Use 'Call : Add <name> <info>' ONLY when the user EXPLICITLY asks to "remember", "save", "register", or "add" a person.
            5. UPDATE: Use 'Call : Update <name> <info>' only for correcting existing info.
            6. MUSIC: Use 'Call : Music <song>' for playback.
            7. WEATHER: Use 'Call : Weather <city>' for forecasts.
            8. For reminders, STRICTLY use this format:
            Call : RemindMe <task description> | <YYYY-MM-DD HH:MM>

            EXAMPLES:
            User: "remind me to call mom at 8 PM today"
            Output: Call : RemindMe Call Mom | 2026-03-23 20:00
            
            User: "meeting with Ankit tomorrow at 10 AM"  
            Output: Call : RemindMe Meeting with Ankit | 2026-03-24 10:00
            
            CURRENT DATE & TIME: {current_time_str} ({current_date_str})
            REMINDER RULES (STRICT):
            - "today at 7" → {now.strftime('%Y-%m-%d')} 07:00 (today's date, same day)
            - "tomorrow at 8 PM" → next date 20:00
            - "in 2 hours" → current time + 2 hours
            FORMAT (PIPE REQUIRED):
            Call : RemindMe <task> | <YYYY-MM-DD HH:MM>
            
            REMINDLIST RULE (VERY STRICT):
            - User asks "any reminders?" / "do I have any schedule"?" / "pending reminders?"
            - WRITE EXACTLY : Call : RemindList all
            - NO PIPE, NO DATE, NO EXTRA TEXT
            - WRONG: Call : RemindList all | 2026-03-23
            - WRONG: Call : RemindList check
            - RIGHT: Call : RemindList all
            

            CRITICAL FALLBACK (General Knowledge):
            If you have a strong gut feeling that user wants to save or remember a person 
            (You will find an Indian name and by the sentence you feel that wanna save the persona and info) then call the 'ADD' too.
            If the user asks a general question or simply wants to chat, DO NOT CALL ANY TOOL. 
            Instead, output: 'Final Answer : <Your direct answer here>'.
            """

        prompt = f"{system_context}\n{tools_desc}\nUser asked: \"{text}\"\nDECIDE TOOL. OUTPUT FORMAT ONLY."

        print(f"Agent Thinking ...")

        try:
            raw_response = ollama.generate(model='qwen2.5:3b-instruct', prompt=prompt, options={'temperature': 0.1})
            response = raw_response['response'].strip()
            print(f"Agent Output: {response}")

            match = re.search(r"Call\s*:\s*(\w+(?:\w+)?)\s*(.*)", response, re.IGNORECASE)

            if match:
                tool_name = match.group(1).lower()
                argument = match.group(2).strip()

                #  1. VISION TOOL (Added Logic) 
                if tool_name == "vision":
                    # Use the visual_user variable we already calculated
                    if visual_user and visual_user not in ["unknown", "camera error", "none"]:
                        return f"I can see {visual_user} standing right in front of me."
                    elif visual_user == "unknown":
                        return "I can see someone, but I don't recognize them."
                    else:
                        return "I don't see anyone right now."

                elif tool_name == "weather":
                    print(f"Fetching weather data for: {argument}...")
                    data = self.weather.get_weather(argument)
                    make_response = self.build_response(text, data)
                    return make_response


                elif tool_name == "add":
                    json_info = self.extract_parameters(argument)
                    if json_info and "name" in json_info:
                        extracted_name = json_info["name"].strip()
                        extracted_info = json_info.get("info", "")

                        forbidden_names = ["naina", "i", "me", "myself", "person", "someone",
                                "unknown", "nobody", "user", "qwen", "llm", "ai", "model"]

                        if (extracted_name.lower() in forbidden_names
                                or len(extracted_name) < 3
                                or not extracted_name.replace(" ", "").isalpha()):
                            print(f"Blocked Garbage Add Request: {extracted_name}")
                            return "I'm not sure who you want me to remember. Can you say the name clearly?"

                        print(f"Triggering Registration for: {extracted_name}")
                        self.dynamicDb.add_person(extracted_name, extracted_info)
                        return f"[REGISTER] {extracted_name} | {extracted_info}"
                    else:
                        return "I couldn't understand who to add."
                elif tool_name == "remindlist":
                    # Argument ignore karo — pipe wala garbage bhi aa sakta hai
                    result = self.reminder_engine.get_all()
                    return f"Your pending reminders: {result}"

                elif tool_name == "remindme":
                    try:
                        if "|" not in argument:
                            return "Please say it like 'remind me to call mom at 8 PM today'."

                        parts = argument.split("|")
                        task = parts[0].strip()
                        time_str = parts[1].strip()

                        if not task:
                            return "What should I remind you about?"

                        remind_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M")

                        # Past time → warn karo but set mat karo
                        if remind_at < datetime.now():
                            return f"'{task}' Time has been passed. May I remind you it later?"

                        formatted = self.reminder_engine.add_reminder(task, remind_at)
                        return f"Done! I'll remind you to '{task}' on {formatted}."

                    except ValueError:
                        return "Didn't understand the time format. Please use 7' o clock format."
                    except Exception as e:
                        print(f"Reminder Error: {e}")
                        return "Something went wrong."

                elif tool_name == "update":
                    json_info = self.extract_parameters(text)
                    if json_info and "name" in json_info:
                        extracted_name = json_info["name"]
                        extracted_info = json_info["info"]
                        print(f"Updating: {extracted_name} -> {extracted_info}")
                        self.dynamicDb.update_user(extracted_name, extracted_info)
                        return f"Updated information for {extracted_name}."
                    else:
                        return "Could not extract details for update."

                elif tool_name == "music":
                    ctx = self.build_response(text, None)

                    def play_music_worker():
                        print(f"🎵 Thread fetching: {argument}")
                        try:
                            self.music.play(argument)
                        except Exception as e:
                            print(f"Music Error: {e}")

                    music_thread = threading.Thread(target=play_music_worker)
                    music_thread.daemon = True
                    music_thread.start()
                    return f"Starting music: {ctx}"

                elif tool_name == "search":
                    if any(x in argument.lower() for x in ["developer", "creator", "maker"]):
                        argument = "priyadarshan"
                    print(f"Searching DB for: {argument}")
                    data = self.dynamicDb.find_user(argument)
                    if data:
                        return self.generate_info(str(data), argument)
                    else:
                        print(f"DB Miss. Switching to General Knowledge.")
                        return self.chat(text)

            if "final answer" in response.lower():
                try:
                    return response.split(":", 1)[1].strip()
                except:
                    return response

            # If no tool matched, just chat
            return self.chat(text)

        except Exception as e:
            print(f"Agent Error: {e}")
            # Fallback to chat to prevent silence
            return self.chat(text)

    #  MISSING FUNCTIONS RESTORED BELOW 

    def get_active_context(self):
        """
        Checks who is currently in front of the camera.
        Removes trailing numbers (e.g. 'Priyadarshan7' -> 'Priyadarshan')
        """
        detected_names = self.vision.scan_scene()

        if not detected_names or detected_names == ["Camera Error"]:
            self.current_user = "None"  # Reset
            return "none"

        known_faces = [n for n in detected_names
                       if n not in ["Unknown", "Camera Error"]]

        if known_faces:
            raw_name = known_faces[0].rstrip("0123456789")
            self.current_user = raw_name if raw_name else known_faces[0]
        elif "Unknown" in detected_names:
            self.current_user = "Unknown"
        else:
            self.current_user = "None"

        return self.current_user.lower()

    def extract_parameters(self, text):
        """
        Extracts the 'name' and 'info' from the given text.
        Args:
            text: Takes a string containing name and info

        Returns: {name :string, info :string}

        """
        prompt = f"""
        Extract the 'name' and 'info' from the following user command.
        Command: "{text}"
        Return ONLY a JSON object. Format: {{"name": "Person Name", "info": "The information"}}
        """
        try:
            raw = ollama.generate(model='qwen2.5:3b-instruct', prompt=prompt, options={'temperature': 0.0})
            response_text = raw['response'].strip().replace("```json", "").replace("```", "").strip()
            return json.loads(response_text)
        except Exception as e:
            print(f"Extraction Error: {e}")
            return None

    def chat(self, user_input):
        """
            The main chat function. Where the user asks general queries and it generates responses.
        Args:
            user_input: Prompts

        Returns: Generated Response

        """
        #  Update history
        self.history.append({"role": "user", "content": user_input})

        #  Get Response
        try:
            response = ollama.chat(model='qwen2.5:3b-instruct', messages=self.history)
            reply = response['message']['content']
        except Exception as e:
            print(f"Chat Gen Error: {e}")
            reply = "I'm having trouble thinking right now. I think the LLM is not responding."

        #  Save to history
        self.history.append({"role": "assistant", "content": reply})
        self.chat_db.add_message(self.current_session_id, "user", user_input)
        self.chat_db.add_message(self.current_session_id, "assistant", reply)


        # Token per second report it uses internal clock
        eval_count = response.get('eval_count', 0)
        eval_duration = response.get('eval_duration', 0)
        if eval_duration > 0:
            eval_duration_s = eval_duration / 1e9
            exact_tps = eval_count / eval_duration_s
            print(f"[Exact TPS] : {exact_tps:.2f}")

        save_thread = threading.Thread(target=self.save_to_memory, args=(user_input, self.current_user))
        save_thread.start()

        return reply

    def build_response(self, query, data):
        system_prompt = """
            You are Naina. Convert the provided data into a natural, conversational response for the user.
            Keep it concise.
            """
        user_message = f"User Query: {query}\nData Found: {data}\nResponse:"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        try:
            response = ollama.chat(model='qwen2.5:3b-instruct', messages=messages)
            return response['message']['content'].strip()
        except:
            return f"Here is the data: {data}"

    def generate_info(self, json_text, name):
        """
        raw_json + name -> Meaningful Response
        Examples (Input): {"name": "Ankit", "info": "God of DSA"}
        Examples (Input): {"name": "Prerak", "info": "God of Javascript"}
        Args:
            json_text:
            name:

        Returns: Meaningful Response

        """
        system_prompt = (f"Describe {name} based on this data. Use 'He/She'"
                         f" based on their Indian names and use your gut feeling to use the pronouns, "
                         f"if you are not confident then use general term 'They', not 'I'. Data: {json_text}")
        try:
            response = ollama.generate(model='qwen2.5:3b-instruct', prompt=system_prompt)
            return response['response'].strip()
        except:
            return f"I found info on {name}: {json_text}"

    def save_to_memory(self, text, user_name):
        if user_name in ["Unknown", "priyadarshan"]: return

        prompt = f"Extract facts about '{user_name}' from: \"{text}\". Return fact or 'None'."
        try:
            response = ollama.generate(model='qwen2.5:3b-instruct', prompt=prompt)
            fact = response['response'].strip()
            if "None" not in fact and len(fact) > 5:
                self.dynamicDb.add_person(user_name, fact)
                print(colorama.Fore.GREEN + f"💾 Memory Updated for {user_name}: {fact}")
        except:
            pass

    def process_name_info(self, text):
        """
        Wrapper around extract_parameters to prevent AttributeError from main.py
        """
        result = self.extract_parameters(text)
        if result:
            return result
        return {"name": text, "info": ""}
