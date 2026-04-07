import React from 'react';

const styles = `
  .ov-panel {
    background: #181b1f;
    padding: 16px;
    border-radius: 8px;
    font-family: 'Inter', 'Helvetica Neue', sans-serif;
    color: #d8d9da;
    min-width: 220px;
  }
  .ov-card {
    background: #1e2128;
    border-radius: 6px;
    padding: 16px;
  }
  .ov-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
  }
  .ov-title {
    font-size: 14px;
    font-weight: 600;
    color: #d8d9da;
  }
  .ov-unit {
    font-size: 11px;
    color: #8e8e8e;
  }
  .ov-hero {
    font-size: 32px;
    font-weight: 700;
    color: #d8d9da;
    line-height: 1.1;
    margin-bottom: 2px;
  }
  .ov-sub {
    font-size: 12px;
    color: #8e8e8e;
    margin-bottom: 14px;
  }
  .ov-range-track {
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, #73BF69 0%, #FF9830 50%, #F2495C 100%);
    margin-bottom: 12px;
  }
  .ov-range-dot {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid #181b1f;
    box-shadow: 0 0 4px rgba(0,0,0,0.5);
  }
  .ov-extremes {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
  }
  .ov-min {
    color: #73BF69;
  }
  .ov-min-label {
    color: #8e8e8e;
    font-size: 10px;
  }
  .ov-max {
    color: #F2495C;
    text-align: right;
  }
  .ov-max-label {
    color: #8e8e8e;
    font-size: 10px;
  }
`;

const OTEPanel = () => {
  const currentPrice = 2.45;
  const minPrice = 1.23;
  const minTime = '3:00';
  const maxPrice = 4.56;
  const maxTime = '18:00';
  const currentHour = '14:00';
  const dotPct = 45;

  return (
    <>
      <style>{styles}</style>
      <div className="ov-panel">
        <div className="ov-card">
          <div className="ov-header">
            <span className="ov-title">OTE Today</span>
            <span className="ov-unit">CZK/kWh</span>
          </div>
          <div className="ov-hero">{currentPrice.toFixed(2)}</div>
          <div className="ov-sub">now &middot; {currentHour}</div>
          <div className="ov-range-track">
            <div
              className="ov-range-dot"
              style={{ left: `${dotPct}%` }}
            />
          </div>
          <div className="ov-extremes">
            <div className="ov-min">
              <div>MIN: {minPrice.toFixed(2)}</div>
              <div className="ov-min-label">@{minTime}</div>
            </div>
            <div className="ov-max">
              <div>MAX: {maxPrice.toFixed(2)}</div>
              <div className="ov-max-label">@{maxTime}</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default OTEPanel;
