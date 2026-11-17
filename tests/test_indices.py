import pytest
import numpy as np
import pandas as pd

from agroclima import indices as ix


def synthetic(lat, years=(2000, 2003), tmean=20.0):
    idx = pd.date_range(f"{years[0]-1}-07-01", f"{years[1]}-12-31", freq="D")
    df = pd.DataFrame({"T2M": tmean, "T2M_MAX": tmean + 6, "T2M_MIN": tmean - 6, "PRECTOTCORR": 1.0,
                       "RH2M": 60.0, "WS2M": 2.0, "ALLSKY_SFC_SW_DWN": 20.0, "T2MDEW": 10.0}, index=idx)
    return df


def test_winkler_constant_temperature_north():
    s = ix.Settings()
    d = ix.enrich_daily(synthetic(42.0), 42.0, 500, s)
    a = ix.campaign_indices(d, 42.0, s).set_index("Campaña")
    assert a.loc[2001, "GDD Winkler (°C·día)"] == 214 * 10  # 1 abr–31 oct
    assert a.loc[2001, "GST (°C)"] == 20
    assert a.loc[2001, "Índice de Huglin"] == pytest.approx(183 * 13 * 1.02)


def test_south_season_crosses_year():
    s = ix.Settings()
    d = ix.enrich_daily(synthetic(-33.0), -33.0, 900, s)
    a = ix.campaign_indices(d, -33.0, s).set_index("Campaña")
    # 1 oct 2000 – 30 abr 2001 = 212 días
    assert a.loc[2001, "GDD Winkler (°C·día)"] == 212 * 10


def test_incomplete_season_is_nan():
    s = ix.Settings()
    raw = synthetic(42.0)
    raw.loc["2001-05-01":"2001-06-30", "T2M"] = np.nan
    d = ix.enrich_daily(raw, 42.0, 500, s)
    a = ix.campaign_indices(d, 42.0, s).set_index("Campaña")
    assert np.isnan(a.loc[2001, "GDD Winkler (°C·día)"])


def test_et0_reasonable():
    s = ix.Settings()
    d = ix.enrich_daily(synthetic(42.0), 42.0, 500, s)
    assert d.loc["2001-07-15", "ET0"] > 3 and d.loc["2001-07-15", "ET0"] < 8


def test_classify():
    from agroclima.config import WINKLER_CLASSES
    assert ix.classify(1500, WINKLER_CLASSES) == "Región II"
    assert ix.classify(np.nan, WINKLER_CLASSES) == "Sin datos"
