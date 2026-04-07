import React from 'react';

const TempStatPanel = () => {
  const value = 18.4;
  const unit = '\u00B0C';
  const maxTemp = 40;
  const minTemp = -10;
  const pct = (value - minTemp) / (maxTemp - minTemp);

  // Continuous BlYlRd
  function getColor(p) {
    if (p < 0.33) {
      const t = p / 0.33;
      const r = Math.round(50 + t * 205);
      const g = Math.round(100 + t * 155);
      const b = Math.round(200 - t * 180);
      return `rgb(${r},${g},${b})`;
    } else if (p < 0.66) {
      const t = (p - 0.33) / 0.33;
      return `rgb(255,${Math.round(255 - t * 180)},${Math.round(20 + t * 10)})`;
    } else {
      const t = (p - 0.66) / 0.34;
      return `rgb(${Math.round(255 - t * 40)},${Math.round(75 - t * 50)},30)`;
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
        Temp
      </div>
      <div
        style={{
          color: valueColor,
          fontSize: 36,
          fontWeight: 700,
          lineHeight: 1.1,
        }}
      >
        {value.toFixed(1)}
      </div>
      <div style={{ color: '#8e8e8e', fontSize: 12, marginTop: 4 }}>{unit}</div>
    </div>
  );
};

export default TempStatPanel;
