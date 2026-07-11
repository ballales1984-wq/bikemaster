from __future__ import annotations

import os

from aethermap.render.ascii import render_ascii
from aethermap.render.scene import Scene

_HERE = os.path.dirname(__file__)


def main() -> None:
    scene = Scene.example()
    frame = render_ascii(scene)
    print(frame)
    out = os.path.join(_HERE, "frame.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(frame + "\n")
    print(f"\n[render] frame salvato in {out}")


if __name__ == "__main__":
    main()
