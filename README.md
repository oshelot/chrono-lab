# ChronoLab

ChronoLab is a local observability lab that ties together **OpenTelemetry**, **Prometheus**, **Tempo**, **Phoenix** and **Grafana** with GPU metrics (via NVIDIA DCGM) and LLM span metrics.  
It’s designed as a self-contained environment for experimenting with span metrics, traces, and exemplar linking into Phoenix.

---

## Repository Structure

```
chrono-lab/
├── app/
│   ├── app.py
│   ├── loadgen.py
│   ├── run_app.sh
│   └── run_load.sh
├── dashboards/
│   └── gpu-llm-traces-final.json   # Grafana dashboard with span + GPU panels
=======
│   └── gpu-llm-traces-final.json
├── prometheus/
│   └── prometheus.yml
├── tempo/
│   └── tempo.yaml
├── otel/
│   └── otel-collector.yaml
├── compose/
│   └── docker-compose.yml
├── docs/
│   └── (Presentations, PDFs, diagrams)
└── README.md
```

> If your filenames differ, update the paths accordingly.

---

## Prerequisites

- Docker + Docker Compose v2
- (Optional) NVIDIA GPU if you want DCGM metrics
- (Optional) Ollama - If you want to generate load against a **local LLM**, you can install [Ollama](https://ollama.com/). Your `app/` and `loadgen.py` can then be configured to send traffic through a local Ollama instead of a remote API (as done here). Phoenix will ingest those traces the same way.

---

## Phoenix & LLM Observability

This lab uses **Phoenix** as the deep-dive UI for LLM observability.

- We currently focus on **Prompt/Response traces**: each LLM call is captured as a span with input/output details, visible in Phoenix.
- Grafana panels include **exemplar links** (trace IDs) that let you jump directly into Phoenix for detailed trace inspection.
- Phoenix also supports **LLM evaluation metrics** (toxicity, helpfulness, correctness) and **model comparison/regression testing**, but those are not enabled in this lab.
  
## Start the stack

```bash
cd compose
docker compose up -d
```

Services:
- **Prometheus** (metrics) — http://localhost:9090
- **Tempo** (traces) — http://localhost:3200
- **Grafana** (dashboards) — http://localhost:3000
- **OTel Collector** (pipelines)
- **DCGM exporter** (GPU telemetry)
- **Phoenix** (LLM trace exploration UI) — http://localhost:6006


Import the dashboard in Grafana: `dashboards/gpu-llm-traces-final.json`

---

## Run the app + load generator

=======

From another terminal:
Make sure scripts are executable:
```bash
chmod +x app/run_app.sh app/run_load.sh
```

```bash
cd app
./run_app.sh
```

Once running, generate load:

```bash
cd app
./run_load.sh
```



---

## One-liner: tmux session (3 panes)

This opens 3 panes: **Compose up**, **App**, and **Load** — all visible in a tiled layout.

```bash
tmux new-session -d -s chrono-lab 'cd ~/chrono-lab/compose && docker compose up -d' \;   split-window -h 'cd ~/chrono-lab/app && ./run_app.sh' \;   split-window -v 'cd ~/chrono-lab/app && ./run_load.sh' \;   select-layout tiled \; attach
```

> If your repo lives somewhere else, replace `~/chrono-lab` with the actual path.

---

## Notes

- Update the Prometheus and Tempo config files under `prometheus/` and `tempo/` if you add new scrape targets or want to adjust retention.  
- The `docs/` directory is for presentation material (e.g., PDFs of slides).  
=======
- Prometheus and Tempo configs live in `prometheus/` and `tempo/`. Adjust scrape targets and retention to taste.
- The `docs/` directory is for presentation material (PDFs, diagrams, etc.).
- If you later add a `requirements.txt` and virtualenv, you can wire that into `run_app.sh`; not required for this lab.

