"""生成一份合成 TCX（模拟 Apple Watch / WorkOutDoors 导出），用于端到端验证。"""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "running" / "test_run_10k.tcx"
OUT.parent.mkdir(parents=True, exist_ok=True)

START = datetime(2026, 10, 14, 7, 30, 0)
DURATION_S = 3600
POINTS = 600
DIST_TOTAL_M = 10000.0
BASE_LAT, BASE_LON = 28.2282, 112.9388

lines = []
lines.append('<?xml version="1.0" encoding="UTF-8"?>')
lines.append('<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">')
lines.append("  <Activities>")
lines.append('    <Activity Sport="Running">')
lines.append(f"      <Id>{START.isoformat()}Z</Id>")
lines.append(f"      <Lap StartTime=\"{START.isoformat()}Z\">")
lines.append(f"        <TotalTimeSeconds>{DURATION_S}</TotalTimeSeconds>")
lines.append(f"        <DistanceMeters>{DIST_TOTAL_M}</DistanceMeters>")
lines.append("        <Calories>760</Calories>")
lines.append("        <Intensity>Active</Intensity>")
lines.append("        <TriggerMethod>Manual</TriggerMethod>")
lines.append("        <Track>")

for i in range(POINTS):
    frac = i / (POINTS - 1)
    t = START + timedelta(seconds=frac * DURATION_S)
    dist = frac * DIST_TOTAL_M
    hr = 140 + 18 * frac + 2.0 * math.sin(frac * 12 * math.pi)
    cadence = 172 + 3.0 * math.sin(frac * 20 * math.pi)
    speed = DIST_TOTAL_M / DURATION_S
    lat = BASE_LAT + (dist / 111_320.0)
    lon = BASE_LON + 0.0006 * math.sin(frac * 6 * math.pi)
    alt = 45.0 + 20.0 * math.sin(frac * 5 * math.pi)

    lines.append("          <Trackpoint>")
    lines.append(f"            <Time>{t.isoformat()}Z</Time>")
    lines.append("            <Position>")
    lines.append(f"              <LatitudeDegrees>{lat:.6f}</LatitudeDegrees>")
    lines.append(f"              <LongitudeDegrees>{lon:.6f}</LongitudeDegrees>")
    lines.append("            </Position>")
    lines.append(f"            <AltitudeMeters>{alt:.1f}</AltitudeMeters>")
    lines.append(f"            <DistanceMeters>{dist:.1f}</DistanceMeters>")
    lines.append("            <HeartRateBpm>")
    lines.append(f"              <Value>{int(round(hr))}</Value>")
    lines.append("            </HeartRateBpm>")
    lines.append("            <Extensions>")
    lines.append("              <ns3:TPX>")
    lines.append(f"                <ns3:Speed>{speed:.3f}</ns3:Speed>")
    lines.append(f"                <ns3:RunCadence>{int(round(cadence))}</ns3:RunCadence>")
    lines.append("              </ns3:TPX>")
    lines.append("            </Extensions>")
    lines.append("          </Trackpoint>")

lines.append("        </Track>")
lines.append("      </Lap>")
lines.append("    </Activity>")
lines.append("  </Activities>")
lines.append("</TrainingCenterDatabase>")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"已生成 {OUT}  ({OUT.stat().st_size/1024:.1f} KB, {POINTS} 个轨迹点)")