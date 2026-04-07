import React, { useState, useEffect } from "react";

// ---------- Mock data ----------
const MOCK = {
  temp: 18.4,
  hi: 23,
  lo: 14,
  humidity: 72,
  rain_fc: 2.1,
  rain_rate: 0.0,
  rain_total: 4.2,
  wind: 12,
  gust: 18,
  wind_30m: 15,
  gust_30m: 22,
};

// Hourly temperature forecast (0-23h): rises from 14 to 23 at 14h, falls to 16 at 23h
const HOURLY_TEMP = [
  { h: 0, v: 14.0 },
  { h: 1, v: 14.2 },
  { h: 2, v: 14.1 },
  { h: 3, v: 14.0 },
  { h: 4, v: 14.3 },
  { h: 5, v: 14.8 },
  { h: 6, v: 15.5 },
  { h: 7, v: 16.5 },
  { h: 8, v: 17.5 },
  { h: 9, v: 18.8 },
  { h: 10, v: 20.0 },
  { h: 11, v: 21.2 },
  { h: 12, v: 22.1 },
  { h: 13, v: 22.8 },
  { h: 14, v: 23.0 },
  { h: 15, v: 22.5 },
  { h: 16, v: 21.8 },
  { h: 17, v: 20.5 },
  { h: 18, v: 19.2 },
  { h: 19, v: 18.0 },
  { h: 20, v: 17.2 },
  { h: 21, v: 16.5 },
  { h: 22, v: 16.2 },
  { h: 23, v: 16.0 },
];

// Rain hourly mock (mm) - only non-zero hours
const HOURLY_RAIN = { 15: 0.5, 16: 1.2, 17: 0.8 };

// Wind hourly mock (km/h) - values 5-15 across the day
const HOURLY_WIND = [
  { h: 0, v: 5 },
  { h: 1, v: 5 },
  { h: 2, v: 6 },
  { h: 3, v: 6 },
  { h: 4, v: 7 },
  { h: 5, v: 7 },
  { h: 6, v: 8 },
  { h: 7, v: 9 },
  { h: 8, v: 10 },
  { h: 9, v: 11 },
  { h: 10, v: 12 },
  { h: 11, v: 13 },
  { h: 12, v: 14 },
  { h: 13, v: 15 },
  { h: 14, v: 14 },
  { h: 15, v: 13 },
  { h: 16, v: 12 },
  { h: 17, v: 11 },
  { h: 18, v: 10 },
  { h: 19, v: 9 },
  { h: 20, v: 8 },
  { h: 21, v: 7 },
  { h: 22, v: 6 },
  { h: 23, v: 5 },
];

// ---------- SVG chart dimensions ----------
const W = 680;
const H = 80;
const PAD_X = 8;
const PAD_Y = 14;
const PAD_BOT = 14;

// ---------- Helpers ----------
function pad02(n) {
  return String(n).padStart(2, "0");
}

function tempColor(temp) {
  if (temp <= 0) return "#4fc3f7";
  if (temp >= 30) return "#f2495c";
  return "#f2cc0c";
}

// Weather icon selection based on rain rate (matches panel 70 afterRender logic)
function WeatherIcon({ rainRate }) {
  if (rainRate > 1) {
    // Heavy rain: cloud with rain drops
    return (
      <svg width="36" height="36" viewBox="0 0 48 48" fill="none">
        <path
          d="M10 28a6 6 0 0 1 6-6h1a8 8 0 0 1 15.3-1.8A6 6 0 0 1 38 26v0a6 6 0 0 1-6 6H16a6 6 0 0 1-6-4z"
          fill="#8b8fa3"
          opacity="0.7"
        />
        <line x1="16" y1="33" x2="14" y2="39" stroke="#5794f2" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
        <line x1="24" y1="33" x2="22" y2="39" stroke="#5794f2" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
        <line x1="32" y1="33" x2="30" y2="39" stroke="#5794f2" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
      </svg>
    );
  }
  if (rainRate > 0) {
    // Light rain: double cloud layer, no drops
    return (
      <svg width="36" height="36" viewBox="0 0 48 48" fill="none">
        <path
          d="M12 32a7 7 0 0 1 7-7h1a9 9 0 0 1 17.5-2A7 7 0 0 1 38 30v0a7 7 0 0 1-7 7H19a7 7 0 0 1-7-5z"
          fill="#6b7085"
          opacity="0.6"
        />
        <path
          d="M8 36a6 6 0 0 1 6-6h1a8 8 0 0 1 15.3-1.8A6 6 0 0 1 36 34v0a6 6 0 0 1-6 6H14a6 6 0 0 1-6-4z"
          fill="#8b8fa3"
          opacity="0.8"
        />
      </svg>
    );
  }
  // Daytime: sun + partial cloud
  return (
    <svg width="36" height="36" viewBox="0 0 48 48" fill="none">
      <circle cx="18" cy="18" r="8" fill="#f2cc0c" opacity="0.8" />
      <path
        d="M16 34a8 8 0 0 1 8-8h4a6 6 0 0 1 6 6v0a6 6 0 0 1-6 6H22a6 6 0 0 1-6-4z"
        fill="#8b8fa3"
        opacity="0.7"
      />
    </svg>
  );
}

// ---------- Scale functions ----------
const temps = HOURLY_TEMP.map((p) => p.v);
const minV = Math.min(...temps) - 0.5;
const maxV = Math.max(...temps) + 0.5;

const wVals = HOURLY_WIND.map((p) => p.v);
const wMin = Math.min(...wVals);
const wMax = Math.max(...wVals) + 1;

function xS(h) {
  return PAD_X + (h / 23) * (W - 2 * PAD_X);
}

function yS(v) {
  return PAD_Y + ((maxV - v) / (maxV - minV)) * (H - PAD_Y - PAD_BOT);
}

function yW(v) {
  const wPadTop = PAD_Y + 4;
  const wPadBot = PAD_BOT + 4;
  return wPadTop + ((wMax - v) / (wMax - wMin)) * (H - wPadTop - wPadBot);
}

// Catmull-Rom spline path
function catmullRomPath(pts, yFn) {
  if (pts.length < 2) return "";
  let d = `M${xS(pts[0].h)},${yFn(pts[0].v)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const i0 = Math.max(0, i - 1);
    const i2 = i + 1;
    const i3 = Math.min(pts.length - 1, i + 2);

    const x1 = xS(pts[i].h);
    const y1 = yFn(pts[i].v);
    const x2 = xS(pts[i2].h);
    const y2 = yFn(pts[i2].v);

    const cpx1 = x1 + (xS(pts[i2].h) - xS(pts[i0].h)) / 6;
    const cpy1 = y1 + (yFn(pts[i2].v) - yFn(pts[i0].v)) / 6;
    const cpx2 = x2 - (xS(pts[i3].h) - xS(pts[i].h)) / 6;
    const cpy2 = y2 - (yFn(pts[i3].v) - yFn(pts[i].v)) / 6;

    d += ` C${cpx1},${cpy1} ${cpx2},${cpy2} ${x2},${y2}`;
  }
  return d;
}

// Interpolate Y at fractional hour
function interpolateY(nowH, pts, yFn) {
  for (let i = 0; i < pts.length - 1; i++) {
    if (nowH >= pts[i].h && nowH <= pts[i + 1].h) {
      const f = (nowH - pts[i].h) / (pts[i + 1].h - pts[i].h);
      return yFn(pts[i].v + (pts[i + 1].v - pts[i].v) * f);
    }
  }
  if (nowH <= pts[0].h) return yFn(pts[0].v);
  return yFn(pts[pts.length - 1].v);
}

// Pre-compute paths and indices
const tempLineD = catmullRomPath(HOURLY_TEMP, yS);
const tempAreaD =
  tempLineD +
  ` L${xS(HOURLY_TEMP[HOURLY_TEMP.length - 1].h)},${H} L${xS(HOURLY_TEMP[0].h)},${H} Z`;
const windLineD = catmullRomPath(HOURLY_WIND, yW);

const hiIdx = HOURLY_TEMP.reduce((best, p, i) => (p.v > HOURLY_TEMP[best].v ? i : best), 0);
const loIdx = HOURLY_TEMP.reduce((best, p, i) => (p.v < HOURLY_TEMP[best].v ? i : best), 0);
const wHiIdx = HOURLY_WIND.reduce((best, p, i) => (p.v > HOURLY_WIND[best].v ? i : best), 0);
const wLoIdx = HOURLY_WIND.reduce((best, p, i) => (p.v < HOURLY_WIND[best].v ? i : best), 0);

// Rain bar sizing
const maxRain = Math.max(0.1, ...Object.values(HOURLY_RAIN));
const barSlotW = (W - 2 * PAD_X) / 24;
const barW = barSlotW * 0.6;
const rainBarMaxH = (H - PAD_Y - PAD_BOT) * 0.6;

// Hour labels at 3h intervals
const hourLabels = HOURLY_TEMP.filter((p) => p.h % 3 === 0);

// ---------- Sparkline SVG component ----------
function SparklineSVG({ nowH }) {
  const nowX = xS(nowH);
  const nowTempY = interpolateY(nowH, HOURLY_TEMP, yS);
  const nowWindY = interpolateY(nowH, HOURLY_WIND, yW);

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      style={{ display: "block", width: "100%", height: "100%" }}
    >
      <defs>
        <linearGradient id="wwGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f2cc0c" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#f2cc0c" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Rain bars (purple) */}
      {Object.entries(HOURLY_RAIN).map(([hour, rv]) => {
        if (rv <= 0) return null;
        const bH = (rv / maxRain) * rainBarMaxH;
        const bX = xS(parseInt(hour, 10)) - barW / 2;
        const bY = H - PAD_BOT - bH;
        const op = (0.15 + (rv / maxRain) * 0.45).toFixed(2);
        return (
          <rect
            key={`rain-${hour}`}
            x={bX}
            y={bY}
            width={barW}
            height={bH}
            rx={barW / 2}
            fill="#B877D9"
            opacity={op}
          />
        );
      })}

      {/* Wind line (blue) */}
      <path
        d={windLineD}
        fill="none"
        stroke="#5794F2"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.6"
      />

      {/* Temp area gradient fill */}
      <path d={tempAreaD} fill="url(#wwGrad)" />

      {/* Temp line (yellow) */}
      <path
        d={tempLineD}
        fill="none"
        stroke="#f2cc0c"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* "Now" vertical dashed line */}
      <line
        x1={nowX}
        y1={PAD_Y}
        x2={nowX}
        y2={H - PAD_BOT}
        stroke="#f2cc0c"
        strokeWidth="0.5"
        strokeDasharray="2,2"
        opacity="0.4"
      />

      {/* Temp now dot (yellow) */}
      <circle cx={nowX} cy={nowTempY} r="8" fill="#f2cc0c" opacity="0.15" />
      <circle cx={nowX} cy={nowTempY} r="4.5" fill="#f2cc0c" />

      {/* Wind now dot (blue) */}
      <circle cx={nowX} cy={nowWindY} r="6" fill="#5794F2" opacity="0.12" />
      <circle cx={nowX} cy={nowWindY} r="3" fill="#5794F2" opacity="0.7" />

      {/* Wind hi/lo labels */}
      <text
        x={xS(HOURLY_WIND[wHiIdx].h)}
        y={yW(HOURLY_WIND[wHiIdx].v) - 5}
        textAnchor="middle"
        fill="#5794F2"
        fontSize="8"
        fontWeight="600"
        fontFamily="Inter,sans-serif"
        opacity="0.7"
      >
        {Math.round(HOURLY_WIND[wHiIdx].v)}
      </text>
      <text
        x={xS(HOURLY_WIND[wLoIdx].h)}
        y={yW(HOURLY_WIND[wLoIdx].v) + 12}
        textAnchor="middle"
        fill="#5794F2"
        fontSize="8"
        fontWeight="600"
        fontFamily="Inter,sans-serif"
        opacity="0.7"
      >
        {Math.round(HOURLY_WIND[wLoIdx].v)}
      </text>

      {/* Temp hi/lo labels */}
      <text
        x={xS(HOURLY_TEMP[hiIdx].h)}
        y={yS(HOURLY_TEMP[hiIdx].v) - 5}
        textAnchor="middle"
        fill="#FF9830"
        fontSize="9"
        fontWeight="600"
        fontFamily="Inter,sans-serif"
      >
        {HOURLY_TEMP[hiIdx].v.toFixed(1)}°
      </text>
      <text
        x={xS(HOURLY_TEMP[loIdx].h)}
        y={yS(HOURLY_TEMP[loIdx].v) - 5}
        textAnchor="middle"
        fill="#5794F2"
        fontSize="9"
        fontWeight="600"
        fontFamily="Inter,sans-serif"
      >
        {HOURLY_TEMP[loIdx].v.toFixed(1)}°
      </text>

      {/* Hour labels every 3h */}
      {hourLabels.map((p) => (
        <text
          key={`hr-${p.h}`}
          x={xS(p.h)}
          y={H - 2}
          textAnchor="middle"
          fill="#5a5e72"
          fontSize="8"
          fontFamily="Inter,sans-serif"
        >
          {pad02(p.h)}:00
        </text>
      ))}
    </svg>
  );
}

// ---------- Main component ----------
function WeatherPanel() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const nowH = now.getHours() + now.getMinutes() / 60;
  const tc = tempColor(MOCK.temp);

  return (
    <div className="ww" style={styles.root}>
      <style>{cssText}</style>

      {/* ---- Hero row ---- */}
      <div className="ww-hero" style={styles.hero}>
        <div className="ww-left" style={styles.left}>
          <div className="ww-icon">
            <WeatherIcon rainRate={MOCK.rain_rate} />
          </div>
          <div className="ww-temp-group" style={styles.tempGroup}>
            <span className="ww-temp" style={{ ...styles.temp, color: tc }}>
              {MOCK.temp}
            </span>
            <span className="ww-deg" style={{ ...styles.deg, color: tc }}>
              °C
            </span>
          </div>
          <div className="ww-hilo" style={styles.hilo}>
            <span className="ww-hi" style={styles.hi}>
              <span className="ww-hi-lbl" style={styles.hiloLbl}>
                Hi
              </span>
              {MOCK.hi}°
            </span>
            <span className="ww-lo" style={styles.lo}>
              <span className="ww-lo-lbl" style={styles.hiloLbl}>
                Lo
              </span>
              {MOCK.lo}°
            </span>
          </div>
        </div>
        <div className="ww-clock" style={styles.clock}>
          <span className="ww-clock-time" style={styles.clockTime}>
            {pad02(now.getHours())}:{pad02(now.getMinutes())}:{pad02(now.getSeconds())}
          </span>
          <span className="ww-clock-date" style={styles.clockDate}>
            {pad02(now.getDate())}.{pad02(now.getMonth() + 1)}.
            {String(now.getFullYear()).slice(2)}
          </span>
        </div>
      </div>

      {/* ---- Sparkline chart ---- */}
      <div className="ww-spark" style={styles.spark}>
        <SparklineSVG nowH={nowH} />
      </div>

      {/* ---- Bottom stats bar ---- */}
      <div className="ww-stats" style={styles.stats}>
        {/* Humidity */}
        <div className="ww-stat" style={{ ...styles.stat, flex: 0.67 }}>
          <span className="ww-label" style={styles.label}>
            Humidity
          </span>
          <span
            className="ww-val ww-blue"
            style={{ ...styles.val, color: "#5794F2" }}
          >
            {MOCK.humidity}
            <span className="ww-unit" style={styles.unit}>
              %
            </span>
          </span>
        </div>

        <div className="ww-sep" style={styles.sep} />

        {/* Wind: current + 30m max */}
        <div
          className="ww-stat"
          style={{
            ...styles.stat,
            flexDirection: "row",
            gap: "6px",
            justifyContent: "space-between",
            padding: "2px 8px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <span className="ww-label" style={styles.label}>
              Wind{" "}
              <span className="ww-unit" style={styles.unit}>
                km/h
              </span>
            </span>
            <span className="ww-val" style={styles.val}>
              {MOCK.wind}
              <span className="ww-sub" style={styles.sub}>
                {" "}
                / {MOCK.gust}
              </span>
            </span>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <span className="ww-label" style={styles.label}>
              30m{" "}
              <span className="ww-unit" style={styles.unit}>
                km/h
              </span>
            </span>
            <span
              className="ww-val ww-orange"
              style={{ ...styles.val, color: "#FF9830" }}
            >
              {MOCK.wind_30m}
              <span className="ww-sub-orange" style={styles.subOrange}>
                {" "}
                / {MOCK.gust_30m}
              </span>
            </span>
          </div>
        </div>

        <div className="ww-sep" style={styles.sep} />

        {/* Rain: rate + forecast + total */}
        <div className="ww-stat" style={styles.stat}>
          <span className="ww-label" style={styles.label}>
            Rain
          </span>
          <div className="ww-rain-row" style={styles.rainRow}>
            <div className="ww-rain-item" style={styles.rainItem}>
              <span className="ww-rain-val" style={styles.rainVal}>
                {MOCK.rain_rate}
              </span>
              <span className="ww-rain-unit" style={styles.rainUnit}>
                mm/h
              </span>
            </div>
            <div className="ww-rain-item" style={styles.rainItem}>
              <span className="ww-rain-val" style={styles.rainVal}>
                {MOCK.rain_fc}
              </span>
              <span className="ww-rain-unit" style={styles.rainUnit}>
                fc
              </span>
            </div>
            <div className="ww-rain-item" style={styles.rainItem}>
              <span className="ww-rain-val" style={styles.rainVal}>
                {MOCK.rain_total}
              </span>
              <span className="ww-rain-unit" style={styles.rainUnit}>
                tot
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Injected CSS (matches original .ww- class styles) ----------
const cssText = `
.ww {
  font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
  color: #e8e8e8;
}
`;

// ---------- Inline styles (vw-based for responsive scaling, matching panel 70 CSS) ----------
const styles = {
  root: {
    fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
    color: "#e8e8e8",
    background: "#181b1f",
    borderRadius: 8,
    padding: "8px 12px",
    overflow: "hidden",
  },
  hero: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "2px",
  },
  left: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  tempGroup: {
    display: "flex",
    alignItems: "baseline",
    gap: "2px",
  },
  temp: {
    fontSize: "4.7vw",
    fontWeight: 800,
    color: "#f2cc0c",
    lineHeight: 1,
    letterSpacing: "-0.03em",
  },
  deg: {
    fontSize: "2.1vw",
    fontWeight: 700,
    color: "#f2cc0c",
    opacity: 0.7,
  },
  hilo: {
    display: "flex",
    flexDirection: "column",
    gap: "1px",
    marginLeft: "6px",
  },
  hi: {
    fontSize: "1.4vw",
    color: "#FF9830",
    fontWeight: 700,
  },
  lo: {
    fontSize: "1.4vw",
    color: "#5794F2",
    fontWeight: 700,
  },
  hiloLbl: {
    fontSize: "0.9vw",
    color: "#5a5e72",
    marginRight: "3px",
  },
  clock: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
  },
  clockTime: {
    fontSize: "2.75vw",
    fontWeight: 700,
    color: "#e8e8e8",
    fontVariantNumeric: "tabular-nums",
    letterSpacing: "-0.02em",
    lineHeight: 1,
  },
  clockDate: {
    fontSize: "1.35vw",
    color: "#e8e8e8",
    fontWeight: 500,
    fontVariantNumeric: "tabular-nums",
  },
  spark: {
    margin: "0 -4px 2px",
    height: "80px",
  },
  stats: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "stretch",
    background: "#111217",
    borderRadius: "6px",
    padding: "4px 12px",
    gap: 0,
  },
  stat: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 0,
    flex: 1,
    padding: "2px 4px",
  },
  label: {
    fontSize: "1.16vw",
    color: "#5a5e72",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    fontWeight: 500,
    lineHeight: 1.2,
  },
  val: {
    fontSize: "3.63vw",
    fontWeight: 700,
    color: "#e8e8e8",
    lineHeight: 1.15,
  },
  unit: {
    fontSize: "1.32vw",
    color: "#5a5e72",
    fontWeight: 500,
  },
  sub: {
    fontSize: "1.82vw",
    color: "#5a5e72",
    fontWeight: 500,
  },
  subOrange: {
    fontSize: "1.82vw",
    color: "#FF9830",
    fontWeight: 600,
  },
  sep: {
    width: "1px",
    background: "#2a2d35",
    alignSelf: "stretch",
    margin: "2px 0",
  },
  rainRow: {
    display: "flex",
    gap: "8px",
    alignItems: "baseline",
    justifyContent: "center",
  },
  rainItem: {
    display: "flex",
    alignItems: "baseline",
    gap: "2px",
  },
  rainVal: {
    fontSize: "2.64vw",
    fontWeight: 700,
    color: "#B877D9",
  },
  rainUnit: {
    fontSize: "1.16vw",
    color: "#5a5e72",
  },
};

export default WeatherPanel;
