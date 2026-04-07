import React from 'react';

const PowerPanel = () => {
  const width = 700;
  const height = 320;
  const padL = 55;
  const padR = 20;
  const padT = 40;
  const padB = 40;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const hours = Array.from({ length: 25 }, (_, i) => i);

  // Power (PV generation) - peaks midday ~5kW
  const powerData = [
    0, 0, 0, 0, 0, 0.1, 0.4, 1.0, 2.0, 3.2, 4.2, 4.8, 5.0, 4.7, 4.0, 3.0,
    2.0, 1.0, 0.3, 0.05, 0, 0, 0, 0, 0,
  ];

  // Consumption - relatively flat ~1.5kW
  const consumptionData = [
    0.8, 0.7, 0.6, 0.6, 0.7, 0.9, 1.2, 1.5, 1.6, 1.4, 1.3, 1.5, 1.8, 1.6,
    1.4, 1.5, 1.8, 2.2, 2.5, 2.0, 1.5, 1.2, 1.0, 0.9, 0.8,
  ];

  // Battery load - charges during day, discharges at night
  const batteryData = [
    -0.5, -0.4, -0.3, -0.2, -0.1, 0, 0.2, 0.5, 1.0, 1.5, 2.0, 2.2, 2.0,
    1.5, 1.0, 0.5, 0, -0.3, -0.5, -0.8, -0.7, -0.6, -0.5, -0.5, -0.5,
  ];

  // Bojlery (hot water heaters)
  const bojleryData = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.5, 1.5, 2.0, 2.0, 1.5, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
  ];

  const allValues = [
    ...powerData,
    ...consumptionData,
    ...batteryData,
    ...bojleryData,
  ];
  const minVal = Math.min(...allValues) - 0.5;
  const maxVal = Math.max(...allValues) + 0.5;
  const valRange = maxVal - minVal;

  function x(h) {
    return padL + (h / 24) * chartW;
  }
  function y(val) {
    return padT + chartH - ((val - minVal) / valRange) * chartH;
  }

  function makePath(data) {
    return data
      .map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
      .join(' ');
  }

  function makeFill(data, color) {
    const path = data
      .map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`)
      .join(' ');
    const baseline = y(0);
    return `M${x(0).toFixed(1)},${baseline} ${path.split(' ').map((p, i) => `L${p}`).join(' ')} L${x(24).toFixed(1)},${baseline} Z`;
  }

  const series = [
    { name: 'power', data: powerData, color: '#73C0DE', width: 1 },
    { name: 'consumption', data: consumptionData, color: '#73BF69', width: 1 },
    { name: 'battery_load', data: batteryData, color: '#F2CC0C', width: 1 },
    { name: 'bojlery', data: bojleryData, color: '#FF9830', width: 1 },
  ];

  const gridVals = [-1, 0, 1, 2, 3, 4, 5];
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
        Power
      </div>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          {series.map((s) => (
            <linearGradient key={`grad-${s.name}`} id={`fill-${s.name}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.2} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        {/* Grid */}
        {gridVals.map((v) => (
          <g key={`gv-${v}`}>
            <line x1={padL} y1={y(v)} x2={width - padR} y2={y(v)} stroke="#2a2e35" strokeWidth={1} />
            <text x={padL - 8} y={y(v) + 4} fill="#8e8e8e" fontSize={11} textAnchor="end">
              {v} kW
            </text>
          </g>
        ))}
        {gridHours.map((h) => (
          <g key={`gh-${h}`}>
            <line x1={x(h)} y1={padT} x2={x(h)} y2={height - padB} stroke="#2a2e35" strokeWidth={1} />
            <text x={x(h)} y={height - padB + 18} fill="#8e8e8e" fontSize={11} textAnchor="middle">
              {String(h).padStart(2, '0')}:00
            </text>
          </g>
        ))}
        {/* Zero line */}
        <line x1={padL} y1={y(0)} x2={width - padR} y2={y(0)} stroke="#555" strokeWidth={1} strokeDasharray="4,3" />
        {/* Filled areas and lines */}
        {series.map((s) => {
          const pts = s.data.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
          const fillPath = `M${x(0).toFixed(1)},${y(0).toFixed(1)} L${pts.split(' ').map((p) => p).join(' L')} L${x(24).toFixed(1)},${y(0).toFixed(1)} Z`;
          return (
            <g key={s.name}>
              <path d={fillPath} fill={`url(#fill-${s.name})`} />
              <path d={makePath(s.data)} fill="none" stroke={s.color} strokeWidth={s.width} />
            </g>
          );
        })}
        {/* Legend */}
        {series.map((s, i) => (
          <g key={`leg-${s.name}`}>
            <rect x={padL + 10 + i * 120} y={padT + 5} width={12} height={4} rx={2} fill={s.color} />
            <text x={padL + 26 + i * 120} y={padT + 10} fill="#8e8e8e" fontSize={10}>
              {s.name}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
};

export default PowerPanel;
