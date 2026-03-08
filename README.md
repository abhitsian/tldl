# TLDL

**Too Long; Didn't Listen.**

Transcribe any video. Summarize it. Chat with it — grounded in *your* context.

---

## Why TLDL?

Every transcription tool gives you a wall of text. TLDL gives you a **conversation**.

You watch a 45-minute talk on system design. You don't need 12 pages of transcript. You need answers: *"What was their take on read replicas?" "How does this compare to what we're doing?" "What should I steal from this?"*

TLDL lets you **ask questions about any video**, and grounds the answers in two things:

1. **The transcript** — what was actually said
2. **Your context** — who you are, what you work on, what you care about

A simple file (`~/.tldl/me.md`) tells TLDL about you. A backend engineer gets different answers than a product manager watching the same talk. That's the difference between a transcription tool and a thinking tool.

### What makes it different

| Feature | YouTube Transcripts | Otter.ai / Fireflies | TLDL |
|---------|-------------------|---------------------|------|
| Works with any video URL | No | Limited | Yes (1000+ sites) |
| Runs locally (private) | N/A | No | Yes |
| No account / no subscription | Yes | No | Yes |
| Summarization | No | Yes | Yes |
| Chat with transcript | No | Limited | Yes |
| Grounded in your context | No | No | **Yes** |
| CLI + Web UI | No | No | Yes |
| Free | Yes | No | Yes |

---

## Quick start

```bash
# Install dependencies
brew install yt-dlp ffmpeg
pip3 install openai-whisper flask

# Clone
git clone https://github.com/abhitsian/tldl.git
cd tldl
chmod +x tldl

# Run
./tldl --web
```

Opens at [http://localhost:4983](http://localhost:4983).

For summarize and chat features, install [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code).

---

## Usage

### Web UI

```bash
tldl --web
```

1. Paste any video URL
2. Pick a Whisper model (tiny → large)
3. Hit **transcribe**
4. Use the toolbar:
   - **copy** — markdown to clipboard
   - **download .md** — save the file
   - **search** — find text in the transcript
   - **summarize** — key points via Claude
   - **ask** — chat with the video

### CLI

```bash
# Transcribe a YouTube video
tldl "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Zoom recording with password
tldl "https://zoom.us/rec/share/..." --password "abc123"

# Better accuracy with a larger model
tldl "https://youtu.be/xyz" --model medium

# Custom output path
tldl "https://youtu.be/xyz" --output meeting.md
```

### Options

| Flag | Description |
|------|-------------|
| `--model`, `-m` | `tiny`, `base` (default), `small`, `medium`, `large`, `turbo` |
| `--password`, `-p` | Video password (Zoom, etc.) |
| `--output`, `-o` | Output file path |
| `--web`, `-w` | Launch web UI |

---

## Set up your context

Create `~/.tldl/me.md` to personalize answers. This file is never uploaded anywhere — it stays on your machine and is read by Claude when you ask questions.

```bash
mkdir -p ~/.tldl
cat > ~/.tldl/me.md << 'EOF'
# About me

I'm a backend engineer at a Series B startup.
We run Rails + PostgreSQL, ~50k DAU.
Currently evaluating whether to break into microservices.
I care about practical, boring technology choices.
EOF
```

Now when you watch a talk on microservices and ask *"should I do this?"*, the answer accounts for your stack, your scale, and your preferences.

**More context = better answers.** Include your role, tech stack, current projects, what you care about, how you think.

---

## How it works

```
Video URL
    │
    ▼
┌──────────┐
│  yt-dlp  │ ── extracts audio (supports 1000+ sites)
└──────────┘
    │
    ▼
┌──────────┐
│ Whisper  │ ── transcribes locally (nothing leaves your machine)
└──────────┘
    │
    ▼
┌──────────────────────────────────────┐
│         Timestamped Markdown         │
│  ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │  copy  │ │summary │ │   ask    │ │
│  └────────┘ └────────┘ └──────────┘ │
│                              │       │
│                    ┌─────────┘       │
│                    ▼                 │
│              ┌───────────┐           │
│              │  Claude   │           │
│              │ + me.md   │           │
│              │ + history │           │
│              └───────────┘           │
└──────────────────────────────────────┘
```

- **Transcription** is 100% local via Whisper. No data sent anywhere.
- **Summarize** and **Ask** use Claude Code CLI. Your transcript and context are sent to Claude for processing.
- **Library** — every transcript auto-saves to `~/.tldl/library/` so they accumulate over time.

---

## Whisper models

| Model | Speed | Accuracy | Size |
|-------|-------|----------|------|
| tiny | Fastest | Lower | 39M |
| base | Fast | Good | 74M |
| small | Medium | Better | 244M |
| medium | Slow | Great | 769M |
| large | Slowest | Best | 1.5G |
| turbo | Fast | Great | 809M |

Use `tiny` for quick-and-dirty. Use `medium` or `turbo` when accuracy matters.

---

## Supported sites

Anything [yt-dlp supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md): YouTube, Zoom, Vimeo, Twitch, Twitter/X, TikTok, Loom, and 1000+ more.

---

## File structure

```
~/.tldl/
├── me.md           # your context (optional, never shared)
└── library/        # auto-saved transcripts
    ├── meeting_standup.md
    ├── tech_talk_scaling.md
    └── ...
```

---

## Requirements

- Python 3.8+
- ffmpeg
- yt-dlp
- openai-whisper
- flask
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (optional — for summarize + chat)

---

## Use cases

- **Meeting recordings** — transcribe Zoom calls, search for decisions, ask "what were the action items?"
- **Tech talks** — watch at 2x, then ask questions grounded in your stack
- **Podcasts** — turn audio into searchable, queryable text
- **Lectures** — study by chatting with the content instead of re-watching
- **Research** — transcribe interviews, extract themes, ask follow-ups

---

## License

MIT
