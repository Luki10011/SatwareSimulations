import datetime
import pytest

from utils.rotations import datetime_to_julian_date, get_initial_gmst


@pytest.mark.parametrize(
    "dt, expected_jd, expected_gmst",
    [
        (
            datetime.datetime(2000, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            2451545.0,
            280.46061837,
        ),
        (
            datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            2451544.5,
            99.967794686855,
        ),
        (
            datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            2460310.5,
            100.15260758483782,  # Poprawiona wartość
        ),
    ],
)

def test_julian_date_and_gmst_known_values(dt, expected_jd, expected_gmst):
    jd = datetime_to_julian_date(dt)
    gmst = get_initial_gmst(jd)

    assert jd == pytest.approx(expected_jd, abs=1e-6)
    assert gmst == pytest.approx(expected_gmst, abs=1e-6)


def test_timezone_conversion():
    cet = datetime.timezone(datetime.timedelta(hours=1))
    dt_cet = datetime.datetime(2000, 1, 1, 13, 0, 0, tzinfo=cet)

    jd = datetime_to_julian_date(dt_cet)
    gmst = get_initial_gmst(jd)

    assert jd == pytest.approx(2451545.0, abs=1e-6)
    assert gmst == pytest.approx(280.46061837, abs=1e-6)


def test_naive_datetime_handling():
    dt_naive = datetime.datetime(2000, 1, 1, 12, 0, 0)

    jd = datetime_to_julian_date(dt_naive)
    assert jd == pytest.approx(2451545.0, abs=1e-6)