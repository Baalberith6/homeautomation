import React from 'react';

const BatteryLifePanel = () => {
  const cycles = 342;
  const soh = 98;

  return (
    <div
      style={{
        background: '#181b1f',
        borderRadius: 8,
        padding: 16,
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
        textAlign: 'center',
        minWidth: 140,
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
        FVE Battery life
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ color: '#8e8e8e', fontSize: 11, marginBottom: 2 }}>Cycles</div>
        <div style={{ color: '#d8d9da', fontSize: 28, fontWeight: 700 }}>{cycles}</div>
      </div>
      <div>
        <div style={{ color: '#8e8e8e', fontSize: 11, marginBottom: 2 }}>SOH</div>
        <div style={{ color: '#d8d9da', fontSize: 28, fontWeight: 700 }}>{soh}%</div>
      </div>
    </div>
  );
};

export default BatteryLifePanel;
