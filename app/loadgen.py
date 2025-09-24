#!/usr/bin/env python3
import argparse
import time
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
import requests
from collections import Counter
from pathlib import Path
import json

DEFAULT_PROMPTS = [
    "Explain OpenTelemetry in one sentence.",
    "What is the difference between tracing and logging?",
    "Summarize why a Collector fan-out is useful.",
    "How does sampling affect trace quality?",
    "Give me 3 pros and 3 cons of auto-instrumentation.",
    "What is an OTLP exporter and why do we use one?",
    "Describe a typical Grafana Tempo + Prometheus + Loki stack.",
    "How do I correlate a trace in Grafana with a Phoenix session?",
    "What are common labels/tags to add to LLM spans?",
    "Explain the term ‘span kind’ with examples."
]

def load_prompts(path: str | None):
    if not path:
        return DEFAULT_PROMPTS
    p = Path(path)
    if not p.exists():
        print(f"[warn] prompts file not found: {p} — falling back to defaults")
        return DEFAULT_PROMPTS
    # supports JSON list or newline-delimited text
    if p.suffix.lower() in (".json", ".jsonl"):
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return [str(x) for x in data if x]
        else:
            return DEFAULT_PROMPTS
    else:
        return [line.strip() for line in p.read_text().splitlines() if line.strip()]

def do_request(session, method, url, timeout, verify, headers=None, data=None, json_body=None):
    t0 = time.time()
    try:
        resp = session.request(method=method, url=url, timeout=timeout, verify=verify,
                               headers=headers, data=data, json=json_body)
        latency = time.time() - t0
        return True, resp.status_code, latency, None, resp
    except Exception as e:
        latency = time.time() - t0
        return False, None, latency, str(e), None

def main():
    parser = argparse.ArgumentParser(description="HTTP/LLM load generator with random RPS and concurrency")
    parser.add_argument("--mode", choices=["get", "chat"], default="get",
                        help="get = GET <url> each request; chat = POST JSON prompts to /chat")
    parser.add_argument("--url", required=True,
                        help="Target URL. For mode=get, this is the GET endpoint. For mode=chat, this should be the /chat endpoint.")
    parser.add_argument("--duration", type=int, default=1, help="Duration in minutes")
    parser.add_argument("--max-rps", type=int, default=10, help="Maximum requests per second (randomized 1..max)")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout seconds (chat can take longer)")
    parser.add_argument("--no-preflight", action="store_true", help="Skip initial connectivity check")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    # chat mode extras
    parser.add_argument("--prompts-file", help="Path to JSON list or newline-delimited prompts")
    parser.add_argument("--model", help="Override model (e.g., llama3.2:3b). If omitted, server default is used.")
    parser.add_argument("--min-words", type=int, default=10, help="Minimum words to request (hint in prompt)")
    parser.add_argument("--max-words", type=int, default=60, help="Maximum words to request (hint in prompt)")
    args = parser.parse_args()

    prompts = load_prompts(args.prompts_file) if args.mode == "chat" else []

    duration_s = args.duration * 60
    end_time = time.time() + duration_s
    verify = not args.insecure

    attempts = 0
    successes = 0
    failures = 0
    status_counts = Counter()
    latencies = []
    error_samples = Counter()

    session = requests.Session()
    session.headers.update({"User-Agent": "loadgen/llm-1.2"})

    # Preflight
    if not args.no_preflight:
        try:
            if args.mode == "get":
                pre = session.get(args.url, timeout=args.timeout, verify=verify)
            else:
                # send a tiny prompt
                body = {"prompt": "ping", "model": args.model} if args.model else {"prompt": "ping"}
                pre = session.post(args.url, json=body, timeout=args.timeout, verify=verify)
            print(f"[preflight] {args.url} -> HTTP {pre.status_code}")
        except Exception as e:
            print(f"[preflight] Cannot reach {args.url}: {e}")
            print("Tip: check URL/port, container bindings, network, or run with --no-preflight to skip.")
            return

    print(f"Running for {args.duration}m | mode={args.mode} | target={args.url} | 1..{args.max_rps} rps | "
          f"concurrency={args.concurrency} | timeout={args.timeout}s")

    def submit_one():
        nonlocal attempts
        attempts += 1
        if args.mode == "get":
            return pool.submit(
                do_request, session, "GET", args.url, args.timeout, verify, None, None, None
            )
        else:
            # pick and lightly vary a prompt
            base = random.choice(prompts)
            want = random.randint(args.min_words, max(args.min_words, args.max_words))
            hint = f" Answer in about {want} words."
            prompt = base if base.endswith((".", "?", "!")) else base + "."
            prompt += hint
            body = {"prompt": prompt}
            if args.model:
                body["model"] = args.model
            headers = {"content-type": "application/json"}
            return pool.submit(
                do_request, session, "POST", args.url, args.timeout, verify, headers, None, body
            )

    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            inflight = set()
            while time.time() < end_time:
                second_start = time.time()
                rps = random.randint(1, max(1, args.max_rps))
                for _ in range(rps):
                    fut = submit_one()
                    inflight.add(fut)

                # harvest whatever completes this second
                while True:
                    elapsed = time.time() - second_start
                    if elapsed >= 1.0:
                        break
                    done, inflight = wait(inflight, timeout=max(0.0, 1.0 - elapsed), return_when=FIRST_COMPLETED)
                    if not done:
                        break
                    for f in done:
                        try:
                            ok, code, lat, err, resp = f.result()
                            if ok:
                                successes += 1
                                status_counts[code] += 1
                                if lat is not None:
                                    latencies.append(lat)
                                # optional: sanity-check LLM response JSON
                                if args.mode == "chat" and code == 200:
                                    # don’t print; we’re load testing
                                    _ = resp.json()
                            else:
                                failures += 1
                                if err:
                                    key = err.split(":")[0][:60]
                                    error_samples[key] += 1
                        except Exception as e:
                            failures += 1
                            key = str(e).split(":")[0][:60]
                            error_samples[key] += 1

                # keep ~1s cadence
                elapsed = time.time() - second_start
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)

            # drain leftovers
            for f in as_completed(inflight):
                try:
                    ok, code, lat, err, _ = f.result()
                    if ok:
                        successes += 1
                        status_counts[code] += 1
                        if lat is not None:
                            latencies.append(lat)
                    else:
                        failures += 1
                        if err:
                            key = err.split(":")[0][:60]
                            error_samples[key] += 1
                except Exception as e:
                    failures += 1
                    key = str(e).split(":")[0][:60]
                    error_samples[key] += 1

    except KeyboardInterrupt:
        print("\n[info] Stopped early by user.")

    total = attempts
    success_rate = (successes / total * 100.0) if total > 0 else 0.0
    avg_lat = statistics.mean(latencies) if latencies else None
    p95_lat = None
    if latencies:
        lat_sorted = sorted(latencies)
        idx = int(0.95 * (len(lat_sorted) - 1))
        p95_lat = lat_sorted[idx]

    print("\n=== Load Generator Report ===")
    ran_for = (args.duration * 60) - max(0.0, end_time - time.time())
    print(f"Duration: {ran_for:.1f}s")
    print(f"Attempts: {total}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    print(f"Success Rate: {success_rate:.2f}%")
    if status_counts:
        print("Status codes:")
        for code, cnt in sorted(status_counts.items()):
            print(f"  {code}: {cnt}")
    if avg_lat is not None:
        print(f"Latency avg: {avg_lat*1000:.1f} ms")
    if p95_lat is not None:
        print(f"Latency p95: {p95_lat*1000:.1f} ms")
    if error_samples:
        print("Sample errors (top 5):")
        for err, cnt in error_samples.most_common(5):
            print(f"  {err} ... x{cnt}")

if __name__ == "__main__":
    main()
