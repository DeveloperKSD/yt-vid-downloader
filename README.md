# YouTube Video Downloader

A simple Python script to download YouTube videos in the highest available quality, with a GUI folder picker for save location.

## Technologies Used

- **Python 3**
- **pytubefix** – fetches YouTube video/audio streams
- **tkinter** – native GUI dialog for selecting the download folder
- **ffmpeg** (via `imageio-ffmpeg`) – merges separate video and audio streams into one file
- **subprocess** – runs ffmpeg commands from Python
- **os** – file handling and cleanup

## How to run

'''bash
pdad
'''


## How It Works

1. User enters a YouTube URL and picks a save folder via a file dialog.
2. The script fetches the video using `pytubefix`.
3. Since high-resolution YouTube videos (1080p+) don't come as a single combined file, it separately downloads:
   - the best available **video-only** stream
   - the best available **audio-only** stream
4. `ffmpeg` merges these two temp files into a single `.mp4`.
5. Temp files are deleted, leaving just the final merged video.

## What I Learned

- YouTube serves video and audio as **separate streams** above 720p — there's no single progressive download for high quality.
- Why relying on `get_highest_resolution()` blindly can fail silently (`None` returned when no matching stream exists).
- How to merge separate video/audio tracks using `ffmpeg` via `subprocess`.
- How to avoid system-wide `ffmpeg` installs and PATH issues using `imageio-ffmpeg`, which bundles a working binary.
- Basic error handling patterns to catch and surface real failure reasons instead of generic crashes.
- Sanitizing filenames to strip characters invalid on Windows filesystems.
