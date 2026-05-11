# CascadeAI

**Closing the 120-day gap between when a crisis starts cascading and when the world responds.**

> Built for the [Gemma 4 Good Hackathon](https://kaggle.com/competitions/gemma-4-good-hackathon) · Global Resilience Track · Powered by Gemma 4

---

## The Problem

In 2022, Russia invaded Ukraine. Within hours, wheat exports halted, fertilizer supply was severed, and shipping lanes were disrupted. Yet the world took **120 days** to connect these dots to bread prices in Kenya. By then, 47 million people were food insecure.

Today, **318 million people** face crisis-level hunger — double the number from 2019. Sudan's civil war has cascaded into the world's largest humanitarian crisis. Middle East conflict has driven fertilizer prices up 46% in a single month, devastating planting seasons across Sub-Saharan Africa.

These are not isolated crises. They are **cascades** — where a conflict in one region destroys food systems, health infrastructure, and livelihoods thousands of miles away.

**CascadeAI closes that gap.** It predicts how a single event ripples through energy, food, health, and displacement systems — hours after a crisis begins, not months later.

---

## What CascadeAI Does

Given a trigger event (a conflict, climate shock, or economic disruption), CascadeAI:

1. **Detects** the crisis type and severity from natural language using Gemma 4
2. **Propagates** impacts through a weighted cascade graph (BFS across energy → fertilizer → crop → food → health → displacement)
3. **Profiles** each affected country's vulnerability (food import dependency, health infrastructure, displacement capacity)
4. **Generates** tailored response narratives for different stakeholders — WHO, WFP, UNHCR, community leaders — in their local language
5. **Backtests** predictions against historical crises to validate accuracy

### Validated on Real Crises

| Scenario | CascadeAI Prediction | Actual Outcome | Accuracy |
|---|---|---|---|
| Ukraine 2022 — Kenya food price | +40–55% increase | +53% increase | ✓ |
| Ukraine 2022 — Egypt wheat shortage | Critical shortage in 60–90 days | Shortage in 75 days | ✓ |
| Sudan 2023 — Displacement | 12–16M displaced | 14M displaced | ✓ |
| Hormuz 2026 — Fertilizer price | +35–50% surge | +46% surge | ✓ (live) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: FRONTEND (Streamlit + Folium maps)                │
│  Cascade visualization · Backtest explorer · Narratives     │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: GEMMA 4 AGENTS                                    │
│  EventDetector · ImpactPredictor · NarrativeGenerator       │
│  VisionAnalyst · Dispatcher · Orchestrator                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: DETERMINISTIC CORE (pure Python — runs anywhere)  │
│  CascadeGraph (BFS) · Country Profiles · Data Fetchers      │
│  Crisis Replay Engine · Compound BFS · FastAPI Backend      │
└─────────────────────────────────────────────────────────────┘
```

### Gemma 4 Integration Points

| Capability | Where Used |
|---|---|
| **Function calling** | `EventDetector` — structured crisis extraction from news text |
| **Multilingual generation** | `NarrativeGenerator` — stakeholder reports in local languages |
| **Multimodal (vision)** | `VisionAnalyst` — satellite/news image analysis |
| **Edge deployment** | Runs fully offline via Ollama on a $300 laptop |
| **Google AI Studio** | Cloud mode for high-throughput inference |
| **RAG** | Country profiles + historical data grounding |
| **Fine-tuning ready** | Unsloth-compatible for domain adaptation |

---

## Project Structure

```
CascadeAI/
├── agents/                  # Gemma 4 powered agents
│   ├── event_detector.py    # Natural language → crisis type + severity
│   ├── impact_predictor.py  # Country-level impact forecasting
│   ├── narrative_generator.py  # Stakeholder-specific multilingual reports
│   ├── vision_analyst.py    # Image/satellite analysis
│   ├── dispatcher.py        # Route queries to correct agent
│   └── orchestrator.py      # Multi-agent coordination
├── cascade/
│   ├── graph.py             # Weighted directed cascade graph
│   ├── traversal.py         # BFS propagation engine
│   └── replay.py            # Historical backtest engine
├── data/
│   ├── country_profiles/    # 11 country vulnerability profiles (JSON)
│   ├── backtest/            # Historical crisis datasets
│   ├── predictions/         # Forward scenario predictions (2026)
│   └── fetchers/            # ACLED, EIA, World Bank, ReliefWeb APIs
├── frontend/
│   ├── app.py               # Streamlit main app
│   └── components/          # Map, impact cards, backtest view
├── models/
│   ├── gemma_client.py      # Unified Gemma 4 client (Ollama + Google AI)
│   └── function_schemas.py  # Tool call schemas
├── api.py                   # FastAPI REST backend
├── config.py                # Environment configuration
└── requirements.txt
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) (for local/offline mode) **or** a Google AI Studio API key (for cloud mode)

### 1. Clone & Install

```bash
git clone https://github.com/snehasankaran/CascadeAI.git
cd CascadeAI
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set your backend:

```bash
cp .env.example .env
```

**Option A — Local (Ollama, fully offline):**
```env
GEMMA_API_BASE=http://localhost:11434/v1
GEMMA_API_KEY=ollama
GEMMA_MODEL=gemma4:e2b
```

Pull the model:
```bash
ollama pull gemma4:e2b
```

**Option B — Cloud (Google AI Studio):**
```env
GEMMA_API_BASE=https://generativelanguage.googleapis.com/v1beta
GEMMA_API_KEY=your_google_ai_studio_key
GEMMA_MODEL=gemma-4-31b-it
```

### 3. Run the Backend API

```bash
uvicorn api:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 4. Run the Frontend

```bash
streamlit run frontend/app.py
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/cascade` | POST | Run cascade prediction from a trigger event |
| `/cascade/compound` | POST | Multi-event compound cascade |
| `/detect` | POST | Detect crisis type from natural language |
| `/narrative` | POST | Generate stakeholder narrative |
| `/backtest/{scenario}` | GET | Run historical backtest |
| `/predictions` | GET | List forward scenario predictions |
| `/countries` | GET | List available country profiles |
| `/graph` | GET | Return cascade graph structure |

### Example: Predict cascade from Sudan conflict

```bash
curl -X POST http://localhost:8000/cascade \
  -H "Content-Type: application/json" \
  -d '{"node": "war", "severity": 0.85, "country": "kenya"}'
```

---

## Supported Countries

Bangladesh · Chile · Congo DRC · Egypt · Ethiopia · India · Indonesia · Kenya · Pakistan · Somalia · Turkey

---

## Backtest Scenarios

| Scenario | Date | Description |
|---|---|---|
| `ukraine_2022` | Feb 24, 2022 | Russia-Ukraine war → global food crisis |
| `sudan_2023` | Apr 15, 2023 | Sudan civil war → famine + displacement |
| `hormuz_2026` | Mar 2026 | Strait of Hormuz disruption → fertilizer surge |
| `bev_crash_2025` | 2025 | EV market crash → supply chain cascade |

---

## Live 2026 Validation

CascadeAI's cascade graph edges are validated against current real-world data:

| Edge | Weight | 2026 Evidence |
|---|---|---|
| WAR → DISPLACEMENT | 0.90 | Sudan: 14M displaced ✓ |
| WAR → HEALTH | 0.60 | Sudan: 70% healthcare collapsed ✓ |
| ENERGY → FERTILIZER | 0.85 | Hormuz: urea +46% in one month ✓ |
| FERTILIZER → CROP | 0.75 | Sub-Saharan Africa planting at risk (emerging) |
| FOOD → HEALTH | 0.85 | Sudan: 4.2M children acutely malnourished ✓ |

---

## Hackathon Submission

- **Competition**: [Gemma 4 Good Hackathon](https://kaggle.com/competitions/gemma-4-good-hackathon)
- **Track**: Global Resilience (Impact Track)
- **Model**: Gemma 4 (gemma4:e2b local / gemma-4-31b-it cloud)
- **Deadline**: May 18, 2026

---

## License

MIT License — open source, open data, open model.
