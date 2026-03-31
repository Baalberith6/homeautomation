import { useState, useEffect } from "react";

const OTE_VBAT_PANEL = () => {
  // --- Mock data (replace with your actual Grafana data source) ---
  const [oteData] = useState({
    current: { price: 1.82, hour: "14:00" },
    max: { price: 3.21, hour: "13:00" },
    min: { price: -0.12, hour: "03:00" },
  });

  const [vbatData] = useState({
    charge: 42.3,         // virtualBatteryActualCharge (kWh)
    production: 1250.0,   // aggregated sold/exported (kWh)
    consumption: 980.0,   // aggregated bought/imported (kWh)
    inToday: 12.1,        // daily delta from Flux difference()
    outToday: 8.4,        // daily delta from Flux difference()
  });

  // % = production / consumption — can exceed 100%
  const vbatPercent = vbatData.consumption > 0
    ? (vbatData.production / vbatData.consumption) * 100
    : 0;

  // --- Color helpers ---
  const getPriceColor = (price) => {
    if (price < 0) return "#73BF69"; // green - negative = good
    if (price < 1.5) return "#73BF69";
    if (price < 3.0) return "#FF9830"; // orange
    return "#F2495C"; // red - expensive
  };

  const getRatioColor = (pct) => {
    if (pct >= 100) return "#73BF69";  // green - producing more than consuming
    if (pct >= 50) return "#FF9830";
    return "#F2495C";
  };

  const currentColor = getPriceColor(oteData.current.price);
  const ratioColor = getRatioColor(vbatPercent);

  // --- Gauge arc helper ---
  const GaugeArc = ({ percent, color, size = 100, strokeWidth = 8 }) => {
    const radius = (size - strokeWidth) / 2;
    const cx = size / 2;
    const cy = size / 2;

    // Arc from 135° to 405° (270° sweep)
    const startAngle = 135;
    const endAngle = 405;
    const sweepAngle = (endAngle - startAngle) * (percent / 100);

    const toRad = (deg) => (deg * Math.PI) / 180;

    const x1 = cx + radius * Math.cos(toRad(startAngle));
    const y1 = cy + radius * Math.sin(toRad(startAngle));

    const bgX2 = cx + radius * Math.cos(toRad(endAngle));
    const bgY2 = cy + radius * Math.sin(toRad(endAngle));

    const valEndAngle = startAngle + sweepAngle;
    const valX2 = cx + radius * Math.cos(toRad(valEndAngle));
    const valY2 = cy + radius * Math.sin(toRad(valEndAngle));

    const bgLargeArc = 1;
    const valLargeArc = sweepAngle > 180 ? 1 : 0;

    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <path
          d={`M ${x1} ${y1} A ${radius} ${radius} 0 ${bgLargeArc} 1 ${bgX2} ${bgY2}`}
          fill="none"
          stroke="#2a2a3e"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        {percent > 0 && (
          <path
            d={`M ${x1} ${y1} A ${radius} ${radius} 0 ${valLargeArc} 1 ${valX2} ${valY2}`}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
      </svg>
    );
  };

  // --- Price range bar ---
  const PriceBar = ({ min, max, current }) => {
    const range = max - min || 1;
    const pos = ((current - min) / range) * 100;
    return (
      <div
        style={{
          position: "relative",
          width: "100%",
          height: 6,
          background: "linear-gradient(to right, #73BF69, #FF9830, #F2495C)",
          borderRadius: 3,
          marginTop: 6,
          marginBottom: 2,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: `${Math.min(Math.max(pos, 2), 98)}%`,
            top: -3,
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: "#fff",
            border: `2px solid ${currentColor}`,
            transform: "translateX(-50%)",
          }}
        />
      </div>
    );
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        fontFamily:
          "'Inter', 'Helvetica Neue', Arial, sans-serif",
        color: "#d8d9da",
        background: "#181b1f",
        padding: 12,
        borderRadius: 8,
        width: 280,
      }}
    >
      {/* ========== OTE Panel ========== */}
      <div
        style={{
          background: "#1e2128",
          borderRadius: 6,
          padding: 14,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "#8e8ea0",
            }}
          >
            OTE Today
          </span>
          <span style={{ fontSize: 10, color: "#6e6e80" }}>CZK/kWh</span>
        </div>

        {/* Current price - hero */}
        <div style={{ textAlign: "center", marginBottom: 10 }}>
          <span
            style={{
              fontSize: 36,
              fontWeight: 700,
              color: currentColor,
              lineHeight: 1,
            }}
          >
            {oteData.current.price.toFixed(2)}
          </span>
          <div style={{ fontSize: 11, color: "#8e8ea0", marginTop: 2 }}>
            now · {oteData.current.hour}
          </div>
        </div>

        {/* Price range bar */}
        <PriceBar
          min={oteData.min.price}
          max={oteData.max.price}
          current={oteData.current.price}
        />

        {/* Min / Max row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 8,
          }}
        >
          <div>
            <div style={{ fontSize: 10, color: "#73BF69", fontWeight: 600 }}>
              MIN
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
              <span style={{ fontSize: 20, fontWeight: 700, color: "#73BF69" }}>
                {oteData.min.price.toFixed(2)}
              </span>
              <span style={{ fontSize: 11, color: "#6e6e80" }}>
                @{oteData.min.hour}
              </span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: "#F2495C", fontWeight: 600 }}>
              MAX
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
              <span style={{ fontSize: 20, fontWeight: 700, color: "#F2495C" }}>
                {oteData.max.price.toFixed(2)}
              </span>
              <span style={{ fontSize: 11, color: "#6e6e80" }}>
                @{oteData.max.hour}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ========== Virtual Battery Panel ========== */}
      <div
        style={{
          background: "#1e2128",
          borderRadius: 6,
          padding: 14,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 4,
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "#8e8ea0",
            }}
          >
            Virtual Battery
          </span>
        </div>

        {/* Gauge with % on top of kWh */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            margin: "0 auto",
            width: 140,
            height: 120,
          }}
        >
          <div style={{ position: "absolute", top: 0, left: "50%", transform: "translateX(-50%)" }}>
            <GaugeArc percent={Math.min(vbatPercent, 100)} color={ratioColor} size={140} strokeWidth={10} />
          </div>
          {/* Center text: ratio % over charge kWh */}
          <div
            style={{
              position: "absolute",
              top: "42%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: 32,
                fontWeight: 700,
                color: ratioColor,
                lineHeight: 1,
              }}
            >
              {vbatPercent.toFixed(0)}%
            </div>
            <div
              style={{
                fontSize: 14,
                color: "#8e8ea0",
                marginTop: 2,
                fontWeight: 500,
              }}
            >
              {vbatData.charge} kWh
            </div>
          </div>
        </div>

        {/* In / Out stats */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-around",
            marginTop: 4,
            paddingTop: 8,
            borderTop: "1px solid #2a2a3e",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#73BF69", fontWeight: 600 }}>
              ▲ SOLD
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#d8d9da" }}>
              {vbatData.inToday}
              <span style={{ fontSize: 11, color: "#6e6e80", marginLeft: 2 }}>
                kWh
              </span>
            </div>
          </div>
          <div
            style={{
              width: 1,
              background: "#2a2a3e",
              alignSelf: "stretch",
            }}
          />
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#FF9830", fontWeight: 600 }}>
              ▼ BOUGHT
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#d8d9da" }}>
              {vbatData.outToday}
              <span style={{ fontSize: 11, color: "#6e6e80", marginLeft: 2 }}>
                kWh
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OTE_VBAT_PANEL;