# Validation — standalone file `data/processed/spectralpaca_pmhm_dataset.parquet`

_Validated 2026-11-14T17:29:17Z_

- Size: 59.3 MB · rows: 4,586,255 · sha256 `eb77b66a76f27eab5a053fe564954d9fe4ef584423f1053cb46542ac38961226`
- **22 passed · 1 warnings · 0 failed**

| record_type | rows |
|---|---|
| roi_frame | 125,323 |
| frame | 48,157 |
| spectrometer | 4,397,250 |
| camera_filter | 9,616 |
| light_source | 2,033 |
| color_checker | 3,840 |
| channel | 16 |
| stage | 10 |
| subject | 10 |

| Check | Status | Detail |
|---|---|---|
| schema_matches_spec | PASS | 81 columns |
| column_docs_embedded | PASS |  |
| file_metadata_embedded | PASS |  |
| rows[roi_frame]_equal_master_rois | PASS | 125323 vs 125323 |
| rows[frame]_equal_master_frames | PASS | 48157 vs 48157 |
| rows[spectrometer]_equal_master_spectrometer | PASS | 4397250 vs 4397250 |
| rows[camera_filter]_equal_optics_ximea_filters | PASS | 9616 vs 9616 |
| rows[light_source]_equal_optics_xenon_light_source | PASS | 2033 vs 2033 |
| rows[color_checker]_equal_color_checker_spectrometer_adapted | PASS | 3840 vs 3840 |
| rows[channel]_equal_ref_channels | PASS | 16 vs 16 |
| rows[stage]_equal_ref_stages | PASS | 10 vs 10 |
| rows[subject]_equal_ref_subjects | PASS | 10 vs 10 |
| no_unknown_record_types | PASS | ['camera_filter', 'channel', 'color_checker', 'frame', 'light_source', 'roi_frame', 'spectrometer', 'stage', 'subject'] |
| each_row_group_single_record_type | PASS | 96 row groups |
| spectrometer_values_identical | PASS | 80 row groups compared |
| roi_rows_match_master_rois_1to1 | PASS | {'both': 125323, 'left_only': 0, 'right_only': 0} |
| roi_coordinates_time_frame_identical | PASS |  |
| spectral_values_present_iff_image_frame | PASS | 123527 with values, 1796 without (tracked after cube end) |
| roi_spectra_recomputed_from_cube | PASS | 400 random ROI-frames re-extracted via full-frame read; max relative diff 5.88e-08 |
| provenance_present[frame] | PASS | 0 null source_file |
| provenance_present[subject] | WARN | 2 null source_file (subjects with no cube in the download) |
| provenance_present[stage] | PASS | 0 null source_file |
| provenance_present[channel] | PASS | 0 null source_file |
