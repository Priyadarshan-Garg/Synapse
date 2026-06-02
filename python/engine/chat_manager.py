import sqlite3
import json
import uuid
import os
import sys
from datetime import datetime


class ChatManager:
    def __init__(self, db_name="chat_history.db"):
        # Production ready: Store data in user's home directory so it's not read-only
        user_home = os.path.expanduser("~")
        BASE_DIR = os.path.join(user_home, ".naina_ai")
        os.makedirs(BASE_DIR, exist_ok=True)

        db_path = os.path.join(BASE_DIR, db_name)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS sessions
                            (
                                session_id
                                TEXT
                                PRIMARY
                                KEY,
                                title
                                TEXT,
                                created_at
                                DATETIME
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            """)


        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS messages
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                session_id
                                TEXT,
                                role
                                TEXT, -- 'user' or 'assistant'
                                content
                                TEXT,
                                timestamp
                                DATETIME
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                FOREIGN
                                KEY
                            (
                                session_id
                            ) REFERENCES sessions
                            (
                                session_id
                            )
                                )
                            """)
        self.conn.commit()

    #  New Session Start Karna 
    def create_session(self, title="New Chat"):
        session_id = str(uuid.uuid4())  # Unique ID generate karo
        self.cursor.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, title))
        self.conn.commit()
        return session_id

    #  Message Save Karna 
    def add_message(self, session_id, role, content):
        self.cursor.execute("""
                            INSERT INTO messages (session_id, role, content)
                            VALUES (?, ?, ?)
                            """, (session_id, role, content))
        self.conn.commit()

    #  History Retrieve Karna (LLM Context ke liye) 
    def get_history(self, session_id, limit=10):
        # Last 'limit' messages nikalo taaki LLM ko context mile
        self.cursor.execute("""
                            SELECT role, content
                            FROM messages
                            WHERE session_id = ?
                            ORDER BY timestamp ASC
                            """, (session_id,))

        rows = self.cursor.fetchall()
        # OpenAI format me converter
        history = [{"role": row[0], "content": row[1]} for row in rows]
        return history

    # Although it's currently not useful may be we could use in further versions
    def get_all_sessions(self):
        self.cursor.execute("SELECT session_id, title, created_at FROM sessions ORDER BY created_at DESC")
        return self.cursor.fetchall()