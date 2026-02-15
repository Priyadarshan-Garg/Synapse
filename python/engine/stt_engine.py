from faster_whisper import WhisperModel # -> Open Ai ka whisper model heavy hai..isliye faster-wishper usko c++ me optimize karke fast aur light banata hai..real-time ke liye best hai..
import speech_recognition as sr # -> whisper khud mic se nhin sunta, woh sirf audio file samjhta hai..isliye speech recognition library ka use karenge mic se audio capture karne ke liye..
import numpy as np # -> Audio data ko numpy array me convert karta hai, whisper model ko samajhne ke liye zaroori hai..
import time # -> time se hum check karnge ki model kitni der mein load hua..
import colorama # -> terminal mei colorful text dikhaata hai coloroma jisse hum error aur succes ko alaga dikha sakein..

# Colors init
colorama.init(autoreset=True)

class STT_Engine:
    def __init__(self):
        print(colorama.Fore.CYAN + "[STT] Initializing Whisper Model...")
        
        # Configuration
        model_size = "distil-large-v3" # -> distil-large-v3 model use kar hein jo ki fast aur accurate hai..bade model ko chhota aur tez banaya gaya hai..
        device = "cuda"  #  -> cuda gpu kaa use karenge speed ke liye, agar gpu nahi hai to cpu karna padega..
        compute_type = "int8" # -> int8(model ko weight ko 8 bit mein convert kar dete hein) quantization se model ka size aur latency dono kam ho jata hai, thoda accuracy sacrifice hoti hai par real-time ke liye best hai..
        
        start_time = time.time()
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type) # -> model load ho rha hai..
        print(colorama.Fore.GREEN + f"[STT] Model loaded in {time.time() - start_time:.2f} seconds")
        
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2 # -> Agar app 1.2 seconds ke liye chup rehte hein toh apna model maan lega ki aapka sentence complete ho gya hai....
        self.recognizer.energy_threshold = 4000 # -> mic ki sensitivity set kardi hai...jitni jyaada sensitivity utna loud bolna padega..400 par thik thaak aawaz mein bolna padega humein jisse model humein sun sake...chhoti moti backround ko aawaz ko ignore karega
        self.recognizer.dynamic_energy_threshold = True

    def listen(self):
        with sr.Microphone() as source: # -> mic se audio capture karne ke liye microphone source ka use karenge..with block ensure karta hai ki mic sahi se open aur close ho jaye..
            
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5) # -> 0.5 seconds tak kamre ka shor sunega toh toh use zero maan lega aur uske hisab se apni sensitivity set kar lega..isse background noise se bachne mein madad milegi..
            print(colorama.Fore.YELLOW + "\n[Listening]...", end="", flush=True) 
            
            try:
               
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=None) # -> mic se audio capture karna shuru karenge...agar user ne 5 second tak kuchh nahin bola toh program wait karna band kar dega..
                
                # -> Raw Audio Processing (Fastest Method)
                # -> mic se data raw bytes mein aata hai..whisper model ko samjhaane ke liye humein do cheeein chahiye..
                # 1. aawaz ki speed 16000 Hz honi chahiye...
                # 2. aawaz ke numbers -1.0 se 1.0 ke beech hone chahiye..kyonki ai models bade numbers par kaam nahin karte..isliye hum pehle data ko numbers mein badalte hei aur phir use 32768 se divide karek normalize kar dete hain...
                raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
                
               
                # -> Transcribe (Updated with Language Constraints)
                segments, info = self.model.transcribe(
                    audio_np,
                    beam_size=5, # -> 5 alag alag possibilites check karega aur jo bes hogi woh hi use karega..
                    # -> 1. Ye prompt model ko batata hai ki Hinglish expect kare
                    # -> initial_prompt="Priyadarshan, Trinetra, Jarvis, Ankit, Prerak,Dandotia, Hindi, English, Code, Python",
                    # ->  2. Temperature 0 karne se wo creative nahi banta (Hallucination kam hoti hai)..model ab tukke nahin maarega..
                    temperature=0.0,
                    # ->  3. Pichli baat se confuse na ho (Commands ke liye acha hai)..false karne ke baad model puraani baaton ko repeat nahin karega..
                    condition_on_previous_text=False
                )
                text = " ".join([segment.text for segment in segments])
                hallucinations = [
                    "thank you", "thanks", "you", "watching", "subtitles",
                    "copyright", "audio", "bye", "amara", "org",
                    "the user speaks in hinglish",  # YE HAI CULPRIT
                    "user speaks in hinglish",
                    "thank you for watching"
                ]
                # -> Agar text sirf hallucination hai -> Ignore
                # -> (e.g., Sirf "Thank you." aaya to ignore, par "Thank you Jarvis" aaya to chalega)
                # -> Model audio sunega aur text generate karega chaahe woh hallucination ho yaa sahi..ab hum uske clean text mein badalenge lowercase letter..ab code check karega ki kya clean text hallucination list mein hai..agar hai to ignore kar dega..agar text mein 3 se zyada shabd hain aur sab ek jaise hain (e.g., "hello hello hello") to bhi ignore kar dega..aur agar text mein "hindi" shabd hai aur text 10 characters se kam ka hai to bhi ignore kar dega kyunki aise chhote texts mein sirf language ka zikr hota hai jo ki commands ke liye useful nahi hai..
                # -> yeh ek guard ki tarah hai..
                clean_text = text.lower().replace(".", "").strip()
                if clean_text in hallucinations:
                    print(f"🚫 Ignored Hallucination: '{text}'")
                    return None,""
                if len(clean_text.split()) > 3 and len(set(clean_text.split())) == 1:
                    print(f"🚫 Ignored Repetitive Loop: '{text}'")
                    return None,""

                if "hindi" in clean_text and len(clean_text) < 10:
                    return None,""

                if text.strip():
                    return audio, text.strip()
                else:
                    return None,""
                    
            except sr.WaitTimeoutError:
                return None,""
            except Exception as e:
                print(colorama.Fore.RED + f"\nError: {e}")
                return None,""

# -> Ye helper function class ke bahar hi thik hai 
# -> This method is just for checking purpose I already have this method in main.py
def check_exit(text):
    if not text:
        return False
    exit_phrases = ["exit", "quit", "stop", "terminate", "bye", "adios"] # -> user in shabdon ko bolkar program ko band kar skta hai..
    if any(phrase in text.lower() for phrase in exit_phrases):
        return True
    return False

# -> Testing Code (Sirf tab chalega jab is file ko directly run karoge)
# -> Agar aap is file ko import karoge to yeh code run nahi hoga, isse hum apne STT engine ko test kar sakte hain..
if __name__ == "__main__":
    try:
        # -> Yahan humne STT_Engine class ka ek Object banaya. Iska matlab hai ab "engine" naam ke variable ke paas wo saari powers (model, mic settings) aa gayi hain jo humne upar class mein likhi thi.
        engine = STT_Engine()
        
        while True: # -> jab tak user khud exit nahin karega tab tak hum uski baat sunte rahenge..
            # -> Object ka function call karo
            text = engine.listen()
            
            if text:
                print(f"\nUser Said: {text}")
                if check_exit(text):
                    print("Exiting...")
                    break
    except KeyboardInterrupt:
        print("\nStopped by User") # ->  usually agar hum Ctrl + C dabaate hein program band karne ke liye python ek error deta hai..toh hum us error ki jagah ek clean message print karenge..