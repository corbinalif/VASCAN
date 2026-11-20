# Phase F · Consolidation (S17–S18)

![status](https://img.shields.io/badge/status-not%20started-6E7781?style=flat-square)

Work package 7, months 10–12 of the [implementation plan](../docs/PMHM_Implementation_Plan.pdf). Nothing here is implemented yet; this folder is where the work will go.

| Step | Goal | Status |
|:--|:--|:--|
| **S17** Sensitivity battery | Re-run the primary conclusions (H1 in both arms, RQ2, H2) over the grid frozen in S2: dark scenario, cross-talk on or off, flagged frames in or out, window and plateau lengths, reference choice, ROI subset, negative spectrometer values kept or clipped, and Beer–Lambert fit variant. A conclusion counts as robust only if it holds at every grid point | not started |
| **S18** Reports, release and manuscript | Generate reports R1–R6 from run outputs, re-run from a clean checkout and confirm the output checksums match, write the manuscript, and prepare the release package | not started |

## Optional extension: SX

**Standalone file v2 with all ten participants.** This would remove the two-participant limit on the camera analyses. It needs the raw release (about 250 GB) and the archived pipeline in [`../phase_0_data_engineering/`](../phase_0_data_engineering/). Participants would be downloaded and processed one at a time, then S1 and S3–S18 re-run unchanged on v2. The decision is due at milestone M1.
