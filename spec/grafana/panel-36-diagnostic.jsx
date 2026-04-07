import React from 'react';

const DiagnosticPanel = () => {
  const message = 'Normal operation';
  const value = 0; // threshold: 0=green, >=80=red
  const isAlert = value >= 80;
  const statusColor = isAlert ? '#F2495C' : '#73BF69';

  return (
    <div
      style={{
        background: '#181b1f',
        borderRadius: 8,
        padding: 16,
        fontFamily: "'Inter', 'Helvetica Neue', sans-serif",
        textAlign: 'center',
        minWidth: 180,
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
        Diagnostic message
      </div>
      <div
        style={{
          display: 'inline-block',
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: statusColor,
          marginBottom: 8,
          boxShadow: `0 0 8px ${statusColor}`,
        }}
      />
      <div
        style={{
          color: statusColor,
          fontSize: 22,
          fontWeight: 600,
          lineHeight: 1.3,
        }}
      >
        {message}
      </div>
    </div>
  );
};

export default DiagnosticPanel;
