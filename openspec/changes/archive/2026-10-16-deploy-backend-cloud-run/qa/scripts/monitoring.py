#!/usr/bin/env python3
"""Lee métricas de Cloud Monitoring (solo lectura) del servicio boticario-api con el token de gcloud.

Uso: monitoring.py <horas-atrás> <métrica> [<métrica> ...]
Métricas (sufijo tras run.googleapis.com/): request_count, container/memory/utilizations,
container/startup_latencies, container/cpu/allocation_time, container/memory/allocation_time,
container/billable_instance_time, request_latencies, container/instance_count.
No imprime ids de facturación. Requiere gcloud autenticado y PROJECT_ID (por defecto boticario-ai).
"""
import json, os, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

project = os.environ.get("PROJECT_ID", "boticario-ai")
service = os.environ.get("SERVICE", "boticario-api")
hours = float(sys.argv[1])
token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
end = datetime.now(timezone.utc)
start = end - timedelta(hours=hours)
fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(metric):
    flt = f'metric.type="run.googleapis.com/{metric}" AND resource.labels.service_name="{service}"'
    q = urllib.parse.urlencode({"filter": flt, "interval.startTime": fmt(start), "interval.endTime": fmt(end)})
    url = f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries?{q}"
    out, page = [], None
    while True:
        u = url + (f"&pageToken={page}" if page else "")
        req = urllib.request.Request(u, headers={"Authorization": f"Bearer {token}", "x-goog-user-project": project})
        d = json.load(urllib.request.urlopen(req))
        out += d.get("timeSeries", [])
        page = d.get("nextPageToken")
        if not page:
            return out


def dist_stats(v, opts):
    dv = v["distributionValue"]
    count = int(dv.get("count", 0))
    mean = dv.get("mean", 0.0)
    counts = [int(c) for c in dv.get("bucketCounts", [])]
    mx = None
    b = opts
    if "linearBuckets" in b and counts:
        w = b["linearBuckets"]["width"]; off = b["linearBuckets"].get("offset", 0)
        idx = max(i for i, c in enumerate(counts) if c) if any(counts) else 0
        mx = off + idx * w  # cota superior del último bucket ocupado (aprox.)
    elif "exponentialBuckets" in b and counts:
        g = b["exponentialBuckets"]
        idx = max(i for i, c in enumerate(counts) if c) if any(counts) else 0
        mx = g["scale"] * (g["growthFactor"] ** idx)
    return count, mean, mx


for metric in sys.argv[2:]:
    series = fetch(metric)
    print(f"## {metric} ({len(series)} series)")
    total = 0.0
    for s in series:
        labels = {k: v for k, v in s["resource"]["labels"].items() if k == "revision_name"}
        extra = {k: v for k, v in s["metric"].get("labels", {}).items()}
        pts = sorted(s["points"], key=lambda p: p["interval"]["endTime"])
        for p in pts:
            v = p["value"]
            t = p["interval"]["endTime"]
            if "distributionValue" in v:
                c, m, mx = dist_stats(v, v["distributionValue"].get("bucketOptions", {}))
                if c:
                    print(f"{t} {labels.get('revision_name','')} {extra} count={c} mean={m:.4g} max_bucket<={mx if mx is None else round(mx,4)}")
            else:
                val = v.get("doubleValue", v.get("int64Value", 0))
                val = float(val)
                total += val
                if val:
                    print(f"{t} {labels.get('revision_name','')} {extra} value={val:.6g}")
    if series and "distributionValue" not in series[0]["points"][0]["value"]:
        print(f"TOTAL {metric} = {total:.6g}")
