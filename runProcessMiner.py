import os
import subprocess
import sys

# Always run the Streamlit app from the EXE directory
app_path = os.path.join(os.path.dirname(sys.executable), "flow_viewer.py")

subprocess.run(["streamlit", "run", app_path])