import React from 'react';

const FVEPhasesPanel = () => {
  const phases = [
    { label: 'Phase 1', desc: 'traktor, KL, pracka', value: 4.2, unit: 'A' },
    { label: 'Phase 2', desc: 'mycka', value: 1.8, unit: 'A' },
    { label: 'Phase 3', desc: 'AC, trouba', value: 6.1, unit: 'A' },
  ];

  const maxValue = 10; // max scale for bar gauge

  // Continuous BlYlRd color mapping
  function getColor(pct) {
    if (pct < 0.33) {
      // Blue to Yellow
      const t = pct / 0.33;
      const r = Math.round(50 + t * 205);
      const g = Math.round(100 + t * 155);
      const b = Math.round(200 - t * 180);
      return `rgb(${r},${g},${b})`;
    } else if (pct < 0.66) {
      // Yellow to Red
      const t = (pct - 0.33) / 0.33;
      const r = Math.round(255);
      const g = Math.round(255 - t * 180);
      const b = Math.round(20 + t * 10);
      return `rgb(${r},${g},${b})`;
    } else {
      // Deep red
      const t = (pct - 0.66) / 0.34;
      const r = Math.round(255 - t * 40);
      const g = Math.round(75 - t * 50);
      const b = Math.round(30);
      return `rgb(${r},${g},${b})`;
    }
  }

  return (
    <div
      style={{
        background: '#181b1f',
        borderRadius: 8,
        padding: 16,
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
        minWidth: 250,
      }}
    >
      <div
        style={{
          color: '#d8d9da',
          fontSize: 14,
          fontWeight: 600,
          marginBottom: 16,
        }}
      >
        FVE phases
      </div>
      {phases.map((phase) => {
        const pct = phase.value / maxValue;
        const barColor = getColor(pct);
        const gradientStops = Array.from({ length: 20 }, (_, i) => {
          const p = i / 19;
          return `${getColor(p * pct)} ${(p * 100).toFixed(0)}%`;
        }).join(', ');

        return (
          <div key={phase.label} style={{ marginBottom: 14 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                marginBottom: 4,
              }}
            >
              <div>
                <span style={{ color: '#d8d9da', fontSize: 13, fontWeight: 500 }}>
                  {phase.label}
                </span>
                <span style={{ color: '#8e8e8e', fontSize: 11, marginLeft: 8 }}>
                  {phase.desc}
                </span>
              </div>
              <span style={{ color: barColor, fontSize: 18, fontWeight: 700 }}>
                {phase.value} {phase.unit}
              </span>
            </div>
            <div
              style={{
                height: 10,
                borderRadius: 5,
                background: '#2a2e35',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${pct * 100}%`,
                  borderRadius: 5,
                  background: `linear-gradient(90deg, ${gradientStops})`,
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default FVEPhasesPanel;
