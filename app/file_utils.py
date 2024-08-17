import os
from datetime import datetime

UPLOAD_DIR = "uploaded_audios"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_uploaded_file(uploaded_file):
    # Create a unique filename using the current time
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{current_time}_{uploaded_file.name}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save the file to the specified directory
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath
