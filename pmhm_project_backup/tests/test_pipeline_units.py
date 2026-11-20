"""Unit tests for stage parsing, block segmentation, chunk-carry logic and Arrow conversion."""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmhm.data import schema as S  # noqa: E402
from pmhm.data.convert import _running_cumcount, arr, make_table  # noqa: E402
from pmhm.data.stages import BlockTracker, canonical_subject, harmonise_spectrometer_stage, parse_stage  # noqa: E402

STAGES = (["before_clamping"] * 3 + ["during_clamping_20mmHg"] * 2 + ["during_clamping_0mmHg"] * 2
          + ["during_clamping_40mmHg"] * 2 + ["during_clamping_0mmHg"] * 1)


def test_parse_stage():
    assert parse_stage("before_clamping") == (0, "baseline")
    assert parse_stage("during_clamping_0mmHg") == (0, "rest")
    assert parse_stage("during_clamping_160mmHg") == (160, "clamping")
    with pytest.raises(ValueError):
        parse_stage("clamp_160")


def test_subject_and_spectrometer_labels():
    assert canonical_subject("subject 1") == "subject_01"
    assert canonical_subject("subject 10") == "subject_10"
    m = {"baseline (0 mmHg)": "before_clamping", "160 mmHg": "during_clamping_160mmHg"}
    assert harmonise_spectrometer_stage("baseline (0 mmHg)", m) == "before_clamping"
    assert harmonise_spectrometer_stage("160 mmHg", m) == "during_clamping_160mmHg"


@pytest.mark.parametrize("split", [1, 3, 4, 7])
def test_block_tracker_is_chunk_invariant(split):
    t = np.arange(len(STAGES), dtype=float)
    whole = BlockTracker().update(STAGES, t)
    bt = BlockTracker()
    parts = [bt.update(STAGES[i:i + split], t[i:i + split]) for i in range(0, len(STAGES), split)]
    for k in ("stage_block_index", "pressure_mmhg", "time_in_block_s", "preceding_pressure_mmhg"):
        np.testing.assert_array_equal(np.concatenate([p[k] for p in parts]), whole[k])
    assert list(whole["stage_block_index"]) == [0, 0, 0, 1, 1, 2, 2, 3, 3, 4]
    prev = whole["preceding_pressure_mmhg"]
    assert np.isnan(prev[:5]).all() and list(prev[5:7]) == [20, 20] and prev[9] == 40
    assert list(whole["time_in_block_s"][:5]) == [0, 1, 2, 0, 1]


def test_running_cumcount_across_chunks():
    keys = pd.Series(list("aabab" + "bba"))
    state = Counter()
    a = _running_cumcount(keys.iloc[:5].reset_index(drop=True), state)
    b = _running_cumcount(keys.iloc[5:].reset_index(drop=True), state)
    assert list(np.concatenate([a, b])) == list(keys.groupby(keys).cumcount())


def test_arr_nulls_and_ranges():
    a = arr(np.array([1.0, np.nan, 3.0]), pa.int16())
    assert a.to_pylist() == [1, None, 3]
    s = arr(np.array(["x", None], dtype=object), pa.string())
    assert s.to_pylist() == ["x", None]          # never the string 'nan'
    with pytest.raises((pa.ArrowInvalid, OverflowError)):
        arr(np.array([300]), pa.int8())          # out-of-range values are rejected, not wrapped


def test_every_table_schema_has_documented_columns():
    for spec in S.ALL_TABLES.values():
        sch = spec.schema()
        assert set(spec.primary_key) <= set(spec.names)
        for f in sch:
            assert f.metadata[b"description"] and b"origin" in f.metadata


def test_make_table_rejects_missing_columns():
    with pytest.raises(KeyError):
        make_table(S.REF_STAGES, {"stage": ["x"]}, S.REF_STAGES.schema())
