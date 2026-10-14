# hermes-viewport — Design Spec

**Status:** Draft v0.1
**Surface:** Browser/WebGPU rendering target driven by Hermes as a first-class agent surface
**Canonical frame:** 9:16 portrait (mobile)

---

## 1. Surface Registration

`hermes viewport` is a first-class subcommand alongside `hermes browser`, `hermes desktop`, `hermes gui`.

```bash
hermes viewport start          # launch 9:16 viewport with WebLLM bridge
hermes viewport stop           # teardown
hermes viewport status         # current state (model, tokens, latency, frame)
hermes viewport screenshot     # capture current frame
```

The viewport registers as an MCP server so any MCP client can drive it:

```bash
hermes mcp add --command "hermes viewport serve" --name viewport
```

---

## 2. Canonical Frame — 9:16

| Property | Value |
|----------|-------|
| Aspect ratio | 9:16 (portrait) |
| Reference resolution | 375×812 (iPhone logical) |
| Alt resolution | 430×932 (iPhone Pro Max logical) |
| DPR | 2–3 (device-dependent) |
| Orientation | Portrait (locked) |
| Input | Touch (tap ≥44px, swipe, long-press) |
| Layout | Single-column, bottom-sheet modals, sticky header |

The frame is the **portable configuration** — the most-used human-in-loop surface. Desktop browser windows are a secondary target, not the primary.

---

## 3. WebLLM.js Bridge

The viewport loads WebLLM.js in a real browser context (Chrome/Edge with WebGPU). The bridge exposes inference as an MCP tool.

### Model constraints (mobile)

| Constraint | Value |
|------------|-------|
| Parameter count | 0.5B–3B (Qwen2.5-0.5B/1.5B, Phi-3-mini, SmolLM2) |
| Backend | WebGPU primary, WASM fallback |
| Context window | 4K tokens max |
| Quantization | 4-bit minimum |
| Offline | Yes — model cached in IndexedDB after first load |

### MCP tool: `webllm.infer`

```typescript
interface WebLLMInferParams {
  prompt: string;
  model?: string;           // default: "Qwen2.5-0.5B-Instruct-q4f16_1"
  maxTokens?: number;       // default: 512
  temperature?: number;     // default: 0.7
  systemPrompt?: string;    // default: "You are a helpful assistant."
}

interface WebLLMInferResult {
  text: string;
  tokens: { prompt: number; completion: number; total: number };
  latencyMs: number;
  model: string;
  backend: "webgpu" | "wasm";
  receipt: string;          // SHA-256 of (model + prompt + response + timestamp)
}
```

### MCP tool: `webllm.status`

```typescript
interface WebLLMStatus {
  loaded: boolean;
  model: string | null;
  backend: "webgpu" | "wasm" | null;
  memoryUsageMB: number | null;
  lastInferenceMs: number | null;
  receiptChain: string[];   // last N receipt hashes
}
```

---

## 4. Viewport State

The viewport maintains a renderable state that the agent can inspect and manipulate.

### MCP tools

| Tool | Signature | Purpose |
|------|-----------|---------|
| `viewport.render` | `(html: string) => void` | Render HTML in the 9:16 frame |
| `viewport.screenshot` | `() => { png: string; width: number; height: number }` | Capture current frame |
| `viewport.tap` | `(x: number, y: number) => void` | Touch interaction |
| `viewport.swipe` | `(dir: "up"\|"down"\|"left"\|"right", distance?: number) => void` | Scroll/swipe gesture |
| `viewport.input` | `(text: string) => void` | Text entry into focused element |
| `viewport.scroll` | `(x: number, y: number) => void` | Absolute scroll position |
| `viewport.dom` | `() => { title: string; url: string; elements: DOMElement[] }` | Current DOM snapshot |

### Viewport layout (9:16)

```
┌─────────────────┐
│  hermes-viewport │  ← sticky header (model status, backend)
│  ┌───────────┐  │
│  │  agent    │  │  ← chat/response area (scrollable)
│  │  response │  │
│  └───────────┘  │
│  ┌───────────┐  │
│  │  WebLLM   │  │  ← inference status (tokens, latency, receipt)
│  │  status   │  │
│  └───────────┘  │
│  [input] [send] │  ← bottom input bar (sticky)
└─────────────────┘
```

---

## 5. Receipt Schema

Every inference produces a receipt — a hash chain for provenance.

```typescript
interface ViewportReceipt {
  version: 1;
  timestamp: string;        // ISO 8601
  model: string;
  backend: "webgpu" | "wasm";
  promptHash: string;       // SHA-256 of prompt
  responseHash: string;     // SHA-256 of response
  tokens: { prompt: number; completion: number };
  latencyMs: number;
  prevReceipt: string | null;  // hash chain
  hash: string;             // SHA-256 of all above fields
}
```

Receipts are stored in `~/.hermes/viewport/receipts.jsonl` (append-only).

---

## 6. Credential Gate

No external API keys. Local-only, sovereign.

- WebLLM.js runs entirely in-browser
- Model weights cached in IndexedDB (first load downloads, subsequent loads are offline)
- No telemetry, no external calls
- Receipts are local provenance, not remote attestation

---

## 7. Architecture

```
┌─────────────────────────────────────┐
│           Hermes Agent              │
│  ┌──────────┐  ┌──────────────────┐ │
│  │  agent   │  │  hermes-viewport │ │
│  │  loop    │◄─┤  MCP server      │ │
│  └──────────┘  └────────┬─────────┘ │
└─────────────────────────┼───────────┘
                          │ MCP protocol
                          ▼
               ┌─────────────────────┐
               │  Browser (9:16)     │
               │  ┌───────────────┐  │
               │  │  WebLLM.js    │  │
               │  │  (WebGPU)     │  │
               │  └───────────────┘  │
               │  ┌───────────────┐  │
               │  │  Viewport UI  │  │
               │  │  (HTML/Canvas)│  │
               │  └───────────────┘  │
               └─────────────────────┘
```

---

## 8. Implementation Phases

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| 1 | MCP server skeleton + `webllm.status` | None |
| 2 | WebLLM.js bridge + `webllm.infer` | Phase 1 |
| 3 | Viewport render + screenshot + DOM tools | Phase 1 |
| 4 | Receipt chain + `~/.hermes/viewport/receipts.jsonl` | Phase 2 |
| 5 | Touch input (tap, swipe, input) | Phase 3 |
| 6 | Model caching + offline mode | Phase 2 |
| 7 | `hermes viewport` CLI subcommand | Phase 1–6 |

---

## 9. Open Questions

1. **WebLLM.js version** — current stable is 0.2.x; confirm WebGPU support matrix for target devices
2. **Model hosting** — Hugging Face CDN vs local mirror vs IPFS
3. **Receipt verification** — local hash chain is sufficient, or need remote attestation?
4. **Multi-viewport** — can one Hermes instance drive multiple 9:16 frames (e.g. phone + tablet)?
5. **ACP integration** — should the viewport be drivable from VS Code via `hermes acp`?
