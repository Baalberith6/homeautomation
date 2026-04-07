import React from 'react';

const ForecastLinePanel = () => {
  const width = 500;
  const height = 300;
  const padL = 50;
  const padR = 20;
  const padT = 40;
  const padB = 40;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  // Hours from 5 to 18
  const hours = Array.from({ length: 14 }, (_, i) => i + 5);
  const minH = 5;
  const maxH = 18;
  const maxVal = 6;

  function xPos(h) {
    return padL + ((h - minH) / (maxH - minH)) * chartW;
  }
  function yPos(v) {
    return padT + chartH - (v / maxVal) * chartH;
  }

  // Forecast percentiles
  const p10 = [0, 0.1, 0.3, 0.8, 1.5, 2.2, 3.0, 3.2, 3.0, 2.2, 1.5, 0.8, 0.2, 0];
  const p50 = [0.1, 0.3, 0.8, 1.8, 2.8, 3.8, 4.5, 4.6, 4.2, 3.5, 2.5, 1.5, 0.5, 0.1];
  const p90 = [0.2, 0.6, 1.5, 2.8, 4.0, 5.0, 5.5, 5.6, 5.2, 4.5, 3.5, 2.2, 0.8, 0.2];

  // Actual generation (bars)
  const actual = [0.15, 0.4, 0.9, 2.0, 3.0, 4.0, 4.8, 4.5, 4.0, 3.2, 2.0, 1.2, 0.4, 0.05];

  // Build band path (p10 forward, p90 backward)
  const bandPath = hours
    .map((h, i) => `${i === 0 ? 'M' : 'L'}${xPos(h).toFixed(1)},${yPos(p10[i]).toFixed(1)}`)
    .join(' ')
    + ' '
    + [...hours].reverse()
      .map((h, i) => `L${xPos(h).toFixed(1)},${yPos(p90[hours.length - 1 - i]).toFixed(1)}`)
      .join(' ')
    + ' Z';

  const p50Path = hours
    .map((h, i) => `${i === 0 ? 'M' : 'L'}${xPos(h).toFixed(1)},${yPos(p50[i]).toFixed(1)}`)
    .join(' ');

  const barWidth = (chartW / hours.length) * 0.6;

  const gridVals = [0, 1, 2, 3, 4, 5, 6];
  const gridHours = [5, 8, 11, 14, 17];

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
            <text x={padL - 8} y={yPos(v) + 4} fill="#8e8e8e" fontSize={11} textAnchor="end">
              {v} kW
            </text>
          </g>
        ))}
        {gridHours.map((h) => (
          <g key={`gh-${h}`}>
            <line x1={xPos(h)} y1={padT} x2={xPos(h)} y2={height - padB} stroke="#2a2e35" strokeWidth={1} />
            <text x={xPos(h)} y={height - padB + 18} fill="#8e8e8e" fontSize={11} textAnchor="middle">
              {String(h).padStart(2, '0')}:00
            </text>
          </g>
        ))}
        {/* Forecast band (10p-90p) */}
        <path d={bandPath} fill="#73BF69" fillOpacity={0.15} stroke="none" />
        {/* Forecast 50p line */}
        <path d={p50Path} fill="none" stroke="#73BF69" strokeWidth={2} />
        {/* Actual bars */}
        {hours.map((h, i) => (
          <rect
            key={`bar-${h}`}
            x={xPos(h) - barWidth / 2}
            y={yPos(actual[i])}
            width={barWidth}
            height={yPos(0) - yPos(actual[i])}
            fill="#5794F2"
            fillOpacity={0.7}
            rx={2}
          />
        ))}
        {/* Legend */}
        <rect x={padL + 10} y={padT + 5} width={12} height={8} rx={2} fill="#73BF69" fillOpacity={0.15} stroke="#73BF69" strokeWidth={1} />
        <text x={padL + 26} y={padT + 13} fill="#8e8e8e" fontSize={10}>
          Forecast 10p-90p
        </text>
        <line x1={padL + 140} y1={padT + 9} x2={padL + 152} y2={padT + 9} stroke="#73BF69" strokeWidth={2} />
        <text x={padL + 156} y={padT + 13} fill="#8e8e8e" fontSize={10}>
          50p
        </text>
        <rect x={padL + 186} y={padT + 5} width={8} height={8} rx={2} fill="#5794F2" fillOpacity={0.7} />
        <text x={padL + 198} y={padT + 13} fill="#8e8e8e" fontSize={10}>
          Actual
        </text>
      </svg>
    </div>
  );
};

export default ForecastLinePanel;
