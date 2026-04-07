import React from 'react';

const TCTempPanel = () => {
  const width = 600;
  const height = 300;
  const padL = 50;
  const padR = 20;
  const padT = 40;
  const padB = 40;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  // 24 hours of data
  const hours = Array.from({ length: 25 }, (_, i) => i);

  // Target temp: stays around 45C
  const targetData = hours.map((h) => {
    if (h >= 6 && h <= 22) return 45;
    return 42;
  });

  // Becka tC: fluctuates 30-65
  const beckaData = [
    35, 33, 31, 30, 32, 34, 40, 48, 55, 60, 63, 65, 62, 58, 52, 48, 45, 50,
    55, 58, 52, 46, 40, 37, 35,
  ];

  const minTemp = 25;
  const maxTemp = 70;
  const tempRange = maxTemp - minTemp;

  function x(h) {
    return padL + (h / 24) * chartW;
  }
  function y(temp) {
    return padT + chartH - ((temp - minTemp) / tempRange) * chartH;
  }

  const targetPath = targetData
    .map((t, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(t).toFixed(1)}`)
    .join(' ');

  const beckaPath = beckaData
    .map((t, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(t).toFixed(1)}`)
    .join(' ');

  const gridTemps = [30, 40, 50, 60, 70];
  const gridHours = [0, 4, 8, 12, 16, 20, 24];

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
        TC - TEMP
      </div>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {/* Grid lines */}
        {gridTemps.map((t) => (
          <g key={`gt-${t}`}>
            <line
              x1={padL}
              y1={y(t)}
              x2={width - padR}
              y2={y(t)}
              stroke="#2a2e35"
              strokeWidth={1}
            />
            <text x={padL - 8} y={y(t) + 4} fill="#8e8e8e" fontSize={11} textAnchor="end">
              {t}&deg;
            </text>
          </g>
        ))}
        {gridHours.map((h) => (
          <g key={`gh-${h}`}>
            <line
              x1={x(h)}
              y1={padT}
              x2={x(h)}
              y2={height - padB}
              stroke="#2a2e35"
              strokeWidth={1}
            />
            <text
              x={x(h)}
              y={height - padB + 18}
              fill="#8e8e8e"
              fontSize={11}
              textAnchor="middle"
            >
              {String(h).padStart(2, '0')}:00
            </text>
          </g>
        ))}
        {/* Target temp line (dark green, thick) */}
        <path d={targetPath} fill="none" stroke="#37872D" strokeWidth={5} strokeLinejoin="round" />
        {/* Becka tC line (orange) */}
        <path d={beckaPath} fill="none" stroke="#FF9830" strokeWidth={2} strokeLinejoin="round" />
        {/* Legend */}
        <rect x={padL + 10} y={padT + 5} width={12} height={4} rx={2} fill="#37872D" />
        <text x={padL + 26} y={padT + 10} fill="#8e8e8e" fontSize={10}>
          target_temp
        </text>
        <rect x={padL + 110} y={padT + 5} width={12} height={4} rx={2} fill="#FF9830" />
        <text x={padL + 126} y={padT + 10} fill="#8e8e8e" fontSize={10}>
          becka tC
        </text>
      </svg>
    </div>
  );
};

export default TCTempPanel;
