"""This class is responsible for handling to
vision queries and maintaining the active context by checking who
is the current user in front of NAINA"""

import threading
import cv2
import numpy as np
import sqlite3
import time
from ultralytics import YOLO
from insightface.app import FaceAnalysis
import pickle
import json
import colorama
import os
import sys
from thefuzz import process


class Vision_Pro:
    def __init__(self):
        print(colorama.Fore.CYAN + '[Vision] Initializing Vision Pro Engine...')
        self.yolo = YOLO('yolov8n.pt')  # Note: YOLOv8 bhi first boot pe auto-download hota hai (~6MB)
        self.is_running = True


        user_home = os.path.expanduser("~")
        insightface_root = os.path.join(user_home, ".insightface")
        model_path = os.path.join(insightface_root, "models", "buffalo_s")

        if not os.path.exists(model_path):
            print(colorama.Fore.YELLOW + "Face Recognition models not found locally.")
            print(
                colorama.Fore.YELLOW + "[First boot] detected. Downloading Vision models (~330 MB)... Please keep internet ON and do not close.")
        else:
            print(colorama.Fore.CYAN + "[Vision] Local models found. Booting offline...")

        try:
            start_time = time.time()
            self.app = FaceAnalysis(
                name='buffalo_s',
                root=insightface_root,  # <-- Ab ye kisi ke bhi PC par chalega
                providers=['CUDAExecutionProvider']
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            print(
                colorama.Fore.GREEN + f"[Vision] Model loaded successfully in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            print(
                colorama.Fore.RED + "[Fatal Error] Failed to load or download Vision models. Please check your internet connection!")
            print(colorama.Fore.RED + f"Error Details: {e}")

        # Production ready: Store data in user's home directory so it's not read-only
        naina_ai_dir = os.path.join(user_home, ".naina_ai")
        os.makedirs(naina_ai_dir, exist_ok=True)
        
        db_path = os.path.join(naina_ai_dir, 'vision_pro.db')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.setup_db()
        self.import_from_folder()

        self.known_names = []
        self.known_embeddings = []
        self.known_info = []
        self.load_memory()

        # Pehle normal index 0 try karega
        print(colorama.Fore.CYAN + '[Vision] Warming up Camera...')
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        # Agar 0 fail hua (virtual camera clash ki wajah se), to Index 1 try karega
        if not self.cap.isOpened():
            print(colorama.Fore.YELLOW + "Index 0 failed, trying Index 1 with DSHOW...")
            self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

        self.cam_lock = threading.Lock()

        print(colorama.Fore.GREEN + 'Vision Pro Engine Ready.')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_camera()
        return False

    def import_from_folder(self):
        """
        Scans 'known_faces' folder.
        If you put 'ankit.jpg' there, it automatically registers 'Ankit' into the DB.
        """
        
        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        folder_path = os.path.join(BASE_DIR, "known_faces")

        # Create folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(
                colorama.Fore.YELLOW + f"Folder Created '{folder_path}' folder. Drop photos here (e.g. 'Ankit.jpg') to auto-register!")
            return

        print(colorama.Fore.CYAN + "Folder Scanning 'known_faces' folder for new people...")

        valid_extensions = ('.jpg', '.jpeg', '.png')
        new_count = 0

        for filename in os.listdir(folder_path):
            if filename.lower().endswith(valid_extensions):
                # Clean name: "ankit_dandotia.jpg" -> "Ankit Dandotia"
                name = os.path.splitext(filename)[0].replace("_", " ").title()

                # Check if already exists in DB (Prevent Duplicates)
                self.cursor.execute("SELECT 1 FROM humans WHERE name = ?", (name,))
                if self.cursor.fetchone():
                    continue  # Skip if already registered

                # Process Image
                img_path = os.path.join(folder_path, filename)
                img = cv2.imread(img_path)

                if img is None:
                    continue

                # InsightFace requires RGB
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                faces = self.app.get(rgb_img)

                if len(faces) == 0:
                    print(f"⚠️ Warning: No face found in {filename}. Skipping.")
                    continue

                # Take the largest face in the image
                face = sorted(faces, key=lambda x: x.bbox[2] * x.bbox[3])[-1]
                embedding = face.embedding

                # Prepare DB Entry
                binary_enc = pickle.dumps(embedding)
                info = json.dumps({"details": "Imported from file", "added_on": time.strftime("%Y-%m-%d")})

                try:
                    self.cursor.execute("INSERT INTO humans (name, embedding, info) VALUES (?, ?, ?)",
                                        (name, binary_enc, info))
                    new_count += 1
                    print(f"[Auto-Registered] : {name}")
                except Exception as e:
                    print(f"[Error importing] {name}: {e}")

        if new_count > 0:
            self.conn.commit()
            print(colorama.Fore.GREEN + f"[Imported] {new_count} new faces from folder!")
        else:
            print("Folder check complete. No new valid images found.")

    def setup_db(self):
        self.cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS humans
            (
                id
                INTEGER
                PRIMARY
                KEY
                AUTOINCREMENT,
                name
                TEXT,
                info
                TEXT,
                embedding
                BLOB
            )
            ''')
        self.conn.commit()

    def load_memory(self):
        print(colorama.Fore.CYAN + 'Loading Vision Pro Memory...')
        self.cursor.execute("SELECT name, embedding, info FROM humans")
        rows = self.cursor.fetchall()

        self.known_info = []
        self.known_names = []
        self.known_embeddings = []

        for name, enc_blob, info_json in rows:
            embedding = pickle.loads(enc_blob)
            try:
                info = json.loads(info_json) if info_json else {}
            except:
                info = {}

            self.known_names.append(name)
            self.known_embeddings.append(embedding)
            self.known_info.append(info)

        print(colorama.Fore.GREEN + f"[Vision] Loaded {len(self.known_names)} identities.")

    def register_face(self, frame, name, info_dict, tts_engine):
        def speak_and_wait(text, wait_for_user_seconds=0):
            if tts_engine:
                tts_engine.speak(text)
                time.sleep(0.5)
                while hasattr(tts_engine, '_is_speaking') and tts_engine._is_speaking:
                    time.sleep(0.1)
            else:
                print(f"[TTS MISSING]: {text}")
            if wait_for_user_seconds > 0:
                print(f"Waiting {wait_for_user_seconds}s for user action...")
                time.sleep(wait_for_user_seconds)

        import os
        user_home = os.path.expanduser("~")
        naina_ai_dir = os.path.join(user_home, ".naina_ai")
        folder_path = os.path.join(naina_ai_dir, "registered_faces")

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        clean_name = name.replace(" ", "_").lower()
        timestamp = int(time.time())

        # 1. FRONT FACE
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.app.get(rgb_frame)
        if len(faces) == 0:
            print(f'No faces detected')
            speak_and_wait("I can't see your face. Please look at the camera.", 0)
            return False

        speak_and_wait("Hold on, capturing front view.", 0)
        face_straight = sorted(faces, key=lambda x: x.bbox[2] * x.bbox[3])[-1]
        embedding_straight = face_straight.embedding
        cv2.imwrite(f"{folder_path}/{clean_name}_front_{timestamp}.jpg", frame)

        # 2. LEFT FACE
        speak_and_wait("Now turn your face slightly to the left.", wait_for_user_seconds=3)
        ret, frame_left = self.cap.read()
        if not ret: return False
        rgb_left = cv2.cvtColor(frame_left, cv2.COLOR_BGR2RGB)
        faces_left = self.app.get(rgb_left)
        if len(faces_left) == 0:
            speak_and_wait("Face not found in left view, using front view instead.", 0)
            embedding_left = embedding_straight
        else:
            face_left_obj = sorted(faces_left, key=lambda x: x.bbox[2] * x.bbox[3])[-1]
            embedding_left = face_left_obj.embedding
            cv2.imwrite(f"{folder_path}/{clean_name}_left_{timestamp}.jpg", frame_left)

        # 3. RIGHT FACE
        speak_and_wait("Now turn slightly to the right.", wait_for_user_seconds=3)
        ret, frame_right = self.cap.read()
        if not ret: return False
        rgb_right = cv2.cvtColor(frame_right, cv2.COLOR_BGR2RGB)
        faces_right = self.app.get(rgb_right)
        if len(faces_right) == 0:
            speak_and_wait("Face not found in right view, using front view instead.", 0)
            embedding_right = embedding_straight
        else:
            face_right_obj = sorted(faces_right, key=lambda x: x.bbox[2] * x.bbox[3])[-1]
            embedding_right = face_right_obj.embedding
            cv2.imwrite(f"{folder_path}/{clean_name}_right_{timestamp}.jpg", frame_right)

        # 4. SMILE
        speak_and_wait("Okay, now look at the camera and give me a big smile.", wait_for_user_seconds=2)
        ret, frame_smile = self.cap.read()
        embedding_smile = embedding_straight
        if ret:
            rgb_smile = cv2.cvtColor(frame_smile, cv2.COLOR_BGR2RGB)
            faces_smile = self.app.get(rgb_smile)
            if len(faces_smile) > 0:
                face_smile_obj = sorted(faces_smile, key=lambda x: x.bbox[2] * x.bbox[3])[-1]
                embedding_smile = face_smile_obj.embedding

        # DB Insertion
        json_info = json.dumps(info_dict)
        binary_enc_straight = pickle.dumps(embedding_straight)
        binary_enc_left = pickle.dumps(embedding_left)
        binary_enc_right = pickle.dumps(embedding_right)
        binary_enc_smile = pickle.dumps(embedding_smile)

        query = "INSERT INTO humans (name, embedding, info) VALUES (?, ?, ?)"
        self.cursor.execute(query, (name, binary_enc_straight, json_info))
        self.cursor.execute(query, (name, binary_enc_left, json_info))
        self.cursor.execute(query, (name, binary_enc_right, json_info))
        self.cursor.execute(query, (name, binary_enc_smile, json_info))
        self.conn.commit()

        self.known_embeddings.extend([embedding_straight, embedding_left, embedding_right, embedding_smile])
        self.known_names.extend([name, name, name, name])
        self.known_info.extend([info_dict, info_dict, info_dict, info_dict])

        speak_and_wait(f"Done! I have successfully registered {name}.", 0)
        print(colorama.Fore.GREEN + f"[Vision] Registered new face: {name}")
        return True

    def recognize(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.app.get(rgb_frame)

        recognized = []
        for face in faces:
            embedding = face.embedding
            name = "Unknown"
            info = {}
            max_score = 0.0

            if len(self.known_embeddings) > 0:
                known_matrix = np.array(self.known_embeddings)
                sims = np.dot(known_matrix, embedding) / (
                        np.linalg.norm(known_matrix, axis=1) * np.linalg.norm(embedding)
                )
                best_idx = np.argmax(sims)
                max_score = sims[best_idx]

                if max_score > 0.45:
                    name = self.known_names[best_idx]
                    info = self.known_info[best_idx]

            bbox = face.bbox.astype(int)
            recognized.append({
                'name': name,
                'info': info,
                'bbox': bbox,
                'score': float(max_score)
            })

        return recognized

    def close_camera(self):
        self.is_running = False

        if self.cap is not None and self.cap.isOpened():
            # Pehle saare pending frames flush karo
            for _ in range(5):
                self.cap.read()

            self.cap.release()
            self.cap = None

        cv2.destroyAllWindows()
        cv2.waitKey(1)

        import time
        time.sleep(0.5)

        print("Camera Resource Released.")

    def scan_scene(self):
        if self.cap is None or not self.cap.isOpened():
            return ["Camera Error"]

        with self.cam_lock:
            best_names = []
            for _ in range(3):
                ret, frame = self.cap.read()
                if not ret:
                    continue
                results = self.recognize(frame)
                names = [f['name'] for f in results]
                known = [n for n in names if n != "Unknown"]
                if known:
                    return known
                if names:
                    best_names = names
            return best_names if best_names else []

    def get_info(self, name_query):
        try:
            self.cursor.execute("SELECT name, info FROM humans WHERE name LIKE ?", (name_query,))
            row = self.cursor.fetchone()
            if row:
                return row[0], json.loads(row[1])
            return None
        except Exception:
            return None

    def update_person_info(self, name, new_info_dict):
        """Updates the info for an existing person in the database"""
        try:
            info_json = json.dumps(new_info_dict)
            # Update all entries for this person (front, left, right, smile)
            self.cursor.execute("UPDATE humans SET info = ? WHERE name = ?", (info_json, name))
            self.conn.commit()

            # Reload RAM to reflect changes immediately
            self.load_memory()
            print(colorama.Fore.GREEN + f"[Vision] Updated info for {name}")
            return True
        except Exception as e:
            print(colorama.Fore.RED + f"[Vision] DB Update Error: {e}")
            return False

    def check_person_exists(self, final_name):
        """Checks if a person is already in the database"""
        try:
            self.cursor.execute("SELECT info FROM humans WHERE name = ? LIMIT 1", (final_name,))
            row = self.cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        except Exception:
            return None

if __name__ == "__main__":
    v = Vision_Pro()

    print("\n TEST MODE: Press 'q' to quit ")
    print("2. The camera will now try to recognize you.")

    # Warmup — camera ko settle hone do
    print("Warming up camera...")
    for _ in range(10):
        with v.cam_lock:
            if v.cap and v.cap.isOpened():
                v.cap.read()
    print("Camera ready!")

    frame_counter = 0
    current_detections = []  # Puraane detections hold karne ke liye

    while True:
        with v.cam_lock:
            ret, frame = v.cap.read()

        if not ret or frame is None:
            time.sleep(0.01)
            continue

        frame_counter += 1


        # AI model ko har 3rd frame par hi run karo, baaki time purana data dikhao
        if frame_counter % 3 == 0:
            current_detections = v.recognize(frame)

        # Draw bounding boxes using the latest available detections
        for d in current_detections:
            x1, y1, x2, y2 = d['bbox']
            name = d['name']
            score = d['score']
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

            # Box draw karo
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label aur score dikhao
            label = f"{name} ({int(score * 100)}%)"
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Vision Pro Test", frame)

        # UI event loop ko saans lene ka time do
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("User pressed 'q', exiting test mode...")
            break

        if cv2.getWindowProperty("Vision Pro Test", cv2.WND_PROP_VISIBLE) < 1:
            print("Window closed by user, exiting test mode...")
            break

    v.close_camera()