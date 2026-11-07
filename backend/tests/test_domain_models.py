"""Tests for domain models (Site, Sector, Cell, NrBand, AntennaConfig)."""

import pytest
from pydantic import ValidationError

from ran_city.domain.models import (
    AntennaConfig,
    Cell,
    CellType,
    DataSourceOrigin,
    NrBand,
    Sector,
    Site,
)
from ran_city.domain.units import Point3D


class TestDomainModels:
    """Tests for Pydantic domain models and physical constraints."""

    def test_nr_band_presets_and_validation(self):
        n28 = NrBand.n28()
        assert n28.n_band == 28
        assert n28.freq_ghz == 0.728
        assert n28.scs_khz == 15
        assert n28.num_rbs == 106

        n78 = NrBand.n78()
        assert n78.n_band == 78
        assert n78.freq_ghz == 3.5
        assert n78.scs_khz == 30
        assert n78.num_rbs == 273

        n258 = NrBand.n258()
        assert n258.n_band == 258
        assert n258.freq_ghz == 26.0
        assert n258.scs_khz == 120
        assert n258.num_rbs == 66

        # Freq bounds: 0.5 <= f <= 100.0 GHz
        with pytest.raises(ValidationError):
            NrBand(name="bad", n_band=1, freq_ghz=0.3, scs_khz=15, bandwidth_mhz=20.0, num_rbs=100)
        with pytest.raises(ValidationError):
            NrBand(
                name="bad", n_band=1, freq_ghz=105.0, scs_khz=15, bandwidth_mhz=20.0, num_rbs=100
            )

        # SCS validation: 15, 30, 60, 120
        with pytest.raises(ValidationError):
            NrBand(name="bad", n_band=1, freq_ghz=3.5, scs_khz=45, bandwidth_mhz=20.0, num_rbs=100)

    def test_antenna_config_validation(self):
        ant = AntennaConfig(n_rows=8, n_cols=8, mechanical_tilt_deg=5.0, electrical_tilt_deg=3.0)
        assert ant.n_rows == 8
        assert ant.n_cols == 8
        assert ant.mechanical_tilt_deg == 5.0
        assert ant.electrical_tilt_deg == 3.0

        with pytest.raises(ValidationError):
            AntennaConfig(n_rows=0)
        with pytest.raises(ValidationError):
            AntennaConfig(mechanical_tilt_deg=95.0)
        with pytest.raises(ValidationError):
            AntennaConfig(electrical_tilt_deg=-95.0)

    def test_cell_sector_site_hierarchy(self):
        band = NrBand.n78()
        ant = AntennaConfig()
        cell = Cell(
            cell_id="CELL_01",
            cell_type=CellType.MACRO,
            band=band,
            antenna=ant,
            tx_power_dbm=43.0,
            cable_loss_db=0.5,
            source=DataSourceOrigin.REAL,
        )
        assert cell.active is True

        # Invalid tx power
        with pytest.raises(ValidationError):
            Cell(
                cell_id="CELL_BAD",
                cell_type=CellType.MACRO,
                band=band,
                antenna=ant,
                tx_power_dbm=80.0,
                source=DataSourceOrigin.SYNTHETIC,
            )

        # Sector
        sector = Sector(
            sector_id="SEC_01",
            azimuth_deg=450.0,  # should normalize to 90.0
            ant_height_m=25.0,
            cells=(cell,),
        )
        assert sector.azimuth_deg == 90.0

        # Sector empty cells validation
        with pytest.raises(ValidationError):
            Sector(
                sector_id="SEC_EMPTY",
                azimuth_deg=0.0,
                ant_height_m=25.0,
                cells=(),
            )

        # Site
        site = Site(
            site_id="SITE_01",
            network_alias="Red A",
            x_m=435000.0,
            y_m=4180000.0,
            ground_z_m=400.0,
            sectors=(sector,),
            source=DataSourceOrigin.ESTIMATED,
        )
        tx_pos = site.tx_position(sector)
        assert isinstance(tx_pos, Point3D)
        assert tx_pos.x_m == 435000.0
        assert tx_pos.y_m == 4180000.0
        assert tx_pos.z_m == 425.0  # 400.0 + 25.0

    def test_immutability(self):
        band = NrBand.n78()
        with pytest.raises(ValidationError):
            band.freq_ghz = 4.0
