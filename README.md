<div align="center">

<h1>⚡ SignalScope</h1>

<p><strong>Cut through the noise. Surface what matters.</strong></p>

<p>
  SignalScope is a terminal-first intelligence tool that fetches content from technical sources,
  filters it by your interests, and uses an LLM of your choice to rank, summarize,
  and deliver only the signals worth your attention — in clean Markdown.
</p>

<br/>

<p>
  <a href="./README.es.md">🌐 Versión en Español</a>
</p>

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)
![LLM Support](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Anthropic%20%7C%20Ollama-a855f7?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-blue?style=flat-square)

</div>

---

## What It Does

Every day, dozens of technical articles, posts, and threads compete for your attention.
SignalScope connects to your configured sources, pulls the latest content, and runs it through a
pipeline that filters by topic, scores by relevance, and classifies each item as `critical`,
`important`, or `optional` — so you know exactly where to look first.

The output is a structured Markdown report, saved locally, ready to read.

---

## How It Works

```
Sources → Research → Filter → LLM → Ranked Report
```

1. **Sources** — Registered data providers (e.g. Hacker News) are queried concurrently.
2. **Research** — Raw items are fetched asynchronously via HTTP.
3. **Filter** — Items are narrowed down by your configured technologies and topics.
4. **LLM** — Each item is sent to your chosen provider (OpenAI, Anthropic, or Ollama) for summarization and priority classification.
5. **Output** — A clean `.md` file is saved to `/output/` with all items ranked and formatted.

---

## Supported LLM Providers

| Provider  | Requires Key | Local |
|-----------|:------------:|:-----:|
| OpenAI    | ✅           | ❌    |
| Anthropic | ✅           | ❌    |
| Ollama    | ❌           | ✅    |

---

## Priority Levels

Each item processed by the LLM receives one of three priority labels:

| Level      | Meaning |
|------------|---------|
| `critical` | Requires immediate attention — breaking changes, active exploits, major incidents |
| `important`| Highly relevant to your work — worth reading today |
| `optional` | Informational or experimental — read when you have time |

Priority rules adjust automatically based on the `mode` you configure (`dev` or `security`).

---

## Installation & Usage Guide

### Prerequisites

- Python **3.11** or higher
- `pip` package manager
- An API key for OpenAI or Anthropic (not required for Ollama)

---

### Linux / macOS

**1. Clone the repository**

```bash
git clone https://github.com/CesarManzoCode/SignalScope.git
cd SignalScope
```

**2. Create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set up environment variables**

```bash
cp .env.example .env
```

Open `.env` with your editor and fill in your API keys:

```bash
nano .env
# or
code .env
```

**5. Configure your preferences**

Edit `src/config/user_config.json` to match your interests:

```bash
nano src/config/user_config.json
```

**6. Run SignalScope**

```bash
cd src
python main.py
```

---

### Windows

**1. Clone the repository**

```powershell
git clone https://github.com/CesarManzoCode/SignalScope.git
cd SignalScope
```

**2. Create and activate a virtual environment**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

> If you get an execution policy error, run first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**3. Install dependencies**

```powershell
pip install -r requirements.txt
```

**4. Set up environment variables**

```powershell
copy .env.example .env
notepad .env
```

**5. Configure your preferences**

```powershell
notepad src\config\user_config.json
```

**6. Run SignalScope**

```powershell
cd src
python main.py
```

---

### Configuration Reference

`src/config/user_config.json` controls what SignalScope fetches and how it behaves:

```json
{
  "mode": "dev",
  "llm": {
    "provider": "openai"
  },
  "technologies": ["python", "ai", "backend"],
  "topics": ["security", "llms"],
  "sources": {
    "include": [],
    "exclude": []
  },
  "priority": {
    "prefer_high_score": true,
    "prefer_recent": true
  },
  "output": {
    "format": "markdown"
  }
}
```

| Field            | Options                          | Description                                      |
|------------------|----------------------------------|--------------------------------------------------|
| `mode`           | `"dev"`, `"security"`            | Adjusts LLM priority rules for your use case     |
| `llm.provider`   | `"openai"`, `"anthropic"`, `"ollama"` | Which LLM backend to use                    |
| `technologies`   | Any string list                  | Keywords used to filter content by tech stack    |
| `topics`         | Any string list                  | Topics of interest (e.g. `"security"`, `"llms"`) |
| `prefer_high_score` | `true` / `false`              | Prioritize highly-scored community content       |
| `prefer_recent`  | `true` / `false`                 | Favor recently published items                   |
| `output.format`  | `"markdown"`                     | Output format (Markdown is the default)          |

---

### Environment Variables Reference

`.env` controls API access:

```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OLLAMA_URL=http://localhost:11434
DEFAULT_MODEL=gpt-4.1-mini
```

> For Ollama, no API key is required. Just make sure the Ollama server is running locally before executing SignalScope.

---

## Output

Each run saves a structured Markdown file to the `output/` directory.
Every item includes a **Summary**, **Key Points**, **Details**, and its assigned **Priority**.

```
output/
└── example.md
```

---

## Project Structure

```
SignalScope/
├── src/
│   ├── main.py                        # Entry point
│   ├── config/
│   │   ├── user_config.json           # User preferences
│   │   ├── user_config.py             # Config loader
│   │   ├── prompts/                   # LLM prompt builders
│   │   └── protocols/                 # Priority ranking logic
│   ├── core/
│   │   └── types/                     # Domain types (RawItem, FinalItem, etc.)
│   ├── infrastructure/
│   │   ├── llm_clients/               # OpenAI, Anthropic, Ollama adapters
│   │   └── sources/                   # Data source clients (Hacker News, etc.)
│   ├── modules/
│   │   ├── source_selector/           # Selects active sources from config
│   │   ├── research/                  # Async data fetching
│   │   ├── filter/                    # Content filtering pipeline
│   │   ├── llm/                       # LLM orchestration
│   │   └── converter/                 # Output format conversion
│   └── formatters/
│       └── markdown_formatter.py      # Markdown output formatter
├── output/                            # Generated reports
├── .env.example                       # Environment variable template
├── requirements.txt
└── README.md
```

---

## License

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for details.
