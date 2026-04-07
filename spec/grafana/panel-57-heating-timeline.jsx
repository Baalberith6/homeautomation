import React from 'react';

const HeatingTimelinePanel = () => {
  const width = 700;
  const height = 280;
  const padL = 120;
  const padR = 20;
  const padT = 40;
  const padB = 30;
  const chartW = width - padL - padR;
  const chartH = height - padT - padB;

  const zones = [
    'rehau_obyvak',
    'rehau_kuchyn',
    'netatmo_loznice',
    'netatmo_detsky',
    'rehau_koupelna',
  ];

  const zoneLabels = [
    'Obyvak',
    'Kuchyn',
    'Loznice',
    'Detsky',
    'Koupelna',
  ];

  // Color thresholds: 0=red, 0.2=light-green, 0.5=green, 0.7=dark-green, 0.9=darker-green
  function getStateColor(val) {
    if (val >= 0.9) return '#1a6d1a';
    if (val >= 0.7) return '#2d8c2d';
    if (val >= 0.5) return '#37872D';
    if (val >= 0.2) return '#96D98D';
    return '#F2495C';
  }

  // Mock data: each zone has an array of {start, end, value} segments over 24h
  const zoneData = [
    // Obyvak
    [
      { s: 0, e: 6, v: 0 },
      { s: 6, e: 8, v: 0.7 },
      { s: 8, e: 10, v: 0.5 },
      { s: 10, e: 14, v: 0.2 },
      { s: 14, e: 17, v: 0.5 },
      { s: 17, e: 21, v: 0.9 },
      { s: 21, e: 24, v: 0 },
    ],
    // Kuchyn
    [
      { s: 0, e: 6, v: 0 },
      { s: 6, e: 9, v: 0.9 },
      { s: 9, e: 12, v: 0.5 },
      { s: 12, e: 14, v: 0.7 },
      { s: 14, e: 18, v: 0.2 },
      { s: 18, e: 20, v: 0.7 },
      { s: 20, e: 24, v: 0 },
    ],
    // Loznice
    [
      { s: 0, e: 7, v: 0.5 },
      { s: 7, e: 9, v: 0 },
      { s: 9, e: 16, v: 0 },
      { s: 16, e: 22, v: 0 },
      { s: 22, e: 24, v: 0.7 },
    ],
    // Detsky
    [
      { s: 0, e: 6, v: 0.5 },
      { s: 6, e: 8, v: 0.2 },
      { s: 8, e: 15, v: 0 },
      { s: 15, e: 20, v: 0.5 },
      { s: 20, e: 24, v: 0.7 },
    ],
    // Koupelna
    [
      { s: 0, e: 5, v: 0 },
      { s: 5, e: 7, v: 0.9 },
      { s: 7, e: 16, v: 0 },
      { s: 16, e: 18, v: 0.7 },
      { s: 18, e: 20, v: 0.9 },
      { s: 20, e: 24, v: 0 },
    ],
  ];

  const rowH = chartH / zones.length;
  const rowPad = 3;

  function xPos(h) {
    return padL + (h / 24) * chartW;
  }

  const gridHours = [0, 3, 6, 9, 12, 15, 18, 21, 24];

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
        Heating Timeline
      </div>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {/* Grid lines */}
        {gridHours.map((h) => (
          <g key={`g-${h}`}>
            <line
              x1={xPos(h)}
              y1={padT}
              x2={xPos(h)}
              y2={height - padB}
              stroke="#2a2e35"
              strokeWidth={1}
            />
            <text
              x={xPos(h)}
              y={height - padB + 16}
              fill="#8e8e8e"
              fontSize={10}
              textAnchor="middle"
            >
              {String(h % 24).padStart(2, '0')}:00
            </text>
          </g>
        ))}
        {/* Zone rows */}
        {zones.map((zone, zi) => {
          const yBase = padT + zi * rowH;
          return (
            <g key={zone}>
              {/* Zone label */}
              <text
                x={padL - 8}
                y={yBase + rowH / 2 + 4}
                fill="#d8d9da"
                fontSize={11}
                textAnchor="end"
              >
                {zoneLabels[zi]}
              </text>
              {/* State segments */}
              {zoneData[zi].map((seg, si) => (
                <rect
                  key={`${zone}-${si}`}
                  x={xPos(seg.s)}
                  y={yBase + rowPad}
                  width={xPos(seg.e) - xPos(seg.s)}
                  height={rowH - rowPad * 2}
                  fill={getStateColor(seg.v)}
                  rx={2}
                />
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default HeatingTimelinePanel;
