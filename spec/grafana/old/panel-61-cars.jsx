import React from 'react';

const styles = `
  .car-panel {
    background: #181b1f;
    padding: 12px;
    border-radius: 8px;
    font-family: 'Inter', 'Helvetica Neue', sans-serif;
    color: #d8d9da;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .car-card {
    background: #1e2228;
    border-radius: 6px;
    padding: 12px 14px;
  }
  .car-row1 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .car-name {
    font-size: 1.9vw;
    font-weight: 600;
    color: #d8d9da;
    width: 5.5vw;
    flex-shrink: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .car-bar-container {
    flex: 1;
    height: 14px;
    border-radius: 7px;
    position: relative;
    overflow: hidden;
    background: linear-gradient(90deg, #f2495c 0%, #73bf69 20%, #73bf69 90%, #B877D9 100%);
  }
  .car-bar-spacer {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: transparent;
  }
  .car-bar-cover {
    position: absolute;
    top: 0;
    right: 0;
    height: 100%;
    background: #1e2228;
    border-radius: 0 7px 7px 0;
  }
  .car-soc {
    font-size: 16px;
    font-weight: 700;
    min-width: 48px;
    text-align: right;
  }
  .car-row2 {
    display: flex;
    align-items: baseline;
    gap: 12px;
    font-size: 12px;
    padding-left: 2px;
  }
  .car-range {
    color: #d8d9da;
    font-weight: 500;
  }
  .car-maxrange {
    color: #8e8e8e;
  }
  .car-timeleft {
    color: #FF9830;
    font-weight: 500;
  }
  @keyframes car-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .car-charging .car-bar-container {
    animation: car-pulse 2s ease-in-out infinite;
  }
`;

function socColor(soc) {
  if (soc > 90) return '#B877D9';
  if (soc > 20) return '#73bf69';
  return '#f2495c';
}

const CarCard = ({ name, soc, range, maxRange, charging, timeLeft }) => {
  const coverWidth = 100 - soc;
  return (
    <div className={`car-card${charging ? ' car-charging' : ''}`}>
      <div className="car-row1">
        <div className="car-name">{name}</div>
        <div className="car-bar-container">
          <div className="car-bar-spacer" style={{ width: `${soc}%` }} />
          <div className="car-bar-cover" style={{ width: `${coverWidth}%` }} />
        </div>
        <div className="car-soc" style={{ color: socColor(soc) }}>
          {soc}%
        </div>
      </div>
      <div className="car-row2">
        <span className="car-range">{range} km</span>
        <span className="car-maxrange">max {maxRange} km</span>
        {charging && timeLeft != null && (
          <span className="car-timeleft">{timeLeft} min left</span>
        )}
      </div>
    </div>
  );
};

const CarsPanel = () => {
  const cars = [
    {
      name: 'Enyaq',
      soc: 78,
      range: 285,
      maxRange: 365,
      charging: false,
      timeLeft: null,
    },
    {
      name: 'ID.3',
      soc: 45,
      range: 142,
      maxRange: 315,
      charging: true,
      timeLeft: 47,
    },
  ];

  return (
    <>
      <style>{styles}</style>
      <div className="car-panel">
        {cars.map((car) => (
          <CarCard key={car.name} {...car} />
        ))}
      </div>
    </>
  );
};

export default CarsPanel;
