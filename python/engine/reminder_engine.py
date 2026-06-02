"""This class is responsible for managing reminders.
It uses the APScheduler library to schedule tasks and save them to a JSON file.
It also provides methods to add, cancel, and retrieve reminders."""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import colorama
import json
import os
import sys


user_home = os.path.expanduser("~")
BASE_DIR = os.path.join(user_home, ".naina_ai")
os.makedirs(BASE_DIR, exist_ok=True)

REMINDERS_FILE = os.path.join(BASE_DIR, "reminders.json")

class ReminderEngine:
    def __init__(self, mouth):
        self.mouth = mouth
        self.scheduler = BackgroundScheduler()
        print(f"[Reminder] File path: {REMINDERS_FILE}")
        self.scheduler.start()
        print(colorama.Fore.GREEN + "[Reminder] Engine Started.")

        # Restart pe purane reminders load karo
        self._load_from_file()

    def _save_to_file(self):
        jobs = self.scheduler.get_jobs()
        data = []
        for job in jobs:
            # Timezone strip karke save karo
            run_date = job.next_run_time.replace(tzinfo=None)
            data.append({
                "id": job.id,
                "task": job.args[0],
                "run_date": run_date.isoformat()
            })
        with open(REMINDERS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _load_from_file(self):
        if not os.path.exists(REMINDERS_FILE):
            print(f"[Reminder] File not found: {REMINDERS_FILE}")
            return

        try:
            with open(REMINDERS_FILE, "r") as f:
                data = json.load(f)

            print(f"[Reminder] {len(data)} found in file.")
            now = datetime.now()
            loaded = 0

            for item in data:
                run_date = datetime.fromisoformat(item["run_date"])

                run_date = run_date.replace(tzinfo=None)

                if run_date < now:
                    print(f"Past reminder skip: '{item['task']}'")
                    continue

                self.scheduler.add_job(
                    self.trigger_alert,
                    'date',
                    run_date=run_date,
                    args=[item["task"]],
                    id=item["id"],
                    replace_existing=True
                )
                loaded += 1
                print(colorama.Fore.GREEN + f"[Restored]: '{item['task']}' → {run_date.strftime('%d %b, %I:%M %p')}")

            print(f"[Reminder] {loaded} reminders restored.")

        except Exception as e:
            print(colorama.Fore.RED + f"[Reminder] Load Error: {e}")
            import traceback
            traceback.print_exc()

    def add_reminder(self, task_name, trigger_time: datetime):
        job_id = f"reminder_{task_name.replace(' ', '_')}_{int(trigger_time.timestamp())}"

        self.scheduler.add_job(
            self.trigger_alert,
            'date',
            run_date=trigger_time,
            args=[task_name],
            id=job_id,
            replace_existing=True
        )

        # File mein save karo turant
        self._save_to_file()

        formatted = trigger_time.strftime('%d %b %Y at %I:%M %p')
        print(f"[Reminder] Set: '{task_name}' → {formatted}")
        return formatted

    def trigger_alert(self, task_name):
        alert = f"Reminder! {task_name}"
        print(colorama.Fore.YELLOW + f"\n {alert}\n")
        if self.mouth:
            self.mouth.speak(alert)
        # Fire hone ke baad file update karo
        self._save_to_file()

    def get_all(self):
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return "No pending reminders."
        result = []
        for job in jobs:
            result.append(
                f"• {job.args[0]} → {job.next_run_time.strftime('%d %b, %I:%M %p')}"
            )
        return "\n".join(result)

    def cancel(self, task_name):
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            if task_name.lower() in job.args[0].lower():
                job.remove()
                self._save_to_file()  # File update karo
                return f"[Cancelled] reminder for {job.args[0]}"
        return "No matching reminder found."

    def shutdown(self):
        self.scheduler.shutdown()