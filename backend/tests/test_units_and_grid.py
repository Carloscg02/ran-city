"""Tests for RF units and scenario grid."""

import math
from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ran_city.domain.grid import (
    EnvironmentType,
    GridGeometry,
    ScenarioGrid,
)
from ran_city.domain.units import (
    AzimuthDeg,
    Db,
    Dbm,
    LinearMw,
    Point3D,
    ZenithDeg,
)


class TestUnits:
    """Tests for RF domain units and type safety."""

    def test_linear_mw_creation_and_math(self):
        p1 = LinearMw(100.0)
        p2 = LinearMw(200.0)
        p_sum = p1 + p2
        assert isinstance(p_sum, LinearMw)
        assert math.isclose(p_sum.value, 300.0)

        p_scaled = p1 * 2.5
        assert isinstance(p_scaled, LinearMw)
        assert math.isclose(p_scaled.value, 250.0)

        with pytest.raises(ValueError):
            LinearMw(-1.0)

    def test_dbm_conversions_and_arithmetic(self):
        # 0 dBm == 1 mW, 30 dBm == 1000 mW
        assert math.isclose(Dbm(0.0).to_mw().value, 1.0)
        assert math.isclose(Dbm(30.0).to_mw().value, 1000.0)
        assert math.isclose(LinearMw(1.0).to_dbm().value, 0.0)
        assert math.isclose(LinearMw(1000.0).to_dbm().value, 30.0)

        with pytest.raises(ValueError):
            LinearMw(0.0).to_dbm()

        # Dbm + Db -> Dbm
        p = Dbm(43.0) + Db(-3.0)
        assert isinstance(p, Dbm)
        assert math.isclose(p.value, 40.0)

        # Dbm - Db -> Dbm
        p2 = Dbm(43.0) - Db(3.0)
        assert isinstance(p2, Dbm)
        assert math.isclose(p2.value, 40.0)

        # Dbm - Dbm -> Db
        diff = Dbm(43.0) - Dbm(40.0)
        assert isinstance(diff, Db)
        assert math.isclose(diff.value, 3.0)

        # Dbm + Dbm must raise TypeError explicitly!
        with pytest.raises(TypeError, match="LinearMw"):
            _ = Dbm(40.0) + Dbm(40.0)

    def test_azimuth_deg_normalization(self):
        assert AzimuthDeg(0.0).value == 0.0
        assert AzimuthDeg(360.0).value == 0.0
        assert AzimuthDeg(720.0).value == 0.0
        assert AzimuthDeg(-90.0).value == 270.0
        assert AzimuthDeg(450.0).value == 90.0

    def test_zenith_deg_bounds(self):
        assert ZenithDeg(0.0).value == 0.0
        assert ZenithDeg(90.0).value == 90.0
        assert ZenithDeg(180.0).value == 180.0

        with pytest.raises(ValueError):
            ZenithDeg(-0.1)

        with pytest.raises(ValueError):
            ZenithDeg(180.1)

    def test_point3d_immutability(self):
        pt = Point3D(x_m=100.0, y_m=200.0, z_m=30.0)
        assert pt.x_m == 100.0
        assert pt.y_m == 200.0
        assert pt.z_m == 30.0
        with pytest.raises(FrozenInstanceError):
            pt.x_m = 50.0

    @given(st.floats(min_value=-100.0, max_value=100.0))
    def test_dbm_mw_roundtrip(self, dbm_val):
        dbm = Dbm(dbm_val)
        mw = dbm.to_mw()
        dbm_back = mw.to_dbm()
        assert math.isclose(dbm.value, dbm_back.value, rel_tol=1e-6, abs_tol=1e-6)


class TestScenarioGrid:
    """Tests for ScenarioGrid and GridGeometry generation."""

    def test_environment_type_resolutions(self):
        assert EnvironmentType.DENSE_URBAN.resolution_m == 5.0
        assert EnvironmentType.URBAN.resolution_m == 12.0
        assert EnvironmentType.RURAL.resolution_m == 50.0

    def test_grid_from_bounds_validation(self):
        with pytest.raises(ValueError):
            ScenarioGrid.from_bounds(100.0, 100.0, 50.0, 200.0, EnvironmentType.URBAN)
        with pytest.raises(ValueError):
            ScenarioGrid.from_bounds(100.0, 100.0, 200.0, 50.0, EnvironmentType.URBAN)
        with pytest.raises(ValueError):
            ScenarioGrid.from_bounds(100.0, 100.0, 105.0, 105.0, EnvironmentType.URBAN)
        with pytest.raises(ValueError):
            ScenarioGrid.from_bounds(
                0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN, rx_height_m=-1.0
            )

    def test_grid_cardinal_directions(self):
        # 3x3 grid centered around (0, 0)
        # Bbox [-7.5, -7.5, 7.5, 7.5] with resolution 5.0 -> centers at -5, 0, 5
        grid = ScenarioGrid.from_bounds(
            -7.5, -7.5, 7.5, 7.5, EnvironmentType.DENSE_URBAN, ground_z_m=0.0, rx_height_m=1.5
        )
        assert grid.shape == (3, 3)

        # TX at center (0, 0, 25.0)
        tx = Point3D(0.0, 0.0, 25.0)
        geom = grid.geometry_from_tx(tx)
        assert isinstance(geom, GridGeometry)
        assert geom.d2d_m.shape == (3, 3)
        assert geom.d3d_m.shape == (3, 3)
        assert geom.zenith_gcs_deg.shape == (3, 3)
        assert geom.azimuth_gcs_deg.shape == (3, 3)

        # Indices: [y_idx, x_idx]. y increases with index (from y_min to y_max)
        # ys: [-5, 0, 5], xs: [-5, 0, 5]
        # North: (x=0, y=5) -> [2, 1]
        assert math.isclose(geom.azimuth_gcs_deg[2, 1], 0.0, abs_tol=1e-5)
        # East: (x=5, y=0) -> [1, 2]
        assert math.isclose(geom.azimuth_gcs_deg[1, 2], 90.0, abs_tol=1e-5)
        # South: (x=0, y=-5) -> [0, 1]
        assert math.isclose(geom.azimuth_gcs_deg[0, 1], 180.0, abs_tol=1e-5)
        # West: (x=-5, y=0) -> [1, 0]
        assert math.isclose(geom.azimuth_gcs_deg[1, 0], 270.0, abs_tol=1e-5)

        # Zenith angles: TX is at z=25, RX is at z=1.5, so TX is above RX.
        # Downtilt means zenith > 90 degrees.
        assert np.all(geom.zenith_gcs_deg > 90.0)

        # Center pixel (x=0, y=0): RX directly beneath TX -> zenith = 180 deg (nadir)
        assert math.isclose(geom.zenith_gcs_deg[1, 1], 180.0, abs_tol=1e-5)

    @given(
        tx_x=st.floats(min_value=-500.0, max_value=500.0),
        tx_y=st.floats(min_value=-500.0, max_value=500.0),
        tx_z=st.floats(min_value=1.0, max_value=100.0),
    )
    def test_grid_geometry_invariants_hypothesis(self, tx_x, tx_y, tx_z):
        grid = ScenarioGrid.from_bounds(0.0, 0.0, 100.0, 100.0, EnvironmentType.URBAN)
        tx = Point3D(tx_x, tx_y, tx_z)
        geom = grid.geometry_from_tx(tx, min_d3d_m=1.0)

        # Invariants:
        # 1. d3d_m >= 1.0
        assert np.all(geom.d3d_m >= 1.0)
        # 2. zenith in [0.0, 180.0]
        assert np.all((geom.zenith_gcs_deg >= 0.0) & (geom.zenith_gcs_deg <= 180.0))
        # 3. azimuth in [0.0, 360.0)
        assert np.all((geom.azimuth_gcs_deg >= 0.0) & (geom.azimuth_gcs_deg < 360.0))
