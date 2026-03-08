# TLDL

Too Long; Didn't Listen. Transcribe any video to markdown — from the terminal or a web UI.

Paste a YouTube, Zoom, or any video URL. TLDL downloads the audio, runs OpenAI Whisper locally, and gives you a timestamped transcript. Hit summarize to get key points via Claude.

## How it works

1. **yt-dlp** extracts audio from the URL (supports [1000+ sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md))
2. **Whisper** transcribes locally on your machine — nothing leaves your computer
3. **Claude** (optional) summarizes the transcript via the Claude Code CLI

## Install

```bash
# Dependencies
brew install yt-dlp ffmpeg
pip3 install openai-whisper flask

# Optional: for the summarize feature
# Install Claude Code CLI: https://docs.anthropic.com/en/docs/claude-code

# Clone
git clone https://github.com/vaibhavbafna5/tldl.git
cd tldl
chmod +x tldl
```

Add to your PATH:

```bash
export PATH="/path/to/tldl:$PATH"
```

## Usage

### Web UI

```bash
tldl --web
# Opens at http://localhost:4983
```

Paste a URL, pick a model, hit transcribe. Use the toolbar to copy, download, search, or summarize.

### CLI

```bash
# Basic
tldl "https://www.youtube.com/watch?v=VIDEO_ID"

# With options
tldl "https://zoom.us/rec/share/..." --password "abc123"
tldl "https://youtu.be/xyz" --model medium --output notes.md
```

### Options

| Flag | Description |
|------|-------------|
| `--model`, `-m` | Whisper model: `tiny`, `base` (default), `small`, `medium`, `large`, `turbo` |
| `--password`, `-p` | Video password (Zoom, etc.) |
| `--output`, `-o` | Output file path |
| `--web`, `-w` | Launch web UI |

### Models

| Model | Speed | Accuracy | Size |
|-------|-------|----------|------|
| tiny | Fastest | Lower | 39M |
| base | Fast | Good | 74M |
| small | Medium | Better | 244M |
| medium | Slow | Great | 769M |
| large | Slowest | Best | 1.5G |
| turbo | Fast | Great | 809M |

## Supported sites

Anything yt-dlp supports: YouTube, Zoom recordings, Vimeo, Twitch VODs, Twitter/X videos, TikTok, and [many more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Requirements

- Python 3.8+
- ffmpeg
- yt-dlp
- openai-whisper
- flask (for web UI)
- Claude Code CLI (optional, for summarization)
