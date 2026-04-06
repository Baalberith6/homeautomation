# InfluxDB Field Reference — Prdikov Dashboard

## Weather (measurement: "weather")
| Field | Description |
|-------|-------------|
| temperature | Outdoor temp (°C) |
| humidity | Outdoor humidity (%) — guessed field name, verify |
| precipRate | Rain rate (mm/h) |
| precipTotal | Rain total (mm) |
| windSpeed | Wind sustained (km/h) |
| windGust | Wind gust (km/h) |
| temperature_upstairs_in | Obyvacka temp (°C) |
| humidity_upstairs_in | Obyvacka humidity (%) |
| moes_co2 | CO2 sensor (ppm) |

## Weather Forecast (measurement: "weatherforecast")
| Field | Description |
|-------|-------------|
| maxtemp | YR.no forecast high (°C) |
| mintemp | YR.no forecast low (°C) |
| precip | Rain forecast (mm) |

## Wind Forecast (measurement: "windforecast", via telegraf; also "WindForecast" direct InfluxDB)
| Field | Description |
|-------|-------------|
| 00–23 | Hourly wind speed forecast (km/h) — telegraf pivoted from MQTT topic hour |
| wind_speed | Sustained wind speed (km/h) — direct InfluxDB write |
| wind_gust | Wind gust speed (km/h) — direct InfluxDB write |

## Gust Forecast (measurement: "gustforecast", via telegraf)
| Field | Description |
|-------|-------------|
| 00–23 | Hourly wind gust forecast (km/h) — telegraf pivoted from MQTT topic hour |

## Indoor - Rehau (measurement: "rehau")
| Field | Description |
|-------|-------------|
| Pracovna | Pracovna temp (°C) |

## Indoor - Rehau Humidity (measurement: "rehau_hum")
| Field | Description |
|-------|-------------|
| Pracovna | Pracovna humidity (%) |

## Indoor - Rehau Setpoints (measurement: "rehau_set")
| Field | Description |
|-------|-------------|
| Obyvacka | Obyvacka target temp (°C) |
| Pracovna | Pracovna target temp (°C) |

## Indoor - Netatmo (measurement: "netatmo")
| Field | Description |
|-------|-------------|
| hala | Poschodie temp (°C) |
| spalna | Spalna temp (°C) |

## Indoor - Netatmo Setpoints (measurement: "temp_target")
| Field | Description |
|-------|-------------|
| hala | Poschodie target temp (°C) |
| kupelna | Kupelna target temp (°C) |
| chodba | Chodba target temp (°C) |
| hostovska | Hostovska target temp (°C) |
| julinka | Julinka target temp (°C) |
| kubo | Kubo target temp (°C) |
| spalna | Spalna target temp (°C) |

## Fireplace (measurement: "krb")
| Field | Description |
|-------|-------------|
| apower | Krb power (W) — ON if > 20W |
| tC | Krb temperature (°C) |

## Heat Pump (measurement: "Estia")
| Field | Description |
|-------|-------------|
| cop_24h | 24h COP — query with range -24h |

## Cars (measurement: "Car")
| Field | Description |
|-------|-------------|
| battery_level_enyaq | Enyaq SoC (%) |
| electric_range_enyaq | Enyaq range (km) |
| battery_level_vw | ID.3 SoC (%) |
| electric_range_vw | ID.3 range (km) |
| charging_wallbox_power | Wallbox charge power (W) |
| charging_time_left_enyaq | Enyaq charge time remaining (min) |
| charging_time_left_vw | ID.3 charge time remaining (min) |
| car_connected | Car plugged in to wallbox (1 = yes, 0 = no) |

## Solar/FVE (measurement: "FVE")
| Field | Tag | Description |
|-------|-----|-------------|
| consumption | | Current consumption (W) |
| power | string="all" | Current production (W) |
| soc | | Battery SoC (%) |
| battery_load | | Battery load (W) |
| meter_power | | Grid meter power (W) — negative = import, positive = export |
| consumption_day | | Daily consumption (kWh) |
| generation_day | | Daily generation (kWh) |

### Monthly calculation
Monthly stats use `consumption_day` and `generation_day` with:
```
range(start: date.truncate(t: v.timeRangeStop, unit: 1mo), stop: v.timeRangeStop)
|> aggregateWindow(every: 1d, fn: max)
|> sum()
```

## Constants
- Max PV power: 9000W (used for bar gauge scaling: value / 9000 * 100)
- Krb ON threshold: > 20W
