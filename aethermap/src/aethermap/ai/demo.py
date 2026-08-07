from __future__ import annotations

import os

from aethermap.ai.ingest import ingest_gpx, ingest_sensor_stream_stub
from aethermap.ai.pipeline import Pipeline, PipelineWorldStore

_HERE = os.path.dirname(__file__)


def main() -> None:
    store = PipelineWorldStore()
    pipe = Pipeline(store, max_latency_s=1.0)

    points = ingest_gpx(os.path.join(_HERE, "sample.gpx"))
    print(f"[ingest] GPX: {len(points)} punti")

    proposte = pipe.research_gpx(points)
    for p in proposte:
        print(f"[ricercatore] nuova {p.tipo} | conf={p.confidence} | {p.motivazione}")
        pipe.submit(p)
    applied = pipe.flush()
    print(f"[pipeline] create entità: {applied}")

    for feat in ingest_sensor_stream_stub(3):
        p = pipe.research_sensor(feat)
        print(f"[ricercatore] update traffico={p.valore} -> {p.target_id} | conf={p.confidence}")
        pipe.submit(p)
    applied = pipe.flush()
    print(f"[pipeline] update applicati: {applied}")

    print("\n=== MONDO (stato) ===")
    print(store.to_json())


if __name__ == "__main__":
    main()
