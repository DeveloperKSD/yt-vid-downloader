"""
YouTube Video Downloader — GUI version

Features:
- Quality selection (pick resolution before downloading)
- Progress bar during download
- Playlist URL support
- Remembers last-used save folder
- Audio-only download (.mp4 audio track) and MP3 extraction
- Subtitle download (English, if available)
- Retry logic on download failure
- URL validation before hitting the network
- Graceful handling of private / age-restricted / unavailable videos
- Tkinter GUI form with a "Paste from clipboard" button

Requires: pytubefix, imageio-ffmpeg  (pip install pytubefix imageio-ffmpeg)
"""

import os
import re
import json
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

from pytubefix import YouTube, Playlist
from pytubefix.exceptions import (
    RegexMatchError,
    VideoPrivate,
    VideoUnavailable,
    AgeRestrictedError,
    LiveStreamError,
)
import imageio_ffmpeg

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
YOUTUBE_URL_PATTERN = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")
MAX_RETRIES = 3


# ---------- Config helpers (remember last save folder) ----------

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# ---------- Validation ----------

def is_valid_youtube_url(url):
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


def is_playlist_url(url):
    return "playlist" in url or "list=" in url


# ---------- Core download logic ----------

def sanitize_filename(name):
    return "".join(c for c in name if c not in r'\/:*?"<>|')


def merge_audio_video(video_file, audio_file, output_file, log):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    log("Merging video and audio...")
    subprocess.run(
        [ffmpeg_path, "-y", "-i", video_file, "-i", audio_file,
         "-c:v", "copy", "-c:a", "aac", output_file],
        check=True,
    )
    os.remove(video_file)
    os.remove(audio_file)


def extract_mp3(audio_file, output_file, log):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    log("Extracting MP3...")
    subprocess.run(
        [ffmpeg_path, "-y", "-i", audio_file, "-vn", "-acodec", "libmp3lame", output_file],
        check=True,
    )
    os.remove(audio_file)


def download_subtitles(yt, save_path, base_name, log):
    try:
        caption = yt.captions.get_by_language_code("en") or yt.captions.get_by_language_code("a.en")
        if caption:
            caption.download(title=base_name, output_path=save_path, srt=True)
            log(f"Subtitles saved for: {base_name}")
        else:
            log("No English subtitles available.")
    except Exception as e:
        log(f"Subtitle download skipped: {e}")


def get_quality_choices(yt):
    """List of (label, stream) for available video-only resolutions, highest first."""
    video_streams = (
        yt.streams.filter(file_extension="mp4", only_video=True)
        .order_by("resolution").desc()
    )
    seen, choices = set(), []
    for s in video_streams:
        if s.resolution and s.resolution not in seen:
            seen.add(s.resolution)
            choices.append((s.resolution, s))
    return choices


def download_single_video(url, save_path, quality_label, mode, want_subs, log, progress_cb,
                           retries=MAX_RETRIES):
    """mode: 'video', 'audio_only', or 'audio_mp3'"""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            yt = YouTube(url, on_progress_callback=progress_cb)
            title = sanitize_filename(yt.title)
            log(f"Fetched: {yt.title}")

            audio_stream = (
                yt.streams.filter(file_extension="mp4", only_audio=True)
                .order_by("abr").desc().first()
            )
            if audio_stream is None:
                raise RuntimeError("No audio stream available for this video.")

            if mode == "audio_mp3":
                audio_file = audio_stream.download(output_path=save_path, filename="audio_temp.mp4")
                output_file = os.path.join(save_path, f"{title}.mp3")
                extract_mp3(audio_file, output_file, log)
                log(f"Saved: {output_file}")

            elif mode == "audio_only":
                output_file = os.path.join(save_path, f"{title}.mp4")
                audio_stream.download(output_path=save_path, filename=f"{title}.mp4")
                log(f"Saved (audio only): {output_file}")

            else:  # video
                choices = get_quality_choices(yt)
                chosen = next((s for label, s in choices if label == quality_label), None)
                if chosen is None and choices:
                    chosen = choices[0][1]  # fall back to highest available
                if chosen is None:
                    raise RuntimeError("No suitable video stream found.")

                video_file = chosen.download(output_path=save_path, filename="video_temp.mp4")
                audio_file = audio_stream.download(output_path=save_path, filename="audio_temp.mp4")
                output_file = os.path.join(save_path, f"{title}.mp4")
                merge_audio_video(video_file, audio_file, output_file, log)
                log(f"Saved: {output_file}")

            if want_subs:
                download_subtitles(yt, save_path, title, log)

            return True

        except (VideoPrivate, AgeRestrictedError, LiveStreamError) as e:
            log(f"Cannot download this video ({type(e).__name__}) — skipping.")
            return False
        except VideoUnavailable as e:
            log(f"Video unavailable: {e} — skipping.")
            return False
        except RegexMatchError:
            log("Invalid or unparseable YouTube URL.")
            return False
        except Exception as e:
            last_error = e
            log(f"Attempt {attempt}/{retries} failed: {e}")

    log(f"Giving up after {retries} attempts: {last_error}")
    return False


# ---------- GUI ----------

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        root.title("YouTube Downloader")
        root.geometry("540x520")

        self.config_data = load_config()
        self.save_path = tk.StringVar(value=self.config_data.get("last_folder", ""))
        self.quality_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="video")
        self.subs_var = tk.BooleanVar(value=False)
        self.status_queue = queue.Queue()

        self._build_ui()
        self.root.after(100, self._poll_queue)

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        url_frame = tk.Frame(self.root)
        url_frame.pack(fill="x", **pad)
        tk.Label(url_frame, text="YouTube URL:").pack(side="left")
        self.url_entry = tk.Entry(url_frame, width=38)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=4)
        tk.Button(url_frame, text="Paste", command=self.paste_url).pack(side="left")
        tk.Button(url_frame, text="Fetch", command=self.fetch_info).pack(side="left")

        folder_frame = tk.Frame(self.root)
        folder_frame.pack(fill="x", **pad)
        tk.Label(folder_frame, text="Save to:").pack(side="left")
        tk.Label(folder_frame, textvariable=self.save_path, fg="blue").pack(
            side="left", fill="x", expand=True, padx=4)
        tk.Button(folder_frame, text="Choose Folder", command=self.choose_folder).pack(side="left")

        mode_frame = tk.LabelFrame(self.root, text="Download Type")
        mode_frame.pack(fill="x", **pad)
        tk.Radiobutton(mode_frame, text="Video (choose quality)", variable=self.mode_var,
                        value="video", command=self.toggle_quality).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Audio only (.mp4 audio track)", variable=self.mode_var,
                        value="audio_only", command=self.toggle_quality).pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Audio as MP3", variable=self.mode_var,
                        value="audio_mp3", command=self.toggle_quality).pack(anchor="w")

        self.quality_frame = tk.Frame(self.root)
        self.quality_frame.pack(fill="x", **pad)
        tk.Label(self.quality_frame, text="Quality:").pack(side="left")
        self.quality_dropdown = ttk.Combobox(self.quality_frame, textvariable=self.quality_var,
                                              state="readonly", width=20)
        self.quality_dropdown.pack(side="left", padx=4)

        tk.Checkbutton(self.root, text="Download English subtitles (if available)",
                        variable=self.subs_var).pack(anchor="w", **pad)

        self.download_btn = tk.Button(self.root, text="Download", command=self.start_download,
                                       state="disabled", bg="#4CAF50", fg="white")
        self.download_btn.pack(pady=8)

        self.progress = ttk.Progressbar(self.root, length=480, mode="determinate")
        self.progress.pack(padx=8, pady=4)

        self.log_box = tk.Text(self.root, height=13, width=64, state="disabled")
        self.log_box.pack(padx=8, pady=4, fill="both", expand=True)

    def toggle_quality(self):
        self.quality_dropdown.config(state="readonly" if self.mode_var.get() == "video" else "disabled")

    def log(self, msg):
        self.status_queue.put(msg)

    def _poll_queue(self):
        while not self.status_queue.empty():
            msg = self.status_queue.get()
            if isinstance(msg, tuple) and msg[0] == "progress":
                self.progress["value"] = msg[1]
            else:
                self.log_box.config(state="normal")
                self.log_box.insert("end", str(msg) + "\n")
                self.log_box.see("end")
                self.log_box.config(state="disabled")
        self.root.after(100, self._poll_queue)

    def paste_url(self):
        try:
            clip = self.root.clipboard_get()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clip)
        except tk.TclError:
            self.log("Clipboard is empty.")

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.set(folder)
            self.config_data["last_folder"] = folder
            save_config(self.config_data)

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid YouTube URL.")
            return

        def worker():
            try:
                if is_playlist_url(url):
                    pl = Playlist(url)
                    self.log(f"Playlist detected: {len(pl.video_urls)} videos found.")
                    self.root.after(0, lambda: self.quality_dropdown.configure(values=[]))
                    self.root.after(0, lambda: self.download_btn.config(state="normal"))
                    return

                yt = YouTube(url)
                choices = get_quality_choices(yt)
                labels = [c[0] for c in choices]
                self.root.after(0, lambda: self.quality_dropdown.configure(values=labels))
                if labels:
                    self.root.after(0, lambda: self.quality_var.set(labels[0]))
                self.log(f"Fetched: {yt.title}")
                self.root.after(0, lambda: self.download_btn.config(state="normal"))
            except (VideoPrivate, AgeRestrictedError, LiveStreamError) as e:
                self.log(f"Cannot access this video: {type(e).__name__}")
            except VideoUnavailable as e:
                self.log(f"Video unavailable: {e}")
            except RegexMatchError:
                self.log("Could not parse this URL as a YouTube video.")
            except Exception as e:
                self.log(f"Error fetching video info: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def progress_callback(self, stream, chunk, bytes_remaining):
        total = stream.filesize
        done = total - bytes_remaining
        percent = (done / total) * 100 if total else 0
        self.status_queue.put(("progress", percent))

    def start_download(self):
        url = self.url_entry.get().strip()
        save_path = self.save_path.get()
        if not save_path:
            messagebox.showerror("No folder", "Please choose a save folder.")
            return
        if not is_valid_youtube_url(url):
            messagebox.showerror("Invalid URL", "Please enter a valid YouTube URL.")
            return

        self.download_btn.config(state="disabled")
        mode = self.mode_var.get()
        quality_label = self.quality_var.get()
        want_subs = self.subs_var.get()

        def worker():
            if is_playlist_url(url):
                pl = Playlist(url)
                total = len(pl.video_urls)
                for i, video_url in enumerate(pl.video_urls, 1):
                    self.log(f"[{i}/{total}] Starting: {video_url}")
                    self.status_queue.put(("progress", 0))
                    download_single_video(video_url, save_path, quality_label, mode,
                                           want_subs, self.log, self.progress_callback)
                self.log("Playlist download complete.")
            else:
                self.status_queue.put(("progress", 0))
                ok = download_single_video(url, save_path, quality_label, mode,
                                            want_subs, self.log, self.progress_callback)
                self.log("Done." if ok else "Download failed.")

            self.root.after(0, lambda: self.download_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()