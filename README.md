# youtubetomp3

Small Flask app for batch-converting links to mp3/mp4, plus a Spotify-playlist screenshot flow: screenshot a playlist, OCR pulls the track list, and each track is searched and downloaded.

## Features

- **Batch URL convert** — paste one or more YouTube (or other yt-dlp-supported) links, one per line, choose mp3 or mp4, download all in parallel (`ThreadPoolExecutor`, 4 workers).
- **Spotify screenshot → download** — upload a screenshot of a playlist, Tesseract OCR extracts title/artist pairs, each track is searched (`ytsearch1:`) and pulled down as mp3.
- Audio extracted via `yt_dlp` + `FFmpegExtractAudio` (192kbps mp3); video merged to mp4 via `FFmpegVideoConvertor`.

## Requires

- Python 3, `ffmpeg` on PATH
- Tesseract OCR on PATH (only needed for the screenshot flow — `pytesseract` + `Pillow`)

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Routes

| Route | Method | Does |
|---|---|---|
| `/` | GET | UI |
| `/convert` | POST | `{urls, format}` → batch mp3/mp4 download |
| `/parse-screenshot` | POST | image → OCR'd raw text |
| `/spotify-convert` | POST | `{songs: [{title, artist}]}` → batch mp3 search + download |
| `/download/<filename>` | GET | fetch a converted file |

Downloaded files land in `downloads/` (gitignored).
