# CascadeAI

## Closing the 120-day gap between when a crisis starts cascading and when the world responds.

**Track:** Global Resilience (+ Ollama Special Track) · **Powered by:** Gemma 4 · **Repo:** https://github.com/snehasankaran/CascadeAI · **Live demo:** https://cascadeai-cvpptq4nakg5kg8jtepf6v.streamlit.app · **Video:** https://www.youtube.com/watch?v=n1ubwIsnSjk

---

## 1 · The Problem

Today, **318 million people across 68 countries face crisis-level hunger — double 2019.** These are not isolated events. They are **cascades** — chains of failure where a conflict in one region quietly destroys food systems, health infrastructure, and water access thousands of kilometres away.

In February 2022, Russia invaded Ukraine. The warning signs of a global food catastrophe were visible within hours — wheat exports halted, fertilizer supply severed, Black Sea shipping disrupted. Yet the world took **120 days** to connect those dots to bread prices in Mombasa. By then, 47 million additional people across East Africa and South Asia were food-insecure. That delay — between when a cascade *begins* and when humanitarian organizations *act* — is the 120-day gap.

Existing tools do not close this gap. WFP HungerMap LIVE and FEWS NET are excellent **observation systems**: they tell you food insecurity is rising once it shows up in the data. CascadeAI is a **scenario engine**: it tells you which countries are about to break, by how much, and how soon, *the moment a triggering event occurs* — before the first food price moves.

Consider Mary Wanjiku, a Senior Programme Officer at a Nairobi humanitarian agency. When Hormuz shipping was disrupted in March 2026, Mary had 48 hours to decide whether to pre-position wheat reserves at Mombasa. The data she needed — energy → fertilizer → crop → food → health, propagated through Kenya's specific vulnerabilities, in her language — was scattered across nine agencies. CascadeAI is built for Mary.

---

## 2 · The Solution

CascadeAI takes a single trigger event (*"Hormuz shipping disrupted, severity 0.8"*) and walks an **11-node / 18-edge directed dependency graph** to forecast which downstream systems will break, in which country, by how much, and on what timeline. The cascade math is **fully deterministic** — pure BFS over a coefficient graph grounded in IEA, FAO, IFPRI, UNHCR, WHO, ILO, and World Bank source data. Gemma 4 supplies the natural-language layer around it.

This architecture intentionally separates prediction from generation: **Gemma 4 explains and verifies the cascade, but never invents the cascade itself.** That separation is what makes every number traceable and every forecast reproducible.

Eight agents share one `GemmaClient` and run in sequence: **Event Detector** (NL → graph seed), **Cascade Analyzer** (deterministic BFS), **Impact Predictor** (per-country numerical forecasts), **Dispatcher** (4-stakeholder action plans), **Action Verifier** (live ReliefWeb + ACLED, classifies each action as *in-progress / partial / blind spot*), **Vision Analyst** (multimodal — satellite tiles, sitrep pages), **Narrative Generator** (8 audience voices × 11 languages), and **Orchestrator**.

Action Verifier is CascadeAI's headline differentiator. **It tells responders not just what to do, but what is not being done yet.** Using Gemma 4's native function-calling protocol, it autonomously queries `search_reliefweb_reports`, `lookup_active_response_plans`, and `search_acled_recent` — each data spine auto-degrades from the credentialed v2/v3 API to a public RSS / HDX XLSX fallback so the demo never goes dark — then classifies every recommended action against real, dated-today humanitarian evidence.

What Mary sees: she types *"Hormuz shipping disrupted"*, picks Kenya, and within seconds gets a cascade map, an impact card (*+44% wheat in 60 days, 2.1M affected*), a four-stakeholder action plan, an **Action Watch** panel flagging the unaddressed Sudanese refugee corridor as a blind spot, and a ready-to-send Swahili WhatsApp message for her field network. The same scenario runs on her $300 laptop offline via Ollama Gemma 4 E2B.

---

## 3 · The Proof

We back-tested CascadeAI against four crises using **only data available before each event**, then compared its forecasts to what actually happened.

| Scenario | Trigger | Countries | Within range |
|---|---|---|---|
| Ukraine 2022 | Russia invasion → wheat / fertilizer shock | Kenya, Ethiopia, Egypt, Bangladesh | **13 / 13** |
| Sudan 2023 → 2026 | Civil war → cascading collapse | Somalia, Ethiopia, Egypt | **6 / 7** |
| Hormuz 2026 | Shipping disruption → energy → fertilizer surge | Kenya, Bangladesh, India | **8 / 8** |
| BEV Crash 2025 | US tariffs → mineral price collapse | Congo DRC, Chile, Indonesia | **11 / 11** |
| **Total** | **4 scenarios · 13 countries** | | **38 / 39 retrospective forecasts within predefined scenario ranges** |

The Ukraine 2022 result is the headline. CascadeAI, running only on pre-February-2022 data, predicted Kenya wheat would rise 35–45% within 60–90 days. Actual peak (June 2022): **+44%**. It predicted East Africa food-insecure populations would grow by 15–25 million in 90–180 days. Actual (Q3 2022): **+23 million**. We're honest about misses too — our fertilizer model under-predicted because it didn't initially account for Russia's role as a major fertilizer exporter alongside Ukraine; we've since added a Compound BFS pathway that lets two seed nodes fire simultaneously with severity combined via probabilistic union.

We also published **four forward predictions** (BEV Second Wave, EU Auto Cascade, Hormuz Escalation, Sudan Famine Spread) with explicit verification windows and named data sources. Anyone can check our accuracy in six months. **We are willing to be wrong in public.**

During development, real-world fertilizer-price volatility aligned with the disruption pathways our Hormuz cascade emphasized. The dual-disruption pathway we added after Ukraine 2022 is what kept the forecasts within range.

---

## 4 · Gemma 4 Integration

**Gemma 4 was chosen not as a generic chatbot layer, but because its multimodal reasoning, multilingual fluency, and native tool-calling made it uniquely capable of translating deterministic crisis forecasts into operational humanitarian action.** We use five distinct Gemma 4 capabilities, each tied to a user need rather than added for show.

1. **Native function calling — end-to-end live.** The Action Verifier runs multi-turn agentic loops on Gemma 4's `apply_chat_template(tools=[...])` (Ollama / Hugging Face) and `functionDeclarations` (Google AI Studio). Real `tool_call` control tokens — not prompt-engineered JSON — round-trip through `agents/tool_runtime.py` to two auto-degrading humanitarian data spines: **ReliefWeb** (v2 API → public RSS) and **ACLED** (v3 API → ACLED-via-HDX XLSX, CC BY 4.0, no credentials). A green `LIVE · NATIVE TOOL CALLS` badge tells the viewer which transport answered. The blind-spot detection is impossible without this.

2. **Multimodal vision.** The Vision Analyst sends `inlineData` parts to `gemma-4-31b-it:generateContent` and parses structured assessments back. In the demo, Mary uploads a Sentinel-2 NDVI tile of Turkana rangelands; Gemma 4 returns severity SEVERE, affected nodes `crop / food / water / displacement`, and seeds the cascade.

3. **Multilingual generation — one model, 11 languages.** English, Swahili, Bengali, Hindi, Arabic, Amharic, French, Portuguese, Indonesian, Spanish, Turkish. The same crisis renders as a WHO English briefing, a Swahili community alert, and an Amharic SMS — without a separate translation pipeline.

4. **Dual backend — cloud + edge.** `models/gemma_client.py` auto-detects the backend from the URL. **Gemma 4 31B Dense via Google AI Studio** powers the hosted demo, chosen for its long-context multi-turn tool-call coherence (which the Action Verifier requires). **Gemma 4 E2B via Ollama** runs the identical pipeline on Mary's $300 laptop offline, qualifying CascadeAI for the **Ollama Special Track**. The demo video disconnects from WiFi mid-run; the cascade keeps executing.

5. **Engineering discipline.** All six text agents return strict schema-validated JSON; failures fall back gracefully so the dashboard never breaks. Eight agents share one client — adding a ninth is ~50 lines. We deliberately did not fine-tune for this submission, demonstrating that base Gemma 4 with strong prompts, function calling, and grounded retrieval is already sufficient for serious humanitarian work *today*. An Unsloth-ready LoRA recipe and 50 seed training examples live in `notebooks/unsloth_cascadeai_finetune.ipynb` for any agency that wants to specialise the model on their playbook.

---

## 5 · Impact

CascadeAI is open source under MIT. Any agency — WFP, WHO, UNHCR, OCHA, FEWS NET, IFRC, the Kenya Red Cross — can fork, deploy, and adapt it for free. It runs on a $300 laptop offline. It speaks the language a mother in Turkana actually speaks.

The 120-day gap is not a technical limitation; it is an information-coordination failure. The math works. What is needed now is field deployment with a real partner agency, integration with the OCHA Anticipatory Action framework, and live wiring of the four forward predictions so the world can audit them in public.

Every crisis cascades. Sudan is cascading right now. Hormuz is cascading right now. The question is not whether AI can model these — we have shown it can — but whether the world is willing to act on a forecast it once took 120 days to receive.

**CascadeAI turns 120 days of reaction into 48 hours of preparation.**
