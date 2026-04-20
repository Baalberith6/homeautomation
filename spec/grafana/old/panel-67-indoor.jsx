import React from 'react';

// Temperature color coding
const getTempColor = (temp) => {
  if (temp > 26) return '#f2495c';
  if (temp > 25) return '#dd5d5e';
  if (temp > 24) return '#b38463';
  if (temp > 23) return '#88ab67';
  if (temp > 20) return '#73bf69';
  if (temp > 16) return '#80b368';
  if (temp > 12) return '#999c65';
  if (temp > 8) return '#b38463';
  if (temp > 4) return '#cc6c60';
  return '#f2495c';
};

// CO2 color coding
const getCo2Color = (ppm) => {
  if (ppm < 800) return '#73bf69';
  if (ppm <= 1000) return '#ff9830';
  return '#f2495c';
};

// Mock data
const rooms = [
  { name: 'Obyvacka', temp: 22.1, target: 22.0, humidity: 48, heating: true },
  { name: 'Pracovna', temp: 21.5, target: 21.0, humidity: 52, heating: true },
  { name: 'Julinka', temp: 20.8, target: 20.0, humidity: null, heating: true },
  { name: 'Kubo', temp: 21.2, target: 21.0, humidity: null, heating: true },
  { name: 'Spalna', temp: 19.5, target: 19.0, humidity: null, heating: false },
];

const heatingStatus = {
  krbOn: true,       // power > 20W
  krbTemp: 65.2,
  cop24h: 3.45,
  co2: 742,
};

const styles = `
  .indoor-container {
    display: flex;
    flex-direction: row;
    width: 100%;
    height: 100%;
    gap: 0;
    font-family: 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    color: #d8d9da;
  }

  .indoor-col-left {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 4px;
  }

  .indoor-divider {
    width: 1px;
    background: #2c3035;
    align-self: stretch;
  }

  .indoor-col-right {
    flex: 0 0 auto;
    width: 38%;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 4px;
  }

  .indoor-card {
    background: #1e2228;
    border-radius: 4px;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex: 1;
    min-height: 0;
  }

  .indoor-room-info {
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .indoor-room-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .indoor-name {
    font-size: 0.8vw;
    color: #999;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .indoor-temp {
    font-size: 1.8vw;
    font-weight: 600;
    line-height: 1;
  }

  .indoor-target {
    font-size: 1.1vw;
    color: #888;
  }

  .indoor-humidity {
    font-size: 1.4vw;
    color: #6e9fff;
  }

  .indoor-heat-arrow {
    font-size: 1.4vw;
    color: #ff9830;
    line-height: 1;
  }

  .indoor-heat-card {
    background: #1e2228;
    border-radius: 4px;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex: 1;
    min-height: 0;
  }

  .indoor-heat-label {
    font-size: 0.8vw;
    color: #999;
  }

  .indoor-heat-val {
    font-size: 1.5vw;
    font-weight: 600;
    line-height: 1;
  }

  .indoor-heat-row-lg {
    flex: 1.6;
  }

  .indoor-heat-val-lg {
    font-size: 2.6vw;
    font-weight: 600;
    line-height: 1;
  }
`;

const RoomRow = ({ name, temp, target, humidity, heating }) => {
  const tempColor = getTempColor(temp);
  return (
    <div className="indoor-card">
      <div className="indoor-room-info">
        <span className="indoor-name">{name}</span>
        <span className="indoor-temp" style={{ color: tempColor }}>
          {temp.toFixed(1)}&deg;
        </span>
        <span className="indoor-target">
          &#9656;{target.toFixed(1)}&deg;
        </span>
      </div>
      <div className="indoor-room-right">
        {humidity != null && (
          <span className="indoor-humidity">{humidity}%</span>
        )}
        {heating && (
          <span className="indoor-heat-arrow">&#9650;</span>
        )}
      </div>
    </div>
  );
};

const IndoorPanel = () => {
  const krbColor = heatingStatus.krbOn ? '#73bf69' : '#f2495c';
  const krbText = heatingStatus.krbOn ? 'ON' : 'OFF';

  // Krb temp color: gradient from blue (cold) through green to red (hot)
  const krbTempColor = getTempColor(heatingStatus.krbTemp > 50 ? 27 : heatingStatus.krbTemp);
  // For fireplace temps (typically 40-80), use warm colors
  const krbTempDisplayColor =
    heatingStatus.krbTemp > 60 ? '#f2495c' :
    heatingStatus.krbTemp > 50 ? '#dd5d5e' :
    heatingStatus.krbTemp > 40 ? '#b38463' :
    '#73bf69';

  const copColor = '#73bf69';
  const co2Color = getCo2Color(heatingStatus.co2);

  return (
    <>
      <style>{styles}</style>
      <div className="indoor-container">
        {/* Left column - Rooms */}
        <div className="indoor-col-left">
          {rooms.map((room) => (
            <RoomRow key={room.name} {...room} />
          ))}
        </div>

        {/* Vertical divider */}
        <div className="indoor-divider" />

        {/* Right column - Heating status */}
        <div className="indoor-col-right">
          <div className="indoor-heat-card">
            <span className="indoor-heat-label">Krb</span>
            <span className="indoor-heat-val" style={{ color: krbColor }}>
              {krbText}
            </span>
          </div>

          <div className="indoor-heat-card">
            <span className="indoor-heat-label">Krb T</span>
            <span className="indoor-heat-val" style={{ color: krbTempDisplayColor }}>
              {heatingStatus.krbTemp.toFixed(1)}&deg;
            </span>
          </div>

          <div className="indoor-heat-card">
            <span className="indoor-heat-label">COP 24h</span>
            <span className="indoor-heat-val" style={{ color: copColor }}>
              {heatingStatus.cop24h.toFixed(2)}
            </span>
          </div>

          <div className="indoor-heat-card indoor-heat-row-lg">
            <span className="indoor-heat-label">CO2</span>
            <span className="indoor-heat-val-lg" style={{ color: co2Color }}>
              {heatingStatus.co2} <small style={{ fontSize: '0.5em', color: '#888' }}>ppm</small>
            </span>
          </div>
        </div>
      </div>
    </>
  );
};

export default IndoorPanel;
