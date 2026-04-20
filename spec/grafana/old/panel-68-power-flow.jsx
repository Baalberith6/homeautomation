/**
 * Power Flow v6 — Panel 68 (Grafana Business Text)
 *
 * Self-contained React component that renders a 3x3 CSS grid with styled
 * divs approximating the canvas-rendered icons used in the real panel.
 *
 * Mock data is embedded so the component can be previewed standalone.
 *
 * CSS scope: #pf6, .pf6-* prefixes to avoid collisions with the rest of
 * the Grafana dashboard.
 *
 * Performance notes (v6.1):
 * - Canvas animations use requestAnimationFrame with auto-stop after 3s
 *   (data refreshes every 10s via Grafana, which re-triggers afterRender)
 * - No shadowBlur — glow effects use wider, lower-opacity strokes instead
 * - Gradients cached once per data refresh, not created per frame
 * - No CSS infinite @keyframes — shimmer/glow are static gradient overlays
 * - Grid direction uses static colored overlay + bouncing arrow (no lineDash)
 */
import React from "react";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------
const MOCK = {
  solar: { kW: 3.42 },
  selfSufficiency: { pct: 67 },
  house: { kW: 2.18 },
  battery: { pct: 72, kW: 0.85, charging: true, timeRemaining: "~2h 15m" },
  grid: { kW: 1.24, exporting: true },
  wallbox: { kW: 6.5, carConnected: true },
  today: { consumed: 15.2, produced: 18.7 },
  virtualBattery: { pct: 87, sold: 142, bought: 163 },
  month: { consumed: 487, produced: 523 },
};

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------
const solarColor = (kW) => (kW < 4 ? "#64dc64" : "#ffaa00");
const houseColor = (kW) => (kW < 2 ? "#73bf69" : kW < 4 ? "#ffaa00" : "#ff4444");
const ssColor = (pct) =>
  pct >= 80 ? "#00cc66" : pct >= 50 ? "#ffaa00" : "#ff4444";
const batteryFillColor = (pct) =>
  pct > 90 ? "#5794F2" : pct >= 30 ? "#73BF69" : pct >= 20 ? "#FF9830" : pct >= 10 ? "#FF6B3D" : "#F2495C";
const gridBadge = (exporting) =>
  exporting
    ? { label: "EXPORT", bg: "#1c3a20", color: "#50ff78" }
    : { label: "IMPORT", bg: "#3a1a1a", color: "#ff5050" };

// ---------------------------------------------------------------------------
// Tiny SVG arc gauge (self-sufficiency / virtual battery)
// ---------------------------------------------------------------------------
function ArcGauge({ pct, color, size = 80 }) {
  const r = (size - 8) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = -210;
  const sweep = 240;
  const endAngle = startAngle + sweep * (pct / 100);

  const polarToCart = (angleDeg) => {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const bgStart = polarToCart(startAngle);
  const bgEnd = polarToCart(startAngle + sweep);
  const fgEnd = polarToCart(endAngle);

  const arcPath = (sx, sy, ex, ey, sweepDeg) => {
    const large = Math.abs(sweepDeg) > 180 ? 1 : 0;
    return `M ${sx} ${sy} A ${r} ${r} 0 ${large} 1 ${ex} ${ey}`;
  };

  return (
    <svg width={size} height={size} style={{ display: "block", margin: "0 auto" }}>
      <path
        d={arcPath(bgStart.x, bgStart.y, bgEnd.x, bgEnd.y, sweep)}
        fill="none"
        stroke="#222"
        strokeWidth={6}
        strokeLinecap="round"
      />
      <path
        d={arcPath(bgStart.x, bgStart.y, fgEnd.x, fgEnd.y, sweep * (pct / 100))}
        fill="none"
        stroke={color}
        strokeWidth={6}
        strokeLinecap="round"
      />
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        fill="#eee"
        fontSize={size * 0.26}
        fontWeight="bold"
        fontFamily="monospace"
      >
        {pct}%
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Energy bar with shimmer
// ---------------------------------------------------------------------------
function EnergyBar({ value, max, color, label }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="pf6-bar-row">
      <span className="pf6-bar-label">{label}</span>
      <div className="pf6-bar-track">
        <div
          className="pf6-bar-fill pf6-shimmer"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}cc, ${color})`,
            boxShadow: `0 0 8px ${color}88`,
          }}
        />
      </div>
      <span className="pf6-bar-value" style={{ color }}>
        {value} kWh
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
function PowerFlowPanel() {
  const d = MOCK;
  const badge = gridBadge(d.grid.exporting);
  const gridValueColor = d.grid.exporting ? "#50ff78" : "#ff5050";
  const batteryDeltaColor = d.battery.charging ? "#50ff78" : "#ff5050";
  const batteryDeltaSign = d.battery.charging ? "+" : "-";

  const barMax = Math.max(
    d.today.consumed,
    d.today.produced,
    d.month.consumed,
    d.month.produced
  );

  return (
    <div id="pf6">
      <style>{`
        /* ----- base grid ----- */
        #pf6 {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr;
          grid-template-rows: 1fr 1fr 1fr;
          gap: 2px;
          width: 100%;
          height: 100%;
          min-height: 380px;
          background: #050505;
          font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
          color: #ddd;
          box-sizing: border-box;
        }
        .pf6-cell {
          background: #0a0a0a;
          border-radius: 8px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 6px 4px;
          overflow: hidden;
          position: relative;
        }
        .pf6-icon {
          font-size: 28px;
          line-height: 1;
          margin-bottom: 2px;
        }
        .pf6-value {
          font-size: 18px;
          font-weight: 700;
          font-family: monospace;
          line-height: 1.2;
        }
        .pf6-sub {
          font-size: 10px;
          color: #888;
          line-height: 1.2;
          margin-top: 1px;
        }
        .pf6-title {
          font-size: 9px;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: #666;
          margin-bottom: 2px;
        }

        /* ----- badge ----- */
        .pf6-badge {
          display: inline-block;
          font-size: 9px;
          font-weight: 700;
          padding: 1px 6px;
          border-radius: 4px;
          letter-spacing: 0.6px;
          margin-top: 2px;
        }

        /* ----- battery fill bar ----- */
        .pf6-batt-track {
          width: 60%;
          height: 10px;
          background: #1a1a1a;
          border-radius: 5px;
          overflow: hidden;
          margin: 3px 0;
          border: 1px solid #333;
        }
        .pf6-batt-fill {
          height: 100%;
          border-radius: 5px;
          transition: width 0.6s ease;
        }

        /* ----- energy bars ----- */
        .pf6-bar-row {
          display: flex;
          align-items: center;
          gap: 4px;
          width: 90%;
          margin: 1px 0;
        }
        .pf6-bar-label {
          font-size: 8px;
          color: #777;
          width: 10px;
          text-align: right;
          flex-shrink: 0;
        }
        .pf6-bar-track {
          flex: 1;
          height: 7px;
          background: #1a1a1a;
          border-radius: 4px;
          overflow: hidden;
        }
        .pf6-bar-fill {
          height: 100%;
          border-radius: 4px;
          position: relative;
        }
        .pf6-bar-value {
          font-size: 9px;
          font-weight: 600;
          font-family: monospace;
          min-width: 48px;
          text-align: right;
          flex-shrink: 0;
        }

        /* ----- shimmer (static gradient overlay, no animation) ----- */
        .pf6-shimmer {
          background: linear-gradient(90deg, transparent 30%, rgba(255,255,255,0.08) 50%, transparent 70%);
          pointer-events: none;
        }

        /* ----- virtual battery footer ----- */
        .pf6-vb-footer {
          display: flex;
          gap: 8px;
          font-size: 8px;
          color: #888;
          margin-top: 2px;
        }
        .pf6-vb-footer span {
          font-weight: 600;
        }

        /* ----- wallbox ----- */
        .pf6-wallbox-dot {
          display: inline-block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          margin-right: 3px;
          vertical-align: middle;
        }
      `}</style>

      {/* ===== Row 1 ===== */}

      {/* (1,1) Solar */}
      <div className="pf6-cell">
        <div className="pf6-title">Solar</div>
        <div className="pf6-icon">&#9728;&#65039;</div>
        <div className="pf6-value" style={{ color: solarColor(d.solar.kW) }}>
          {d.solar.kW.toFixed(2)} kW
        </div>
      </div>

      {/* (2,1) Self-Sufficiency */}
      <div className="pf6-cell">
        <div className="pf6-title">Self-Sufficiency</div>
        <ArcGauge pct={d.selfSufficiency.pct} color={ssColor(d.selfSufficiency.pct)} size={76} />
      </div>

      {/* (3,1) House */}
      <div className="pf6-cell">
        <div className="pf6-title">House</div>
        <div className="pf6-icon">&#127968;</div>
        <div className="pf6-value" style={{ color: houseColor(d.house.kW) }}>
          {d.house.kW.toFixed(2)} kW
        </div>
      </div>

      {/* ===== Row 2 ===== */}

      {/* (1,2) Battery */}
      <div className="pf6-cell">
        <div className="pf6-title">Battery</div>
        <div className="pf6-icon">&#128267;</div>
        <div className="pf6-value" style={{ color: batteryFillColor(d.battery.pct) }}>
          {d.battery.pct}%
        </div>
        <div className="pf6-batt-track">
          <div
            className="pf6-batt-fill"
            style={{
              width: `${d.battery.pct}%`,
              background: batteryFillColor(d.battery.pct),
            }}
          />
        </div>
        <div className="pf6-sub" style={{ color: batteryDeltaColor }}>
          {batteryDeltaSign}{Math.abs(d.battery.kW).toFixed(2)} kW
        </div>
        <div className="pf6-sub">{d.battery.timeRemaining}</div>
      </div>

      {/* (2,2) Grid */}
      <div className="pf6-cell">
        <div className="pf6-title">Grid</div>
        <div className="pf6-icon">&#9889;</div>
        <div className="pf6-value" style={{ color: gridValueColor }}>
          {d.grid.exporting ? "+" : "-"}{d.grid.kW.toFixed(2)} kW
        </div>
        <div
          className="pf6-badge"
          style={{ background: badge.bg, color: badge.color }}
        >
          {badge.label}
        </div>
      </div>

      {/* (3,2) Wallbox */}
      <div className="pf6-cell">
        <div className="pf6-title">Wallbox</div>
        <div className="pf6-icon">&#128663;</div>
        <div className="pf6-value" style={{ color: "#FF9830" }}>
          {d.wallbox.kW.toFixed(1)} kW
        </div>
        <div className="pf6-sub">
          <span
            className="pf6-wallbox-dot"
            style={{ background: d.wallbox.carConnected ? "#50ff78" : "#555" }}
          />
          {d.wallbox.carConnected ? "Car connected" : "No car"}
        </div>
      </div>

      {/* ===== Row 3 ===== */}

      {/* (1,3) Today */}
      <div className="pf6-cell">
        <div className="pf6-title">Today</div>
        <EnergyBar
          value={d.today.produced}
          max={barMax}
          color="#51cf66"
          label="P"
        />
        <EnergyBar
          value={d.today.consumed}
          max={barMax}
          color="#ff6b6b"
          label="C"
        />
      </div>

      {/* (2,3) Virtual Battery */}
      <div className="pf6-cell">
        <div className="pf6-title">Virtual Battery</div>
        <ArcGauge
          pct={d.virtualBattery.pct}
          color={ssColor(d.virtualBattery.pct)}
          size={68}
        />
        <div className="pf6-vb-footer">
          <div>
            SOLD <span style={{ color: "#51cf66" }}>{d.virtualBattery.sold}</span> kWh
          </div>
          <div>
            BOUGHT <span style={{ color: "#ff6b6b" }}>{d.virtualBattery.bought}</span> kWh
          </div>
        </div>
      </div>

      {/* (3,3) Month */}
      <div className="pf6-cell">
        <div className="pf6-title">Month</div>
        <EnergyBar
          value={d.month.produced}
          max={barMax}
          color="#51cf66"
          label="P"
        />
        <EnergyBar
          value={d.month.consumed}
          max={barMax}
          color="#ff6b6b"
          label="C"
        />
      </div>
    </div>
  );
}

export default PowerFlowPanel;
