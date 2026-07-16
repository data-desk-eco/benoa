CREATE OR REPLACE TABLE benoa_lng_trades AS
SELECT
    trade_id,
    date::DATE        AS date,
    year::INTEGER     AS year,
    origin,
    origin_country,
    volume_m3::DOUBLE AS volume_m3,
    mass_t::DOUBLE    AS mass_t,
    vessel,
    status
FROM read_csv('data/benoa_lng_trades.csv', header = true);

CREATE OR REPLACE TABLE benoa_lng_by_origin AS
SELECT
    year,
    origin,
    COUNT(*)              AS cargoes,
    ROUND(SUM(volume_m3)) AS volume_m3,
    ROUND(SUM(mass_t))    AS mass_t
FROM benoa_lng_trades
GROUP BY year, origin
ORDER BY year, origin;
