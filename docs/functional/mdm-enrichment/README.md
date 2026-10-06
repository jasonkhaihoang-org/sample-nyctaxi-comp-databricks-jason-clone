# MDM enrichment — master-data landing

Master-data landing into `mdm_raw`, executed by
`src/dlt/mdm.Notebook/notebook-content.py` (fixed `_loaded_at`
`2024-07-02 02:40:00`; stamps `_load_id`, `_source_file`, `_loaded_at` on every
write). Nine tables, one per master. All pseudo-random enrichment is `hb()` of a
key — deterministic, no RNG. The zone master reads the landed
`bronze_taxi_zone_lookup` via `spark.table`.

## Per-master real-vs-invented contract

| Table | Real columns | Invented columns |
| --- | --- | --- |
| `mdm_raw_zone_master` | `location_id`, borough, zone label, `tlc_service_zone`, airport/zone class | `centroid_lat/lon`, `area_sq_mi`, `resident_population`, `is_congestion_zone`, `demand_tier`, and the entire versioning |
| `mdm_raw_vendor_master` | Vendor ids and names, incl. the VeriFone-to-Curb rebrand | `contract_tier`, `is_approved`, version dates |
| `mdm_raw_payment_method_master` | Codes, labels, `tip_is_captured` (cash tips unmeasured, not zero) | `settlement_class`, `settlement_days`, `processor_fee_pct`, `counts_as_revenue` |
| `mdm_raw_rate_plan_master` | Codes, names, flat-fare amount, airport applicability | `pricing_model`, `is_metered_baseline` |
| `mdm_raw_fare_regime_master` | Surcharge rates (improvement, MTA tax, congestion, airport fee) | Effective dates are approximate |
| `mdm_raw_borough_master` | Names, codes, approximately census-accurate population/area | `reporting_region`, `is_core_market` |
| `mdm_raw_zone_poi` | The three airport points of interest | The other 269 assignments |
| `mdm_raw_calendar_master` | 2024 US federal holidays, 8 April eclipse, St Patrick's Day parade | School-term / season flags |
| `mdm_raw_weather_daily` | Nothing — seasonal sine curve plus hash noise, not NOAA data | Everything |

The coordinates look real and are not: hash output in a plausible NYC range
(JFK reads `40.6034` against a true ~`40.641`; airport resident populations are
nonsense). Any distance, density, or mapping math on them is garbage that passes
a smell test. `tlc_service_zone` is the load-bearing exception — genuine
reference data whose `'Airports'` value silently excludes Newark.

## Versioning rule

Zones with `location_id % 37 == 0` carry two versions: an expired first version
(demand tier stepped down one level) plus the replacing second version. All
other zones carry a single version (`source_version = 1`). The vendor master
versions the VeriFone-to-Curb changeover (date approximate).

## SCD2-in-dbt boundary

Raw versions land side by side; no SCD2 assembly happens here. dbt owns
conforming and history: `core.dim_zone` / `core.dim_vendor` build half-open
`[valid_from_date, valid_to_date)` intervals, as-of joins use `>=` and `<`
(never `BETWEEN`), and `is_current_version` marks `valid_to_date = 2099-12-31`.
The SCD2 mechanics are real; the version history they operate on is
manufactured (seven second-version zones exist because the generator dealt
them, not because TLC re-designated anything).

## Provenance

Tier 2 for the transcribed rates, holidays, rebrand, and code mappings (rates
real, dates approximate — verify against TLC before citing). Tier 3 for the
zone/vendor/payment/rate/borough masters (real keys and classifications, fake
enrichment). Tier 4 (fully synthetic) for `weather_daily`.
