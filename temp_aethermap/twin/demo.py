from __future__ import annotations

import os

from aethermap.render.ascii import render_ascii
from aethermap.render.camera import Camera
from aethermap.render.scene import Scene
from aethermap.twin.objects import make_albero, make_montagna, make_strada
from aethermap.twin.world import DigitalTwin, Environment

_HERE = os.path.dirname(__file__)


def main() -> None:
    twin = DigitalTwin()

    pts = [{"lat": 45.0 + i * 0.0005, "lon": 9.0 + i * 0.0006, "ele": 120 + (i % 2) * 2}
           for i in range(6)]
    twin.add(make_strada("strada-1", 45.0, 9.0, pts))
    twin.add(make_albero("albero-1", 45.005, 9.01, "quercia", 8.5))
    twin.add(make_montagna("montagna-1", 45.015, 9.03, 1800.0, ["nord", "sud", "est"]))

    scenes = []
    for label, env in [
        ("GIORNO caldo", Environment(temp_c=22.0, solar_elev_deg=55.0, ora="12:00")),
        ("SERA fresca", Environment(temp_c=6.0, solar_elev_deg=8.0, ora="20:00")),
        ("NOTTE gelata", Environment(temp_c=-3.0, solar_elev_deg=0.0, ora="03:00")),
    ]:
        twin.step(env)
        if label == "NOTTE gelata":
            mont = next((o for o in twin.store.objects.values() if o.tipo == "montagna"), None)
            if mont is not None:
                print(f"\n[SVO] {mont.id} volume: {mont.volume_stats(env.temp_c)}")
        twin.step(env)
        print(f"\n=== {label} ({env.ora}) ===")
        for s in twin.snapshot():
            print(s)
        scene = Scene()
        for oid, obj in twin.store.objects.items():
            if obj.tipo == "strada":
                scene.add("strada", [(p["lat"], p["lon"]) for p in obj.geometria.dati["punti"]], char="S")
            else:
                scene.add(obj.tipo, (obj.posizione.lat, obj.posizione.lon),
                          alt=obj.posizione.alt, char=obj.tipo[0].upper())
        scenes.append((label, render_ascii(scene, Camera())))

    for label, frame in scenes:
        print(f"\n--- vista {label} ---")
        print(frame)

    with open(os.path.join(_HERE, "twin_frame.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(f"--- {l} ---\n{fr}" for l, fr in scenes) + "\n")
    print("\n[digital twin] frame salvati in twin_frame.txt")


if __name__ == "__main__":
    main()
