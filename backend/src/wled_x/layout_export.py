"""Exports the room layout -- devices, fixtures and every LED's 3D position --
as plain JSON, for tools that drive the same LEDs without the rest of WLED-X
(e.g. the wledx-cues sequencer).

    uv run wled-x-export-layout > layout.json     # straight from the database
    curl localhost:8000/api/layout/export          # from the running app
"""

import json
import sys
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from wled_x.db import engine, get_session
from wled_x.effects.geometry import led_positions
from wled_x.models.device import Device
from wled_x.models.fixture import Fixture

LAYOUT_VERSION = 1

router = APIRouter(prefix="/api/layout", tags=["layout"])


def build_layout(session: Session) -> dict[str, Any]:
    devices = session.exec(select(Device).order_by(Device.id)).all()
    fixtures = session.exec(select(Fixture).order_by(Fixture.id)).all()
    by_id = {d.id: d for d in devices}
    return {
        "version": LAYOUT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "units": "m",
        "devices": [{"name": d.name, "ip": d.ip, "led_count": d.led_count} for d in devices],
        "fixtures": [
            {
                "name": f.name,
                "device": by_id[f.device_id].name,
                "start_channel": f.start_channel,
                "led_count": f.led_count,
                "reverse": f.reverse,
                "points": f.points,
                # In channel order: leds[i] is the pixel at start_channel + i.
                "leds": [
                    [round(float(v), 4) for v in p]
                    for p in led_positions(f.points, f.led_count, f.reverse)
                ],
            }
            for f in fixtures
            if f.device_id in by_id
        ],
    }


@router.get("/export")
def export_layout(session: Session = Depends(get_session)) -> dict[str, Any]:
    return build_layout(session)


def main() -> None:
    with Session(engine) as session:
        json.dump(build_layout(session), sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
