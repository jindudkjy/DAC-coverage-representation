from pathlib import Path

import pandas as pd


DATA = Path(__file__).resolve().parents[1] / "data" / "frozen"


def test_si_figure_s1_matches_published_table() -> None:
    table = pd.read_csv(DATA / "SI_Fig_S1_source_data.csv")
    assert len(table) == 6
    assert table.positive_after_substitution.eq("yes").all()
    assert table.pre_saturated_delta_tau.median() == 0.0253
    assert table.dry_start_delta_tau.median() == 0.0369


def test_si_figure_s2_matches_published_bounds() -> None:
    table = pd.read_csv(DATA / "SI_Fig_S2_source_data.csv")
    assert table.perturbation_magnitude_pct.tolist() == [5, 10]
    assert table.worst_median_delta_tau.tolist() == [-0.0115, -0.0253]
    assert table.median_of_median_delta_tau.tolist() == [0.0236, 0.0253]


def test_si_figure_s4_respects_published_ranges() -> None:
    table = pd.read_csv(DATA / "SI_Fig_S4_source_data.csv")
    assert len(table) == 5
    assert (table.mg_median_C_rel.min(), table.mg_median_C_rel.max()) == (0.588, 0.719)
    assert (table.ira_median_C_rel.min(), table.ira_median_C_rel.max()) == (0.151, 0.237)
    assert (table.mg_reversal_fraction_pct.min(), table.mg_reversal_fraction_pct.max()) == (5.03, 5.35)
    assert (table.ira_reversal_fraction_pct.min(), table.ira_reversal_fraction_pct.max()) == (2.67, 3.11)
