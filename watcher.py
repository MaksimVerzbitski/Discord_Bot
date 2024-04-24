import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import sys


# Function to install dependencies from a requirements file
def install_dependencies():
    subprocess.run(['pip', 'install', '-r', 'requirements_for_discordBot.txt'], check=True)

# Calling the function at the beginning of the script to ensure all dependencies are installed
install_dependencies()

class ChangeHandler(FileSystemEventHandler):
    """Restart the bot process if the script file changes."""

    def __init__(self, script_name):
        self.script_name = script_name
        self.process = subprocess.Popen(['python', self.script_name], stdout=subprocess.PIPE)
        print(f"Started {self.script_name} with PID {self.process.pid}")

    def on_modified(self, event):
        if event.src_path.endswith(self.script_name):
            self.process.terminate()  # Terminate the existing bot process
            self.process.wait()  # Wait for the process to terminate
            self.process = subprocess.Popen(['python', self.script_name], stdout=subprocess.PIPE)  # Restart the bot
            print(f"Restarted {self.script_name} with PID {self.process.pid}")

if __name__ == "__main__":
    path = '.'  # Current directory
    script_name = 'music_bot.py'  # Your bot script

    event_handler = ChangeHandler(script_name)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    print(f"Watching for changes in {script_name}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()