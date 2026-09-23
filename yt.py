from pytubefix import YouTube
import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import imageio_ffmpeg

def download_video(url, save_path):
    try:
        yt = YouTube(url)

        video_stream = (
            yt.streams
            .filter(file_extension="mp4", only_video=True)
            .order_by("resolution")
            .desc()
            .first()
        )
        audio_stream = (
            yt.streams
            .filter(file_extension="mp4", only_audio=True)
            .order_by("abr")
            .desc()
            .first()
        )

        if video_stream is None or audio_stream is None:
            print("Could not find suitable video/audio streams.")
            return

        print(f"Downloading video: {video_stream.resolution}")
        video_file = video_stream.download(output_path=save_path, filename="video_temp.mp4")

        print(f"Downloading audio: {audio_stream.abr}")
        audio_file = audio_stream.download(output_path=save_path, filename="audio_temp.mp4")

        # sanitize filename
        output_file = os.path.join(save_path, "".join(c for c in yt.title if c not in r'\/:*?"<>|') + ".mp4")

        print("Merging video and audio...")
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([
            ffmpeg_path, "-y", "-i", video_file, "-i", audio_file,
            "-c:v", "copy", "-c:a", "aac", output_file
        ], check=True)

        os.remove(video_file)
        os.remove(audio_file)

        print(f"Video downloaded successfully: {output_file}")

    except Exception as e:
        print(f"Error: {e}")

def open_file_dialog():
    folder = filedialog.askdirectory()
    if folder:
        print(f"Selected folder: {folder}")
    return folder

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    video_url = input("Please enter a YouTube url: ")
    save_dir = open_file_dialog()

    if save_dir:
        print("Started download...")
        download_video(video_url, save_dir)
    else:
        print("Invalid save location.")
