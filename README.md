# YouTube Video Downloader (GUI)

A Python/Tkinter app to download YouTube videos or audio, with quality selection, playlist support, subtitles, and a progress bar.

## Technologies Used

- **Python 3**
- **pytubefix** – fetches YouTube video/audio streams and metadata
- **tkinter** – GUI (form, dropdowns, progress bar, log panel)
- **ffmpeg** (via `imageio-ffmpeg`) – merges video+audio streams, extracts MP3
- **subprocess** – runs ffmpeg commands from Python
- **json / os / re / queue / threading** – config storage, filename sanitizing, URL validation, background downloads

## How to Run

1. Install dependencies:
   ```
   pip install pytubefix imageio-ffmpeg
   ```
2. Run the script:
   ```
   python yt.py
   ```
3. In the GUI:
   - Paste or type a YouTube URL, click **Fetch**.
   - Choose a save folder (remembered for next time).
   - Pick a download type: Video (with quality), Audio only, or MP3.
   - Optionally enable subtitle download.
   - Click **Download** and watch the progress bar / log panel.

## How It Works

1. **Fetch** validates the URL and pulls video (or playlist) info via `pytubefix`, populating the quality dropdown.
2. **Download** runs in a background thread so the GUI stays responsive.
3. For video downloads, since high-res streams aren't bundled with audio, the app downloads the chosen video-only stream and the best audio-only stream separately, then merges them with `ffmpeg`.
4. For MP3, only the audio stream is downloaded and converted with `ffmpeg`.
5. For playlists, it loops through every video URL and repeats the process.
6. Temp files are cleaned up after each merge/conversion.
7. Failed downloads are retried up to 3 times before giving up, with clear messages for private/age-restricted/unavailable videos.

## IMAGES

<img width="534" height="543" alt="image" src="https://github.com/user-attachments/assets/b3478f87-07a3-44d0-8d94-9253a9c1ad2f" />



## Features

- Quality selection dropdown (per-resolution video streams)
- Playlist URL support
- Audio-only and MP3 download modes
- English subtitle download (if available)
- Progress bar during download
- Remembers last-used save folder (`config.json`)
- Retry logic on failed downloads
- URL validation before any network call
- Graceful handling of private/age-restricted/live/unavailable videos
- Paste-from-clipboard button for the URL field

## Problems Faced & Solutions

| Problem | Solution |
|---|---|
| `HTTP Error 400: Bad Request` using `pytube` | Switched to `pytubefix`, a maintained fork that keeps up with YouTube's changes. |
| `'NoneType' object has no attribute 'download'` | `get_highest_resolution()` returned `None` because no progressive (video+audio combined) mp4 stream existed. Added a `None` check with a clear message instead of crashing. |
| No progressive stream available at all | Progressive streams cap out around 720p on YouTube. Switched to downloading separate video-only and audio-only streams, then merging with `ffmpeg`. |
| `[WinError 2] The system cannot find the file specified` when merging | `ffmpeg` wasn't installed / not on PATH. Used `imageio_ffmpeg.get_ffmpeg_exe()` instead, which bundles a working binary — no PATH setup needed. |
| Leftover temp files after a failed merge | Added `os.remove()` calls right after each successful merge/conversion to clean up automatically. |
| Terminal `input()` flow was clunky for repeated use | Rebuilt the whole script as a Tkinter GUI form with fields, dropdowns, and a progress bar. |
| GUI freezing during downloads | Moved download/fetch logic into background `threading.Thread`s, with a `queue.Queue` feeding log/progress updates back to the main thread via `root.after()`. |

## What I Learned

- YouTube serves video and audio as **separate streams** above 720p — there's no single progressive download for high quality.
- Why relying on stream-selection methods blindly can fail silently (`None` returned when no matching stream exists) — always check before using the result.
- How to merge separate video/audio tracks and extract audio using `ffmpeg` via `subprocess`.
- How to avoid system-wide `ffmpeg` installs and PATH issues using `imageio-ffmpeg`.
- How to keep a Tkinter GUI responsive during long-running work using threads and a queue instead of blocking the main loop.
- Handling specific failure cases (private, age-restricted, live, unavailable videos) with targeted exception handling instead of one generic catch-all.
- Basic persistence with a small JSON config file for user convenience (remembered folder).
- Sanitizing filenames to strip characters invalid on Windows filesystems.
