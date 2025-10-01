# Lynecode

```text
    ██╗  ██╗   ██╗███╗   ██╗███████╗     ██████╗ ██████╗ ██████╗ ███████╗
    ██║  ╚██╗ ██╔╝████╗  ██║██╔════╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
    ██║   ╚████╔╝ ██╔██╗ ██║█████╗      ██║     ██║   ██║██║  ██║█████╗  
    ██║    ╚██╔╝  ██║╚██╗██║██╔══╝      ██║     ██║   ██║██║  ██║██╔══╝  
    ███████╗██║   ██║ ╚████║███████╗    ╚██████╗╚██████╔╝██████╔╝███████╗
    ╚══════╝╚═╝   ╚═╝  ╚═══╝╚══════╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
```

Lynecode is an AI coding assistant from LyneLabs. It brings a fast terminal UI, built-in project indexing, an opinionated toolset, and optional AI models (OpenAI, Gemini, Azure OpenAI) with your keys. Run it on any folder and work from a powerful chat workflow.

## Why Lynecode is different
- Integrated version control safety net: Lyne maintains its own backup snapshots (`time_machine` in your target path). You can explore diffs and restore changes without relying solely on git.
- Built-in analyzers and guards: Bug and code quality analyzers help spot issues quickly (without exposing internal implementation). Optional static checks are available via extras.
- Context-rich workflow: Attach files/folders inline, fuzzy-find by name, and navigate conversations with a clear menu.
- Model agnostic: Bring your own keys for OpenAI, Google Gemini, or Azure OpenAI and switch models on the fly.

## Installation
```bash
pip install lynecode
```

Python 3.9+ is recommended.

## Quick start
- Run on a specific path:
```bash
lynecode "D:/projects/myrepo"
```

- Or from your current working directory (Lynecode resolves to an absolute path):
```bash
lynecode
```

## Basic usage
Once launched, you’ll see a banner and a prompt. Type your request or use the in-app menus:
- Show navigation menu: `/menu`
- Help: `/help`
- Switch conversations: `/chats`
- Model settings: `/model` or `/switch <model>`
- Quit: `quit`

### Attach files/folders inline
- Attach a file: add `/file:<name_or_term>` inside your message
- Attach a folder: add `/folder:<name_or_term>` inside your message
Lynecode will fuzzy-match and help you pick the right target, then keep attachments visible after responses.

## Choosing and switching models
- Open the model menu from navigation (`/menu` → “Model Settings”) or run `/model`.
- Switch directly with `/switch <model_name>`.
- The default model is used if configured.

Supported providers (bring your own keys):
- OpenAI (e.g., `gpt-4.1`, `gpt-5`)
- Google Gemini (e.g., `gemini-2.5-flash`, `gemini-2.5-pro`, with optional “-thinking” variants)
- Azure OpenAI (your deployment name)
- OpenRouter (e.g., `x-ai/grok-4-fast:free`, `openai/gpt-4o` via OpenRouter)

## Configure API keys (secure, menu-driven)
Launch the API Configuration from the navigation menu:
- `/menu` → “API Configuration”

Follow prompts to set keys:
- OpenAI: API key (`sk-...`)
- Gemini: API key
- Azure OpenAI: API key, endpoint, API version (optional), and deployment name

Keys are stored securely via Lynecode’s config manager and masked in the UI.

**Note:** After updating any API key or provider configuration, restart Lynecode to apply changes.

## Built-in version control workflow
Lynecode automatically creates a hidden `time_machine` folder inside the target directory. It’s your safety-net:
- Auto snapshots around operations
- View diffs and restore via the Version Control menu
- Works even if the target folder is not a git repo

Open from navigation:
- `/menu` → “Version Control”

## Feature highlights
- Intelligent file edits (create/replace/delete blocks)
- Project-wide searching (grep/AST-backed and fuzzy indexing)
- Web reading and search helpers
- Conversation history with attachments
- Rich terminal output where supported; plain fallback otherwise

## Compare: Lynecode vs Cline/Gemini CLI
- Safety first: Lynecode’s built-in snapshotting means quick rollback without external VCS.
- Deep project tooling: File block edits, AST/grep, and fuzzy search integrated in one place.
- Menu-driven UX: Rich menus for models, API setup, attachments, version control.
- Provider-agnostic: Switch between OpenAI, Gemini, or Azure OpenAI at runtime.

## Troubleshooting
- If terminal colors aren’t showing, Lynecode falls back to plain text automatically.
- Ensure your API keys are valid (placeholders are detected and blocked with helpful messages).

## Uninstall
```bash
pip uninstall lynecode
```
