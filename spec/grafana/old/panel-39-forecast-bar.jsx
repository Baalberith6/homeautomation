import React from 'react';

const ForecastBarPanel = () => {
  const width = 700;
  const height = 300;
  const padL = 50;
  const padR = 20;
  const padT = 40;
  const padB = 40;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  // 30-minute intervals from 5:00 to 18:00 = 26 intervals
  const intervals = [];
  for (let h = 5; h < 18; h++) {
    intervals.push(`${String(h).padStart(2, '0')}:00`);
    intervals.push(`${String(h).padStart(2, '0')}:30`);
  }
  intervals.push('18:00');

  const n = intervals.length;

  // Forecast (kWh per 30min interval)
  const forecast = [
    0, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0, 1.3, 1.6, 1.9, 2.1, 2.3, 2.5, 2.5,
    2.4, 2.3, 2.1, 1.8, 1.5, 1.2, 0.8, 0.5, 0.3, 0.1, 0.05, 0, 0,
  ].slice(0, n);

  // Actual generation
  const generation = [
    0, 0.04, 0.12, 0.25, 0.5, 0.8, 1.1, 1.4, 1.7, 2.0, 2.2, 2.4, 2.6, 2.3,
    2.1, 2.0, 1.9, 1.6, 1.3, 1.0, 0.7, 0.4, 0.2, 0.08, 0.03, 0, 0,
  ].slice(0, n);

  const maxVal = 3;

  function xPos(i) {
    return padL + (i / (n - 1)) * chartW;
  }
  function yPos(v) {
    return padT + chartH - (v / maxVal) * chartH;
  }

  const barGroupWidth = chartW / n;
  const barW = barGroupWidth * 0.35;

  const gridVals = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0];
  const labelEvery = 4; // show label every 4 intervals (2 hours)

  return (
    <div
      style={{
        background: '#181b1f',
        borderRadius: 8,
        padding: 8,
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
      }}
    >
      <div
        style={{
          color: '#d8d9da',
          fontSize: 14,
          fontWeight: 600,
          padding: '4px 8px 8px',
        }}
      >
        Power vs Forecast
      </div>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {/* Grid */}
        {gridVals.map((v) => (
          <g key={`gv-${v}`}>
            <line x1={padL} y1={yPos(v)} x2={width - padR} y2={yPos(v)} stroke="#2a2e35" strokeWidth={1} />
            <text x={padL - 8} y={yPos(v) + 4} fill="#8e8e8e" fontSize={10} textAnchor="end">
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {intervals.map((label, i) => {
          if (i % labelEvery !== 0) return null;
          return (
            <text
              key={`lbl-${i}`}
              x={xPos(i)}
              y={height - padB + 16}
              fill="#8e8e8e"
              fontSize={10}
              textAnchor="middle"
            >
              {label}
            </text>
          );
        })}
        {/* Bars */}
        {intervals.map((_, i) => {
          const cx = xPos(i);
          const fVal = forecast[i] || 0;
          const gVal = generation[i] || 0;
          return (
            <g key={`bars-${i}`}>
              {/* Forecast bar (green) */}
              <rect
                x={cx - barW - 1}
                y={yPos(fVal)}
                width={barW}
                height={yPos(0) - yPos(fVal)}
                fill="#73BF69"
                fillOpacity={0.8}
                rx={1}
              />
              {/* Generation bar (blue) */}
              <rect
                x={cx + 1}
                y={yPos(gVal)}
                width={barW}
                height={yPos(0) - yPos(gVal)}
                fill="#5794F2"
                fillOpacity={0.8}
                rx={1}
              />
            </g>
          );
        })}
        {/* Legend */}
        <rect x={padL + 10} y={padT + 5} width={10} height={10} rx={2} fill="#73BF69" fillOpacity={0.8} />
        <text x={padL + 24} y={padT + 14} fill="#8e8e8e" fontSize={10}>
          Forecast
        </text>
        <rect x={padL + 90} y={padT + 5} width={10} height={10} rx={2} fill="#5794F2" fillOpacity={0.8} />
        <text x={padL + 104} y={padT + 14} fill="#8e8e8e" fontSize={10}>
          Generation
        </text>
      </svg>
    </div>
  );
};

export default ForecastBarPanel;
