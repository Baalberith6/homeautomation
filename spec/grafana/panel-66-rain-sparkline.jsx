import React from 'react';

const RainSparklinePanel = () => {
  const width = 200;
  const height = 80;
  const pad = 4;
  const chartW = width - pad * 2;
  const chartH = height - pad * 2;

  // 24 hours of rain rate data with a few spikes
  const data = [
    0, 0, 0, 0, 0.1, 0.3, 0, 0, 0, 0.5, 1.2, 2.5, 1.8, 0.4, 0, 0, 0, 0.2,
    0.8, 1.5, 3.0, 2.0, 0.6, 0,
  ];

  const maxVal = Math.max(...data) || 1;
  const n = data.length;

  function x(i) {
    return pad + (i / (n - 1)) * chartW;
  }
  function y(v) {
    return pad + chartH - (v / maxVal) * chartH;
  }

  const linePath = data
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
    .join(' ');

  const fillPath =
    `M${x(0).toFixed(1)},${(pad + chartH).toFixed(1)} ` +
    data.map((v, i) => `L${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ') +
    ` L${x(n - 1).toFixed(1)},${(pad + chartH).toFixed(1)} Z`;

  return (
    <div
      style={{
        background: 'transparent',
        borderRadius: 4,
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
        overflow: 'hidden',
      }}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ display: 'block' }}
      >
        {/* Fill area */}
        <path d={fillPath} fill="#B877D9" fillOpacity={0.1} />
        {/* Line */}
        <path d={linePath} fill="none" stroke="#B877D9" strokeWidth={1} />
      </svg>
    </div>
  );
};

export default RainSparklinePanel;
