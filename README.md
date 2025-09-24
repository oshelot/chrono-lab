# ChronoLab

ChronoLab is a local observability lab that ties together **OpenTelemetry**, **Prometheus**, **Tempo**, and **Grafana** with GPU metrics (via NVIDIA DCGM) and LLM span metrics.  
It’s designed as a self-contained environment for experimenting with span metrics, traces, and exemplar linking into Phoenix.

---

## Repository Structure

```
chrono-lab/
├── dashboards/
│   └── gpu-llm-traces-merged-fixed.json   # Grafana dashboard with span + GPU panels
├── prometheus/
│   └── prometheus.yml                     # Prometheus scrape configuration
├── tempo/
│   └── tempo.yml                          # Tempo configuration
├── otel/
│   └── otel-collector-config.yaml         # OpenTelemetry Collector pipeline
├── compose/
│   └── docker-compose.yml                 # Services (Prometheus, Tempo, Grafana, OTEL, exporters)
├── docs/
│   └── (Presentations, PDFs, diagrams)
└── README.md
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)  
- [Docker Compose](https://docs.docker.com/compose/install/) (v2 recommended)  
- An NVIDIA GPU + [NVIDIA DCGM exporter](https://github.com/NVIDIA/dcgm-exporter) if you want GPU metrics  

---

## Running the Lab

From the repo root:

```bash
cd compose
docker compose up -d
```

This will start:
- **Prometheus** (metrics backend)
- **Tempo** (trace storage)
- **Grafana** (dashboards + UI)
- **OpenTelemetry Collector** (metrics/traces pipeline)
- **DCGM exporter** (GPU metrics)
- Any additional services defined in `docker-compose.yml`

---

## Accessing the UI

- Grafana: [http://localhost:3000](http://localhost:3000)  
  - Import the dashboard from `dashboards/gpu-llm-traces-merged-fixed.json`  
- Prometheus: [http://localhost:9090](http://localhost:9090)  
- Tempo: [http://localhost:3200](http://localhost:3200)  

---

## Notes

- Update the Prometheus and Tempo config files under `prometheus/` and `tempo/` if you add new scrape targets or want to adjust retention.  
- The `docs/` directory is for presentation material (e.g., PDFs of your slides).  

---

## Next Steps

- Expand the dashboards with more service-level metrics.  
- Add test load generators to produce spans and GPU usage.  
- Experiment with Phoenix links from exemplar trace IDs.
