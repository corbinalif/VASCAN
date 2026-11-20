# PMHM Parquet validation report — pilot_subject_01

_Validated 2026-11-14T17:03:16Z — output `data/processed/pilot_subject_01`_

**114 passed · 1 warnings · 0 failed** (of 115 checks)

| Table | Check | Status | Detail |
|---|---|---|---|
| master_rois | schema_matches_spec | PASS | 27 columns |
| master_rois | column_metadata_embedded | PASS |  |
| master_rois | table_metadata_embedded | PASS |  |
| master_rois | no_nulls_in_required_columns | PASS | ok |
| master_rois | row_count_matches_catalog | PASS | 71344 vs 71344 |
| master_rois | sha256_matches_catalog | PASS |  |
| master_rois | primary_key_unique | PASS | 71344 vs 71344 |
| master_rois | raw_sources_unchanged_since_conversion | PASS | 5 sources verified |
| master_frames | schema_matches_spec | PASS | 13 columns |
| master_frames | column_metadata_embedded | PASS |  |
| master_frames | table_metadata_embedded | PASS |  |
| master_frames | no_nulls_in_required_columns | PASS | ok |
| master_frames | row_count_matches_catalog | PASS | 17576 vs 17576 |
| master_frames | sha256_matches_catalog | PASS |  |
| master_frames | primary_key_unique | PASS | 17576 vs 17576 |
| master_frames | raw_sources_unchanged_since_conversion | PASS | 0 sources verified |
| master_spectrometer | schema_matches_spec | PASS | 14 columns |
| master_spectrometer | column_metadata_embedded | PASS |  |
| master_spectrometer | table_metadata_embedded | PASS |  |
| master_spectrometer | no_nulls_in_required_columns | PASS | ok |
| master_spectrometer | row_count_matches_catalog | PASS | 438900 vs 438900 |
| master_spectrometer | sha256_matches_catalog | PASS |  |
| master_spectrometer | primary_key_unique | PASS | 8 row groups, 8 distinct (subject,stage,ROI), 0 duplicate keys |
| master_spectrometer | raw_sources_unchanged_since_conversion | PASS | 1 sources verified |
| optics_ximea_filters | schema_matches_spec | PASS | 8 columns |
| optics_ximea_filters | column_metadata_embedded | PASS |  |
| optics_ximea_filters | table_metadata_embedded | PASS |  |
| optics_ximea_filters | no_nulls_in_required_columns | PASS | ok |
| optics_ximea_filters | row_count_matches_catalog | PASS | 9616 vs 9616 |
| optics_ximea_filters | sha256_matches_catalog | PASS |  |
| optics_ximea_filters | primary_key_unique | PASS | 9616 vs 9616 |
| optics_ximea_filters | raw_sources_unchanged_since_conversion | PASS | 1 sources verified |
| optics_xenon_light_source | schema_matches_spec | PASS | 5 columns |
| optics_xenon_light_source | column_metadata_embedded | PASS |  |
| optics_xenon_light_source | table_metadata_embedded | PASS |  |
| optics_xenon_light_source | no_nulls_in_required_columns | PASS | ok |
| optics_xenon_light_source | row_count_matches_catalog | PASS | 2033 vs 2033 |
| optics_xenon_light_source | sha256_matches_catalog | PASS |  |
| optics_xenon_light_source | primary_key_unique | PASS | 2033 vs 2033 |
| optics_xenon_light_source | raw_sources_unchanged_since_conversion | PASS | 1 sources verified |
| color_checker_spectrometer_adapted | schema_matches_spec | PASS | 8 columns |
| color_checker_spectrometer_adapted | column_metadata_embedded | PASS |  |
| color_checker_spectrometer_adapted | table_metadata_embedded | PASS |  |
| color_checker_spectrometer_adapted | no_nulls_in_required_columns | PASS | ok |
| color_checker_spectrometer_adapted | row_count_matches_catalog | PASS | 3840 vs 3840 |
| color_checker_spectrometer_adapted | sha256_matches_catalog | PASS |  |
| color_checker_spectrometer_adapted | primary_key_unique | PASS | 3840 vs 3840 |
| color_checker_spectrometer_adapted | raw_sources_unchanged_since_conversion | PASS | 1 sources verified |
| color_checker_frames | schema_matches_spec | PASS | 6 columns |
| color_checker_frames | column_metadata_embedded | PASS |  |
| color_checker_frames | table_metadata_embedded | PASS |  |
| color_checker_frames | no_nulls_in_required_columns | PASS | ok |
| color_checker_frames | row_count_matches_catalog | PASS | 480 vs 480 |
| color_checker_frames | sha256_matches_catalog | PASS |  |
| color_checker_frames | primary_key_unique | PASS | 480 vs 480 |
| color_checker_frames | raw_sources_unchanged_since_conversion | PASS | 0 sources verified |
| ref_channels | schema_matches_spec | PASS | 13 columns |
| ref_channels | column_metadata_embedded | PASS |  |
| ref_channels | table_metadata_embedded | PASS |  |
| ref_channels | no_nulls_in_required_columns | PASS | ok |
| ref_channels | row_count_matches_catalog | PASS | 16 vs 16 |
| ref_channels | sha256_matches_catalog | PASS |  |
| ref_channels | primary_key_unique | PASS | 16 vs 16 |
| ref_channels | raw_sources_unchanged_since_conversion | PASS | 3 sources verified |
| ref_stages | schema_matches_spec | PASS | 6 columns |
| ref_stages | column_metadata_embedded | PASS |  |
| ref_stages | table_metadata_embedded | PASS |  |
| ref_stages | no_nulls_in_required_columns | PASS | ok |
| ref_stages | row_count_matches_catalog | PASS | 10 vs 10 |
| ref_stages | sha256_matches_catalog | PASS |  |
| ref_stages | primary_key_unique | PASS | 10 vs 10 |
| ref_stages | raw_sources_unchanged_since_conversion | PASS | 1 sources verified |
| ref_subjects | schema_matches_spec | PASS | 14 columns |
| ref_subjects | column_metadata_embedded | PASS |  |
| ref_subjects | table_metadata_embedded | PASS |  |
| ref_subjects | no_nulls_in_required_columns | PASS | ok |
| ref_subjects | row_count_matches_catalog | PASS | 1 vs 1 |
| ref_subjects | sha256_matches_catalog | PASS |  |
| ref_subjects | primary_key_unique | PASS | 1 vs 1 |
| ref_subjects | raw_sources_unchanged_since_conversion | PASS | 1 sources verified |
| master_frames | rowcount_vs_cube_frames[subject_01] | PASS | 17576 vs 17576 |
| master_frames | values_identical_to_cube_meta[subject_01] | PASS |  |
| master_frames | time_monotonic[subject_01] | PASS |  |
| master_rois | rowcount[subject_01/roi_1] | PASS | 17836 vs 17836 |
| master_rois | values_identical_to_source[subject_01/roi_1] | PASS | intermediates/rois/subject_01/roi_1.csv |
| master_rois | rowcount[subject_01/roi_2] | PASS | 17836 vs 17836 |
| master_rois | values_identical_to_source[subject_01/roi_2] | PASS | intermediates/rois/subject_01/roi_2.feather |
| master_rois | rowcount[subject_01/roi_3] | PASS | 17836 vs 17836 |
| master_rois | values_identical_to_source[subject_01/roi_3] | PASS | intermediates/rois/subject_01/roi_3.csv |
| master_rois | csv_feather_copies_identical[subject_01/roi_3] | PASS | intermediates/rois/subject_01/roi_3.feather |
| master_rois | rowcount[subject_01/roi_4] | PASS | 17836 vs 17836 |
| master_rois | values_identical_to_source[subject_01/roi_4] | PASS | intermediates/rois/subject_01/roi_4.feather |
| master_rois | rows_equal_sum_of_sources | PASS | 71344 vs 71344 |
| master_rois | frame_join_exact | PASS | 70304 matched rows |
| master_rois | unmatched_rows_are_after_cube_end | PASS | 1040 rows tracked after last cube frame (kept, frame_index=null) |
| master_rois | derived_bbox_consistent | PASS |  |
| master_frames | n_rois_tracked_consistent | PASS |  |
| master_rois | bbox_within_image | PASS | 0 out-of-bounds boxes |
| master_spectrometer | every_row_identical_to_csv | PASS | 438,900 rows compared, 0 mismatching chunks, 0 extra parquet rows |
| master_spectrometer | rowcount_vs_csv | PASS | 438900 vs 438900 |
| master_spectrometer | identical_to_feather_copy | PASS | data/spectrometer/spectrometer.feather |
| master_spectrometer | every_spectrum_has_full_wavelength_grid | PASS | 798 spectra, 0 incomplete |
| master_spectrometer | replicate_order_coherent(min adjacent-wl corr across groups) | PASS | min 0.991, median 0.997 over 8 groups |
| master_spectrometer | negative_reflectance_values | **WARN** | 401 rows < 0 (kept unmodified; flagged) |
| optics_ximea_filters | rowcount_vs_source | PASS | 9616 vs 9616 |
| optics_ximea_filters | values_identical_to_csv | PASS |  |
| optics_ximea_filters | values_identical_to_feather_copy(atol 1e-12) | PASS | 1414 float values differ in last digits (max 1.0e-16; CSV text rounding) |
| optics_xenon_light_source | rowcount_vs_source | PASS | 2033 vs 2033 |
| optics_xenon_light_source | values_identical_to_csv | PASS |  |
| optics_xenon_light_source | values_identical_to_feather_copy(atol 1e-12) | PASS | 0 float values differ in last digits (max 0.0e+00; CSV text rounding) |
| color_checker_spectrometer_adapted | rowcount_vs_source | PASS | 3840 vs 3840 |
| color_checker_spectrometer_adapted | values_identical_to_csv | PASS |  |
| color_checker_spectrometer_adapted | values_identical_to_feather_copy(atol 1e-12) | PASS | 0 float values differ in last digits (max 0.0e+00; CSV text rounding) |
| ref_channels | filter_peak_within_3nm_of_nominal | PASS | max /diff/ 2 nm |
| ref_channels | colorchecker_band_mapping_matches_nominal | PASS |  |

## Data-quality findings (informational)

```json
{
 "timeline_gaps_over_1s": [
  {
   "subject_id": "subject_01",
   "stage_block_index": 1,
   "stage": "during_clamping_20mmHg",
   "time_delta_s": 159.027,
   "frame_interval_s": 35.376
  }
 ],
 "frame_interval_median_s": {
  "subject_01": 0.04
 },
 "roi_displacement_px": [
  {
   "subject_id": "subject_01",
   "roi_id": 1,
   "mean": 0.09799999743700027,
   "max": 3.1619999408721924
  },
  {
   "subject_id": "subject_01",
   "roi_id": 2,
   "mean": 0.07999999821186066,
   "max": 3.1619999408721924
  },
  {
   "subject_id": "subject_01",
   "roi_id": 3,
   "mean": 0.07999999821186066,
   "max": 3.1619999408721924
  },
  {
   "subject_id": "subject_01",
   "roi_id": 4,
   "mean": 0.07999999821186066,
   "max": 3.1619999408721924
  }
 ],
 "roi_rows_without_frame": 1040,
 "xenon_negative_irradiance_rows": 491
}
```
