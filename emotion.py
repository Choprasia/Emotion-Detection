import cv2
from deepface import DeepFace
import os
import time
from tkinter import *
from tkinter import messagebox
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from PIL import Image, ImageTk

def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile("C:\\Users\\Lenovo\\projects\\Emotion-Detection\\client_secret_984184219801-knv08mh4sneu7hh6id62f0qb37gf55gq.apps.googleusercontent.com.json")
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)

# Save image to Google Drive
def upload_to_drive(drive, local_path, folder_id=None):
    try:
        print(f"Uploading file: {local_path} to folder ID: {folder_id}...")
        file = drive.CreateFile({"title": os.path.basename(local_path), "parents": [{"id": folder_id}] if folder_id else None})
        file.SetContentFile(local_path)
        file.Upload()
        print(f"File uploaded successfully. File ID: {file['id']}")
        return file['id']
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise

def get_or_create_emotion_folder(drive, emotion, parent_folder_id):
    try:
        print(f"Searching for folder '{emotion}' in parent folder ID: {parent_folder_id}...")
        folder_list = drive.ListFile({'q': f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and title='{emotion}'"}).GetList()

        if folder_list:
            print(f"Folder '{emotion}' found. Using existing folder ID: {folder_list[0]['id']}")
            return folder_list[0]['id']

        print(f"Folder '{emotion}' not found. Creating new folder...")
        folder_metadata = {
            'title': emotion,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{"id": parent_folder_id}]
        }
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        print(f"Folder '{emotion}' created successfully. Folder ID: {folder['id']}")
        return folder['id']
    except Exception as e:
        print(f"Error creating folder for emotion '{emotion}': {e}")
        raise

# Main Application with Tkinter frontend
class EmotionCaptureApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Emotion-Based Photo Organizer")
        self.master.geometry("800x600")

        # Setup UI components
        self.start_button = Button(master, text="Start Camera", command=self.start_camera, bg="green", fg="white", font=("Arial", 16))
        self.start_button.pack(pady=20)

        self.capture_button = Button(master, text="Capture Photo", command=self.capture_photo, state=DISABLED, bg="blue", fg="white", font=("Arial", 16))
        self.capture_button.pack(pady=20)

        self.stop_button = Button(master, text="Stop Camera", command=self.stop_camera, state=DISABLED, bg="red", fg="white", font=("Arial", 16))
        self.stop_button.pack(pady=20)

        self.output_label = Label(master, text="Emotion Detected: None", font=("Arial", 18))
        self.output_label.pack(pady=20)

        self.video_frame = Label(master)
        self.video_frame.pack()

        self.cap = None
        self.drive = authenticate_drive()
        self.master_folder_id = "1rGEyv8q6kR32mEhnrTo-jLjm8-t7u8Gn"  # Replace with your Google Drive master folder ID
        self.destination_folder_id = "1Els1XBSz8ISC4qKJ0k2AuAJH1o5bGLwm"  # Replace with your Google Drive destination folder ID

    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Camera not accessible!")
            return
        self.capture_button.config(state=NORMAL)
        self.stop_button.config(state=NORMAL)
        self.start_button.config(state=DISABLED)
        self.show_frame()

    def show_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Convert frame to image format for Tkinter
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_frame.imgtk = imgtk
                self.video_frame.configure(image=imgtk)
            self.master.after(10, self.show_frame)

    def capture_photo(self):
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if ret:
            photo_path = f"captured_photo_{int(time.time())}.jpg"
            cv2.imwrite(photo_path, frame)

            try:
                # Upload photo to the master folder first
                print("Uploading photo to master folder...")
                upload_to_drive(self.drive, photo_path, folder_id=self.master_folder_id)

                # Perform emotion analysis
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                emotion = result[0]['dominant_emotion']
                self.output_label.config(text=f"Emotion Detected: {emotion}")

                # Categorize and upload photo to Google Drive
                self.categorize_and_upload(photo_path, emotion)

                os.remove(photo_path)  # Clean up local file
            except Exception as e:
                messagebox.showerror("Error", f"Error processing photo: {e}")

    def categorize_and_upload(self, photo_path, emotion):
        try:
            # Get or create a folder for the emotion
            emotion_folder_id = get_or_create_emotion_folder(self.drive, emotion, self.destination_folder_id)

            # Upload the image to the emotion folder
            upload_to_drive(self.drive, photo_path, folder_id=emotion_folder_id)
            print(f"Photo categorized under '{emotion}' and uploaded successfully.")
        except Exception as e:
            print(f"Error categorizing and uploading photo: {e}")
            raise

    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.start_button.config(state=NORMAL)
        self.capture_button.config(state=DISABLED)
        self.stop_button.config(state=DISABLED)
        self.video_frame.config(image=None)

# Run the application
if __name__ == "__main__":
    root = Tk()
    app = EmotionCaptureApp(root)
    root.mainloop()
