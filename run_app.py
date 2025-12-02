import subprocess
import time
import webbrowser
import sys
import os
import tempfile

def main():
    # Real path inside PyInstaller bundle
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.join(base_path, "flow_viewer.py")

    # Start Streamlit
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", app_path, "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server
    time.sleep(4)

    # Open browser
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    main()
