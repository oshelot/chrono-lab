from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import random, time, requests, os

# --- OpenTelemetry manual tracing ---
from opentelemetry import trace
from opentelemetry.trace import SpanKind

app = FastAPI()
tracer = trace.get_tracer("demo-app")

@app.get("/api")
async def api():
    time.sleep(random.uniform(0.01, 0.2))
    if random.random() < 0.1:
        return JSONResponse({"ok": False, "error": "simulated failure"}, status_code=500)
    return {"ok": True, "msg": "Hello from demo app"}

# --- LLM proxy to Ollama ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")  # pick your model

@app.post("/chat")
def chat(payload: dict = Body(...)):
    """
    Expects: {"prompt": "your question", "model": "optional override"}
    """
    prompt = payload.get("prompt", "")
    model = payload.get("model", OLLAMA_MODEL)

    # Create a CLIENT span around the model call
    with tracer.start_as_current_span(
        "llm.generate",
        kind=SpanKind.CLIENT,
        attributes={
            "llm.system": "ollama",
            "llm.model_name": model,
            "llm.request.type": "completion",
            "llm.request.prompt.len_chars": len(prompt),
        }
    ) as span:
        try:
            # Non-streaming generate API
            # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30,
            )
            span.set_attribute("http.status_code", resp.status_code)

            if resp.status_code != 200:
                span.set_attribute("error", True)
                return JSONResponse({"ok": False, "error": resp.text}, status_code=resp.status_code)

            data = resp.json()
            # Ollama returns token/latency stats in fields like eval_count, total_duration (ns), etc.
            completion = data.get("response", "")
            eval_count = data.get("eval_count", None)          # tokens generated
            prompt_eval_count = data.get("prompt_eval_count", None)  # tokens in prompt
            total_ns = data.get("total_duration", None)

            if eval_count is not None:
                span.set_attribute("llm.response.completion_tokens", int(eval_count))
            if prompt_eval_count is not None:
                span.set_attribute("llm.request.prompt_tokens", int(prompt_eval_count))
            if total_ns is not None:
                span.set_attribute("llm.response.total_duration_ms", round(total_ns / 1e6, 2))

            span.set_attribute("llm.response.completion.len_chars", len(completion))

            return {
                "ok": True,
                "model": model,
                "prompt": prompt,
                "completion": completion,
                "stats": {
                    "prompt_tokens": prompt_eval_count,
                    "completion_tokens": eval_count,
                    "total_ms": round((total_ns or 0)/1e6, 2)
                }
            }
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("exception.message", str(e))
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
