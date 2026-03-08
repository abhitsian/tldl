# TLDL

Too Long; Didn't Listen. Transcribe any video to markdown, then chat with it.

Paste a YouTube, Zoom, or any video URL. TLDL downloads the audio, runs Whisper locally, and gives you a timestamped transcript. Summarize it, search it, or ask questions grounded in the transcript and your personal context.

## How it works

1. **yt-dlp** extracts audio from the URL (supports [1000+ sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md))
2. **Whisper** transcribes locally — nothing leaves your machine
3. **Claude** (optional) powers summarization and chat via Claude Code CLI

## Install

```bash
brew install yt-dlp ffmpeg
pip3 install openai-whisper flask

# Optional: for summarize + chat features
# Install Claude Code CLI: https://docs.anthropic.com/en/docs/claude-code

git clone https://github.com/abhitsian/tldl.git
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

Paste a URL, pick a model, hit transcribe. The toolbar gives you:

- **copy** — raw markdown to clipboard
- **download .md** — save the transcript
- **search** — find text in the transcript
- **summarize** — get key points via Claude
- **ask** — chat with the video

### Chat with your video

Click **ask** after transcribing. Ask anything about the video — answers are grounded in the transcript. Multi-turn conversation, so you can dig deeper.

TLDL also reads `~/.tldl/me.md` to ground answers in your context. Edit this file to describe who you are, what you work on, and what you care about:

```markdown
# ~/.tldl/me.md

I'm a backend engineer at a Series B startup.
We run Rails + PostgreSQL, ~50k DAU.
Currently evaluating whether to break into microservices.
```

This means when you ask "how does this apply to my stack?", the answer is actually useful.

### CLI

```bash
tldl "https://www.youtube.com/watch?v=VIDEO_ID"
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

## Library

Every transcript is auto-saved to `~/.tldl/library/`. Your transcripts accumulate over time as a searchable local knowledge base.

```
~/.tldl/
  me.md              # your profile (optional)
  library/
    me_at_the_zoo.md
    quarterly_review.md
    ...
```

## Supported sites

Anything yt-dlp supports: YouTube, Zoom recordings, Vimeo, Twitch VODs, Twitter/X videos, TikTok, and [many more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Requirements

- Python 3.8+
- ffmpeg
- yt-dlp
- openai-whisper
- flask (for web UI)
- Claude Code CLI (optional, for summarize + chat)
