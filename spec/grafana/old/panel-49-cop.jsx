import React from 'react';

const COPPanel = () => {
  const value = 3.21;
  const maxCOP = 5;
  const pct = value / maxCOP;

  // Continuous RdYlGr (Red-Yellow-Green) - higher is better
  function getColor(p) {
    if (p < 0.33) {
      // Red to Yellow
      const t = p / 0.33;
      return `rgb(${Math.round(242 - t * 20)},${Math.round(73 + t * 182)},${Math.round(92 - t * 72)})`;
    } else if (p < 0.66) {
      // Yellow to Green
      const t = (p - 0.33) / 0.33;
      return `rgb(${Math.round(222 - t * 107)},${Math.round(255 - t * 64)},${Math.round(20 + t * 49)})`;
    } else {
      // Deep green
      const t = (p - 0.66) / 0.34;
      return `rgb(${Math.round(115 - t * 60)},${Math.round(191 - t * 30)},${Math.round(69 - t * 24)})`;
    }
  }

  const valueColor = getColor(pct);

  return (
    <div
      style={{
        background: '#181b1f',
        borderRadius: 8,
        padding: 16,
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
        textAlign: 'center',
        minWidth: 120,
      }}
    >
      <div
        style={{
          color: '#d8d9da',
          fontSize: 13,
          fontWeight: 600,
          marginBottom: 16,
        }}
      >
        COP timewindow
      </div>
      <div
        style={{
          color: valueColor,
          fontSize: 36,
          fontWeight: 700,
          lineHeight: 1.1,
        }}
      >
        {value.toFixed(2)}
      </div>
      <div style={{ color: '#8e8e8e', fontSize: 12, marginTop: 4 }}>COP</div>
    </div>
  );
};

export default COPPanel;
