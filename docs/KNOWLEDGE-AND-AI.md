# FIELD//OS Offline Knowledge + ASSIST

## Knowledge layout

FIELD//OS indexes bundled entries plus operator-selected local text trees. Local folders automatically become categories:

```text
~/knowledge/
├── medical/
├── navigation/
├── radio/
├── communications/
├── repair/
├── survival/
├── computing/
├── networking/
├── manuals/
└── raven/
```

Point FIELD//OS at the root:

```bash
export FIELDOS_KNOWLEDGE_PATHS="$HOME/knowledge"
```

Supported lightweight index formats are Markdown, text, RST, YAML and JSON. Large encyclopedia/manual collections can remain in Kiwix/ZIM and companion map/document applications rather than being copied into the in-memory text index.

The knowledge API supports category listing, category filtering, full-text search and compact context retrieval for the local AI assistant.

## ASSIST

`fieldos.offline_ai.OfflineAI` is the first local inference adapter. It talks to an operator-controlled Ollama-compatible endpoint and defaults to loopback (`127.0.0.1`).

Design rules:

- offline/local by default
- model is optional and FIELD//OS boots without it
- no automatic model downloads
- no command execution from model output
- no automatic radio/network actions
- no automatic evidence changes
- local knowledge can be supplied as retrieval context
- model and endpoint are configured by environment variables

```bash
export FIELDOS_AI_URL='http://127.0.0.1:11434'
export FIELDOS_AI_MODEL='qwen2.5:1.5b'
```

A small quantised model is the intended RVN-01 starting point. Model selection should be validated on the physical Pi for latency, RAM use and thermals before a larger model is adopted.
