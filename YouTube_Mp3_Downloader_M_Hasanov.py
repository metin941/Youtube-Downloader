import customtkinter as ctk
from tkinter import messagebox, filedialog
import webbrowser
import threading
import queue
import yt_dlp
import os
import sys
import configparser # Import configparser

# --- Configuration ---
CONFIG_FILE_NAME = "config.ini"
DEFAULT_DOWNLOAD_SUBDIR = "YouTube_MP3_Downloads" # Subdirectory within user's home or script dir

# --- Determine FFmpeg location ---
# This part is crucial for bundling FFmpeg with PyInstaller
if getattr(sys, 'frozen', False):
    # If the application is frozen (e.g., by PyInstaller)
    # sys._MEIPASS is the path to the temporary folder where PyInstaller extracts bundled files
    base_path = sys._MEIPASS
    # For bundled apps, config.ini should be next to the executable, not in _MEIPASS
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    # If running as a script (for development)
    base_path = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR = base_path

# Construct the path to the ffmpeg_bin folder relative to the base_path
FFMPEG_BIN_PATH = os.path.join(base_path, 'ffmpeg_bin')

# Verify if ffmpeg.exe (or ffmpeg for Linux/macOS) exists in this path
ffmpeg_exe_found = False
if sys.platform == "win32": # Windows
    if os.path.exists(os.path.join(FFMPEG_BIN_PATH, 'ffmpeg.exe')):
        ffmpeg_exe_found = True
elif sys.platform.startswith("linux") or sys.platform == "darwin": # Linux or macOS
    if os.path.exists(os.path.join(FFMPEG_BIN_PATH, 'ffmpeg')):
        ffmpeg_exe_found = True

if not ffmpeg_exe_found:
    print(f"Warning: FFmpeg binaries not found at {FFMPEG_BIN_PATH}. "
          "Make sure they are placed correctly in 'ffmpeg_bin' folder next to the script. "
          "yt-dlp will try to find FFmpeg in system PATH if not found here.")
    FFMPEG_BIN_PATH = None

class YouTubeMP3DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube MP3 Downloader by M.Hasanov")
        self.geometry("600x480") # Increased height for new elements
        self.resizable(False, False)

        # Configure grid layout (1 column)
        self.grid_columnconfigure(0, weight=1)

        # Initialize config parser
        self.config = configparser.ConfigParser()
        self.config_file_path = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

        # Load or set initial download directory
        self._load_config()

        # --- Widgets ---
        self.create_widgets()

        # Queue for thread communication
        self.q = queue.Queue()
        self.after(100, self.process_queue) # Start checking the queue

    def _load_config(self):
        """Loads configuration from config.ini or sets default."""
        self.config.read(self.config_file_path)
        if 'Settings' in self.config and 'download_path' in self.config['Settings']:
            saved_path = self.config['Settings']['download_path']
            if os.path.isdir(saved_path):
                self.current_download_dir = saved_path
            else:
                # Path from config is invalid, use default and save it
                self._set_default_download_dir()
                self._save_config()
        else:
            # No config or no path found, set default and save it
            self._set_default_download_dir()
            self._save_config()

    def _set_default_download_dir(self):
        """Sets the default download directory."""
        # Try to use user's home directory, fallback to script directory
        default_path = os.path.join(os.path.expanduser("~"), DEFAULT_DOWNLOAD_SUBDIR)
        if not os.path.exists(default_path):
            try:
                os.makedirs(default_path)
            except OSError:
                # Fallback if cannot create in home, use directory next to script/exe
                default_path = os.path.join(CONFIG_DIR, DEFAULT_DOWNLOAD_SUBDIR)
                if not os.path.exists(default_path):
                    os.makedirs(default_path)
        self.current_download_dir = default_path

    def _save_config(self):
        """Saves current configuration to config.ini."""
        if 'Settings' not in self.config:
            self.config['Settings'] = {}
        self.config['Settings']['download_path'] = self.current_download_dir
        try:
            with open(self.config_file_path, 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"Error saving config file: {e}")
            messagebox.showerror("Грешка при запис", f"Не може да се запише конфигурационния файл: {e}")

    def create_widgets(self):
        # Title Label
        self.title_label = ctk.CTkLabel(self, text="Изтегляне на YouTube MP3", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="n")

        # URL Input Frame
        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.url_frame.grid_columnconfigure(1, weight=1) # Make entry expand

        self.url_label = ctk.CTkLabel(self.url_frame, text="YouTube URL:", font=ctk.CTkFont(size=14))
        self.url_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Напр. https://www.youtube.com/watch?v=dQw4w9WgXcQ", width=350, font=ctk.CTkFont(size=14))
        self.url_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")
        self.url_entry.bind("<Return>", self.start_download_from_event) # Allow pressing Enter to download

        # Download Location Frame
        self.location_frame = ctk.CTkFrame(self)
        self.location_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.location_frame.grid_columnconfigure(1, weight=1) # Make entry expand

        self.location_label = ctk.CTkLabel(self.location_frame, text="Папка за запис:", font=ctk.CTkFont(size=14))
        self.location_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.location_entry = ctk.CTkEntry(self.location_frame, width=300, font=ctk.CTkFont(size=14))
        self.location_entry.grid(row=0, column=1, padx=(0, 5), pady=10, sticky="ew")
        self.location_entry.insert(0, self.current_download_dir) # Set initial default path from config
        self.location_entry.configure(state="readonly") # Make it read-only

        self.browse_button = ctk.CTkButton(self.location_frame, text="Избери", command=self.browse_download_location,
                                           font=ctk.CTkFont(size=14), width=80)
        self.browse_button.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="e")

        # Download Button
        self.download_button = ctk.CTkButton(self, text="Изтегли MP3", command=self.start_download,
                                             font=ctk.CTkFont(size=16, weight="bold"), height=40,
                                             fg_color="#2ECC71", hover_color="#27AE60") # Green color
        self.download_button.grid(row=3, column=0, pady=20, sticky="n")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal", width=400)
        self.progress_bar.set(0) # Initialize to 0
        self.progress_bar.grid(row=4, column=0, pady=(0, 10), sticky="n")

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Готов.", font=ctk.CTkFont(size=14), text_color="#777")
        self.status_label.grid(row=5, column=0, pady=(0, 10), sticky="n")

        # Footer
        self.footer_label = ctk.CTkLabel(self, text="© 2025 Dev: Metin Hasanov (Gemini 2.5 Flash)", font=ctk.CTkFont(size=10), text_color="#999")
        self.footer_label.grid(row=6, column=0, pady=(20, 10), sticky="s")

    def browse_download_location(self):
        """Opens a directory selection dialog and updates the location entry and config."""
        selected_dir = filedialog.askdirectory(initialdir=self.current_download_dir, title="Избери папка за запис")
        if selected_dir: # Only update if a directory was actually selected (not cancelled)
            self.current_download_dir = selected_dir
            self.location_entry.configure(state="normal") # Temporarily enable to update
            self.location_entry.delete(0, ctk.END)
            self.location_entry.insert(0, self.current_download_dir)
            self.location_entry.configure(state="readonly") # Make it read-only again
            self._save_config() # Save the newly selected path

    def start_download_from_event(self, event):
        """Allows starting download by pressing Enter in the URL entry."""
        self.start_download()

    def start_download(self):
        """Initiates the download process after validation."""
        youtube_url = self.url_entry.get()
        if not youtube_url:
            messagebox.showwarning("Предупреждение", "Моля, въведете URL адрес на YouTube видео.")
            return

        # Check if a download location is selected and valid
        if not self.current_download_dir or not os.path.isdir(self.current_download_dir):
            messagebox.showwarning("Предупреждение", "Моля, изберете валидна папка за запис.")
            # Attempt to set default again if current is invalid
            self._set_default_download_dir()
            self.location_entry.configure(state="normal")
            self.location_entry.delete(0, ctk.END)
            self.location_entry.insert(0, self.current_download_dir)
            self.location_entry.configure(state="readonly")
            self._save_config()
            return

        self.status_label.configure(text="Инициализиране на изтеглянето...")
        self.progress_bar.set(0) # Reset progress bar
        self.download_button.configure(state="disabled") # Disable button during download
        self.browse_button.configure(state="disabled") # Disable browse button

        # Start download in a separate thread
        download_thread = threading.Thread(target=self._download_thread, args=(youtube_url, self.current_download_dir, self.q))
        download_thread.start()

    def _download_thread(self, url, output_path, q):
        """Worker function for the download thread, handling yt-dlp operations."""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'restrictfilenames': True,
                'noplaylist': True,
                'progress_hooks': [lambda d: self._progress_hook(d, q)],
                'ffmpeg_location': FFMPEG_BIN_PATH, # Pass the determined FFmpeg path
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                
                # Find the actual filename after download and post-processing
                base_filename = ydl.prepare_filename(info_dict)
                mp3_filename = os.path.splitext(base_filename)[0] + ".mp3"
                
                if os.path.exists(mp3_filename):
                    q.put({"status": "finished", "filename": mp3_filename})
                else:
                    # Fallback for finding the file if the direct path doesn't work
                    found_file = None
                    for f in os.listdir(output_path):
                        if f.endswith(".mp3") and info_dict.get('title', '') in f:
                            found_file = os.path.join(output_path, f)
                            break
                    if found_file:
                        q.put({"status": "finished", "filename": found_file})
                    else:
                        raise Exception("MP3 file not found after download and conversion.")

        except Exception as e:
            q.put({"status": "error", "message": str(e)})

    def _progress_hook(self, d, q):
        """Hook for yt-dlp progress updates, sends messages to the GUI queue."""
        if d['status'] == 'finished':
            pass # The _download_thread will put the final 'finished' status
        elif d['status'] == 'downloading':
            # Calculate percentage if available
            if d.get('total_bytes') and d.get('downloaded_bytes'):
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                q.put({"status": "downloading", "percent": percent, "message": d.get('_percent_str', 'N/A')})
            elif d.get('total_bytes_estimate') and d.get('downloaded_bytes'): # Fallback for estimate
                percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                q.put({"status": "downloading", "percent": percent, "message": d.get('_percent_str', 'N/A')})
            else:
                q.put({"status": "downloading", "percent": 0, "message": d.get('_percent_str', 'N/A')}) # Unknown progress
        elif d['status'] == 'error':
            q.put({"status": "error", "message": d.get('error', 'Unknown error')})
        elif d['status'] == 'postprocessing':
            # This status is triggered when yt-dlp starts post-processing (e.g., converting to MP3)
            q.put({"status": "postprocessing", "message": "Конвертиране в MP3..."})

    def process_queue(self):
        """Checks the queue for messages from the download thread and updates the GUI."""
        try:
            while True:
                message = self.q.get_nowait()
                if message["status"] == "finished":
                    self.status_label.configure(text=f"Изтеглянето завърши: {os.path.basename(message['filename'])}")
                    self.progress_bar.set(1) # Set to 100%
                    messagebox.showinfo("Успех", f"MP3 файлът е изтеглен успешно!\nЗапазен в: {os.path.abspath(self.current_download_dir)}")
                    self.url_entry.delete(0, ctk.END) # Clear the URL entry
                elif message["status"] == "downloading":
                    self.status_label.configure(text=f"Изтегляне... {message['message']}")
                    self.progress_bar.set(message["percent"] / 100) # Set progress bar value (0-1)
                elif message["status"] == "postprocessing":
                    self.status_label.configure(text=message["message"])
                    self.progress_bar.set(0.95) # Indicate near completion for postprocessing
                elif message["status"] == "error":
                    self.status_label.configure(text="Възникна грешка.")
                    self.progress_bar.set(0) # Reset progress bar on error
                    messagebox.showerror("Грешка", f"Възникна грешка при изтеглянето: {message['message']}")
                
                # Re-enable buttons after any final status (finished or error)
                if message["status"] in ["finished", "error"]:
                    self.download_button.configure(state="normal")
                    self.browse_button.configure(state="normal")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue) # Check again after 100ms

if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # Can be "System", "Light", "Dark"
    ctk.set_default_color_theme("blue")  # Can be "blue", "green", "dark-blue"

    app = YouTubeMP3DownloaderApp()
    app.mainloop()