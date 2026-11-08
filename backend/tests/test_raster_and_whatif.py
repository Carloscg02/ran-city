"""Tests for raster WebGL export (Seam 1) and What-If immutable experiments (Seam 2)."""

from __future__ import annotations

import io

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from PIL import Image

from ran_city.domain.grid import EnvironmentType, ScenarioGrid
from ran_city.domain.models import (
    AntennaConfig,
    Cell,
    CellType,
    DataSourceOrigin,
    NrBand,
    Sector,
    Site,
)
from ran_city.geo.raster import compute_grid_wgs84_bounds, encode_matrix_png_rgba
from ran_city.radio.whatif import CellOverride, SectorOverride, apply_whatif_overrides


class TestRasterExportSeam1:
    """Test suite for raster generation and geographic bounds transformation."""

    def test_compute_grid_wgs84_bounds(self):
        # Jaen urban center approx in EPSG:25830
        grid = ScenarioGrid.from_bounds(
            x_min=429000.0,
            y_min=4180000.0,
            x_max=431000.0,
            y_max=4182000.0,
            environment=EnvironmentType.RURAL,
        )
        bounds = compute_grid_wgs84_bounds(grid)
        west, south, east, north = bounds

        assert west < east
        assert south < north
        # Jaen is around lon -3.8..-3.7, lat 37.7..37.8
        assert -3.85 < west < -3.75
        assert -3.85 < east < -3.75
        assert 37.70 < south < 37.85
        assert 37.70 < north < 37.85

    def test_encode_matrix_png_rgba_basic_and_dimensions(self):
        # Shape: (n_y, n_x) = (20, 30)
        n_y, n_x = 20, 30
        matrix = np.full((n_y, n_x), -90.0)

        png_bytes = encode_matrix_png_rgba(matrix, vmin=-125.0, vmax=-65.0, alpha=200)

        # Valid PNG signature
        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

        img = Image.open(io.BytesIO(png_bytes))
        assert img.mode == "RGBA"
        # PIL Image size is (width, height) = (n_x, n_y)
        assert img.size == (n_x, n_y)

    def test_encode_matrix_north_south_orientation(self):
        # Matrix where only northern row (n_y - 1) has high signal (-70 dBm),
        # whereas all other rows are low (-120 dBm).
        n_y, n_x = 10, 10
        matrix = np.full((n_y, n_x), -120.0)
        matrix[n_y - 1, :] = -70.0

        png_bytes = encode_matrix_png_rgba(matrix, vmin=-125.0, vmax=-65.0, alpha=200)
        img = Image.open(io.BytesIO(png_bytes))
        rgba = np.asarray(img)

        # In decoded PNG (row=0 is the top edge, corresponding to North in deck.gl BitmapLayer):
        # row 0 must have different RGB color from other rows (e.g. row 1..n_y-1)
        top_row_color = rgba[0, 0, :3]
        bottom_row_color = rgba[n_y - 1, 0, :3]
        assert not np.array_equal(top_row_color, bottom_row_color)

        # Rows 1 to n_y-1 should match bottom row color
        for r in range(1, n_y):
            assert np.array_equal(rgba[r, 0, :3], bottom_row_color)

    def test_encode_matrix_nan_and_threshold_transparency(self):
        matrix = np.array([
            [-100.0, np.nan],
            [-130.0, -80.0],
        ])
        # min_threshold = -120.0
        # -100.0: valid (alpha=200)
        # NaN: transparent (alpha=0)
        # -130.0: < min_threshold (alpha=0)
        # -80.0: valid (alpha=200)
        png_bytes = encode_matrix_png_rgba(
            matrix,
            vmin=-125.0,
            vmax=-65.0,
            alpha=200,
            min_threshold=-120.0,
        )
        img = Image.open(io.BytesIO(png_bytes))
        rgba = np.asarray(img)

        # Note: flipud was applied:
        # matrix row 0 was [-100.0, nan], row 1 was [-130.0, -80.0]
        # After flipud:
        # row 0 is [-130.0, -80.0]
        # row 1 is [-100.0, nan]
        # Check alpha channel:
        assert rgba[0, 0, 3] == 0    # -130.0 < min_threshold
        assert rgba[0, 1, 3] == 200  # -80.0 valid
        assert rgba[1, 0, 3] == 200  # -100.0 valid
        assert rgba[1, 1, 3] == 0    # NaN transparent

    def test_encode_matrix_categorical_palette(self):
        # Best server index matrix with indices 0, 1, 2
        matrix = np.array([
            [0.0, 1.0],
            [2.0, 0.0],
        ])
        png_bytes = encode_matrix_png_rgba(matrix, categorical=True, alpha=200)
        img = Image.open(io.BytesIO(png_bytes))
        rgba = np.asarray(img)

        # After flipud:
        # row 0 is [2.0, 0.0]
        # row 1 is [0.0, 1.0]
        c0 = rgba[1, 0, :3]  # idx 0
        c1 = rgba[1, 1, :3]  # idx 1
        c2 = rgba[0, 0, :3]  # idx 2

        # Colors for 0, 1, 2 must be distinct
        assert not np.array_equal(c0, c1)
        assert not np.array_equal(c1, c2)
        assert not np.array_equal(c0, c2)
        # All valid indices have alpha 200
        assert np.all(rgba[..., 3] == 200)


def _make_sample_site() -> Site:
    cell = Cell(
        cell_id="CELL_01",
        cell_type=CellType.MACRO,
        band=NrBand.n78(),
        antenna=AntennaConfig(mechanical_tilt_deg=2.0, electrical_tilt_deg=4.0, electrical_scan_deg=0.0),
        tx_power_dbm=43.0,
        active=True,
        source=DataSourceOrigin.ESTIMATED,
    )
    sector = Sector(
        sector_id="SEC_01",
        azimuth_deg=60.0,
        ant_height_m=30.0,
        cells=(cell,),
    )
    return Site(
        site_id="SITE_01",
        network_alias="Red A",
        x_m=429000.0,
        y_m=4180000.0,
        ground_z_m=500.0,
        sectors=(sector,),
        source=DataSourceOrigin.ESTIMATED,
    )


class TestWhatIfSeam2:
    """Test suite for immutable What-If overrides engine."""

    def test_apply_cell_and_sector_overrides_immutability(self):
        original_site = _make_sample_site()
        sites = (original_site,)

        cell_ovr = CellOverride(
            cell_id="CELL_01",
            mechanical_tilt_deg=10.0,
            electrical_tilt_deg=8.0,
            electrical_scan_deg=-5.0,
            tx_power_dbm=46.0,
            active=False,
        )
        sector_ovr = SectorOverride(
            sector_id="SEC_01",
            azimuth_deg=180.0,
            ant_height_m=45.0,
        )

        new_sites = apply_whatif_overrides(
            sites,
            cell_overrides=(cell_ovr,),
            sector_overrides=(sector_ovr,),
        )

        assert len(new_sites) == 1
        new_site = new_sites[0]

        # Verify original site is 100% untouched
        orig_sec = original_site.sectors[0]
        orig_cell = orig_sec.cells[0]
        assert orig_sec.azimuth_deg == 60.0
        assert orig_sec.ant_height_m == 30.0
        assert orig_cell.antenna.mechanical_tilt_deg == 2.0
        assert orig_cell.antenna.electrical_tilt_deg == 4.0
        assert orig_cell.antenna.electrical_scan_deg == 0.0
        assert orig_cell.tx_power_dbm == 43.0
        assert orig_cell.active is True

        # Verify updated values in the new site
        new_sec = new_site.sectors[0]
        new_cell = new_sec.cells[0]
        assert new_sec.azimuth_deg == 180.0
        assert new_sec.ant_height_m == 45.0
        assert new_cell.antenna.mechanical_tilt_deg == 10.0
        assert new_cell.antenna.electrical_tilt_deg == 8.0
        assert new_cell.antenna.electrical_scan_deg == -5.0
        assert new_cell.tx_power_dbm == 46.0
        assert new_cell.active is False

    def test_unknown_cell_or_sector_id_raises_value_error(self):
        site = _make_sample_site()
        sites = (site,)

        with pytest.raises(ValueError, match="CELL_UNKNOWN"):
            apply_whatif_overrides(
                sites,
                cell_overrides=(CellOverride(cell_id="CELL_UNKNOWN", tx_power_dbm=40.0),),
            )

        with pytest.raises(ValueError, match="SEC_UNKNOWN"):
            apply_whatif_overrides(
                sites,
                sector_overrides=(SectorOverride(sector_id="SEC_UNKNOWN", azimuth_deg=90.0),),
            )

    @given(
        mechanical_tilt=st.floats(min_value=-20.0, max_value=45.0),
        electrical_tilt=st.floats(min_value=-20.0, max_value=45.0),
        tx_power=st.floats(min_value=10.0, max_value=50.0),
    )
    def test_cell_override_hypothesis_invariants(self, mechanical_tilt, electrical_tilt, tx_power):
        original_site = _make_sample_site()
        sites = (original_site,)

        cell_ovr = CellOverride(
            cell_id="CELL_01",
            mechanical_tilt_deg=mechanical_tilt,
            electrical_tilt_deg=electrical_tilt,
            tx_power_dbm=tx_power,
        )

        new_sites = apply_whatif_overrides(sites, cell_overrides=(cell_ovr,))
        new_cell = new_sites[0].sectors[0].cells[0]

        # Invariant 1: original site is untouched
        assert original_site.sectors[0].cells[0].tx_power_dbm == 43.0
        assert original_site.sectors[0].cells[0].antenna.mechanical_tilt_deg == 2.0
        assert original_site.sectors[0].cells[0].antenna.electrical_tilt_deg == 4.0

        # Invariant 2: new cell has exact overridden values
        assert new_cell.tx_power_dbm == pytest.approx(tx_power)
        assert new_cell.antenna.mechanical_tilt_deg == pytest.approx(mechanical_tilt)
        assert new_cell.antenna.electrical_tilt_deg == pytest.approx(electrical_tilt)

