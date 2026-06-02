"""This class is responsible for managing the identity of the user.
It detects when the user changes and fetches the appropriate memory.
It also keeps a short history of what the user said (for context)."""
import re
class IdentityManager:
    def __init__(self, db_engine):
        self.db = db_engine
        self.current_user = "Unknown"
        self.buffer = []  # Context buffer

    def detect_user_change(self, text):
        """
        Detects if the user is introducing themselves.
        Example: "My name is Priyadarshan" or "I am Ankit"
        """
        text = text.lower()

        # Patterns to catch name introduction
        patterns = [
            r"my name is (\w+)",
            r"i am (\w+)",
            r"this is (\w+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                new_name = match.group(1).capitalize()

                # Ignored words (taaki "I am happy" ko naam na samjhe)
                ignored_words = ["happy", "sad", "busy", "here", "ready", "going", "playing", "listening"]
                if new_name.lower() in ignored_words:
                    return None

                if new_name != self.current_user:
                    return new_name

        return None

    def switch_user(self, new_name):
        """
        Switches the current user context and fetches memory.
        """
        self.current_user = new_name
        print(f"[Identity] Context switched to: {self.current_user}")

        # DB se purani baatein nikalo
        user_data = self.db.find_user(new_name)
        return user_data

    def add_to_buffer(self, text):
        """
        Keeps a short history of what user said (for context).
        """
        self.buffer.append(text)
        if len(self.buffer) > 5:
            self.buffer.pop(0)