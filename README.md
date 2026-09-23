# YouTube Video Downloader

A simple Python script to download YouTube videos in the highest available quality, with a GUI folder picker for save location.

## Technologies Used

- **Python 3**
- **pytubefix** – fetches YouTube video/audio streams
- **tkinter** – native GUI dialog for selecting the download folder
- **ffmpeg** (via `imageio-ffmpeg`) – merges separate video and audio streams into one file
- **subprocess** – runs ffmpeg commands from Python
- **os** – file handling and cleanup

## How to Run

1. Install dependencies:
   ```
   pip install pytubefix imageio-ffmpeg
   ```
2. Run the script:
   ```
   python yt.py
   ```
3. Enter the YouTube URL when prompted.
4. Select a save folder in the dialog box that pops up.
5. Wait for it to download video + audio and merge them — the final `.mp4` will appear in your chosen folder.

## How It Works

1. User enters a YouTube URL and picks a save folder via a file dialog.
2. The script fetches the video using `pytubefix`.
3. Since high-resolution YouTube videos (1080p+) don't come as a single combined file, it separately downloads:
   - the best available **video-only** stream
   - the best available **audio-only** stream
4. `ffmpeg` merges these two temp files into a single `.mp4`.
5. Temp files are deleted, leaving just the final merged video.

## Problems Faced & Solutions

| Problem | Solution |
|---|---|
| `HTTP Error 400: Bad Request` using `pytube` | Switched to `pytubefix`, a maintained fork that keeps up with YouTube's changes. |
| `'NoneType' object has no attribute 'download'` | `get_highest_resolution()` returned `None` because no progressive (video+audio combined) mp4 stream existed for the video. Added a `None` check to fail with a clear message instead of crashing. |
| No progressive stream available at all | Progressive streams cap out around 720p on YouTube. Switched to downloading separate video-only and audio-only streams, then merging with `ffmpeg`. |
| `[WinError 2] The system cannot find the file specified` when merging | `ffmpeg` wasn't installed / not on system PATH. Instead of a manual install, used `imageio-ffmpeg`, which bundles a working `ffmpeg` binary and exposes its path directly — no PATH setup needed. |
| Leftover temp files (`video_temp.mp4`, `audio_temp.mp4`) after a failed merge | Once `ffmpeg` merging succeeded, added `os.remove()` calls right after the merge step to clean up temp files automatically. |

## What I Learned

- YouTube serves video and audio as **separate streams** above 720p — there's no single progressive download for high quality.
- Why relying on `get_highest_resolution()` blindly can fail silently (`None` returned when no matching stream exists).
- How to merge separate video/audio tracks using `ffmpeg` via `subprocess`.
- How to avoid system-wide `ffmpeg` installs and PATH issues using `imageio-ffmpeg`, which bundles a working binary.
- Basic error handling patterns to catch and surface real failure reasons instead of generic crashes.
- Sanitizing filenames to strip characters invalid on Windows filesystems.


<img width="1782" height="806" alt="image" src="https://github.com/user-attachments/assets/881e967e-f183-4c5e-983f-e24a7334b01d" />
<img width="1781" height="804" alt="image" src="https://github.com/user-attachments/assets/247bc977-ed02-4b9b-bdb8-86df68ec791d" />

