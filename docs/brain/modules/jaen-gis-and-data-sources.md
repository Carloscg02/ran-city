# Módulo Funcional: Adaptadores GIS e Ingesta de Red Estimada de Jaén (`jaen-gis-and-data-sources`)

> Adaptadores geoespaciales (`EPSG:4326 <-> EPSG:25830`, muestreo de relieve `MDT05`) y pipeline reproducible de fusión OpenCelliD (`MCC=214`) + mástiles OpenStreetMap hacia `data/cities/jaen.yaml`.

## 1. Adaptador Geoespacial (`backend/ran_city/geo/`)
- **`crs.py`**: `wgs84_to_utm30(lon, lat)` y `utm30_to_wgs84(x_m, y_m)` mediante `pyproj` (`EPSG:4326 <-> EPSG:25830`, biyectivas para escalares y arrays `NumPy`).
- **`terrain.py`**: `sample_points_elevation(raster_path, xs_m, ys_m)` y `sample_grid_terrain(raster_path, grid)` sobre GeoTIFF/COG `MDT05` con relleno seguro de `nodata` para evitar `NaN`s en `ScenarioGrid.terrain_z_m`.

## 2. Esquema Declarativo e Ingesta de Jaén (`backend/ran_city/data_sources/` y `data/cities/jaen.yaml`)
- **`city_schema.py`**: `CityZoneSpec`, `OperatorSpectrumSpec`, `CityConfig`, `CityScenario`, `load_city_scenario` y `save_city_scenario` (`PyYAML`).
- **`opencellid_osm.py`**: `RawCellRecord`, `OsmMastRecord`, `map_mnc_to_network_alias` (`7 -> Red A`, `1 -> Red B`, `3 -> Red C`), `cluster_opencellid_and_snap_osm` (radio de agrupación `120 m`, *snap* a mástil OSM `<= 75 m`, sectores `0°/120°/240°`, portadoras CNAF `n28`/`n78`) y modelo hipsométrico de Jaén (`426 m` en Bulevar/Los Olivares hasta `795 m` en el Cerro de Santa Catalina).
- **`ingest_jaen.py` y `data/cities/jaen.yaml`**: Pipeline que descarga celdas de OpenCelliD (`MCC=214`) usando `OPENCELLID_API_KEY` por entorno y mástiles de Overpass OSM, persistiendo en `data/cities/jaen.yaml` 18 emplazamientos trisectoriales (`6` por operador `Red A/B/C`, `source: estimated`) listos para simulación offline.

## 3. Suite de Verificación
- `backend/tests/test_geo_crs_and_terrain.py`
- `backend/tests/test_data_sources_jaen.py`
