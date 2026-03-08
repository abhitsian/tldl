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

### Privacy first

TLDL is designed so your data stays yours.

- **Transcription is 100% local.** Whisper runs on your machine. The audio is downloaded to a temp directory, transcribed, and deleted. Nothing is uploaded to any server.
- **Your profile (`~/.tldl/me.md`) never leaves your machine.** It's read locally and included in prompts to Claude only when you explicitly click summarize or ask. It's never stored remotely, indexed, or shared.
- **Your library (`~/.tldl/library/`) is plain markdown files on disk.** No database, no cloud sync, no telemetry. You own the files. `cat` them, `grep` them, back them up however you want.
- **No accounts, no API keys, no sign-ups.** Transcription works with zero configuration. Summarize and chat work through your existing Claude Code CLI auth — no separate API key to manage.

### Claude Code CLI as the backend

TLDL doesn't call the Anthropic API directly. It shells out to [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude --print`).

Why this matters:

- **No API key management.** If you have Claude Code installed and authenticated, TLDL just works. No `.env` files, no key rotation, no billing surprises from a leaked key.
- **You use your existing Claude subscription.** No separate billing. No middleman service taking a cut.
- **Model selection is flexible.** TLDL uses `claude --print --model sonnet` by default — fast and cheap. You can change this in the code to use any model Claude Code supports.
- **It's a pattern, not a dependency.** Any tool that accepts stdin and returns stdout could replace Claude here. Want to use a local model instead? Swap one subprocess call.

### Peek under the hood

The entire tool is two Python files. No framework, no build step, no infrastructure.

**`tldl`** (CLI entry point, ~170 lines)
- Parses args, downloads audio via `yt-dlp -x --audio-format wav`, runs `whisper.load_model().transcribe()`, formats segments into timestamped markdown. That's it.

**`app.py`** (Web UI + API, ~700 lines)
- Flask server with 4 endpoints:
  - `POST /api/transcribe` — kicks off a background thread that downloads + transcribes. Returns a job ID.
  - `GET /api/status/<id>` — poll for progress. Returns `running`, `done`, or `error` with the transcript.
  - `POST /api/summarize` — pipes transcript to `claude --print` with a summarization prompt.
  - `POST /api/chat` — builds a prompt from: system instructions + `~/.tldl/me.md` + transcript + conversation history. Pipes it to `claude --print`. Returns the response.
- The HTML/CSS/JS is inlined in a single template string. No React, no npm, no build. Open `view-source:` and read the whole frontend in 5 minutes.
- Transcripts auto-save to `~/.tldl/library/` as plain `.md` files.

**The chat prompt structure:**

```
System: You are helping the user understand a video they watched.
Answer questions grounded in the transcript below.
Be concise and direct. Use markdown formatting.
When relevant, connect ideas to the user's background.

Here is who the user is:
{contents of ~/.tldl/me.md}

Here is the transcript:
{full transcript}

User: What was their main argument?
Assistant: ...
User: How does this apply to my project?
Assistant: ...
```

The profile and transcript are included in every turn. Conversation history accumulates so follow-up questions work naturally. No embeddings, no vector DB, no RAG — just a well-structured prompt with the right context.

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
