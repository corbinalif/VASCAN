# Optimized Data Engineering and Exploratory Data Analysis Pipeline for the SPECTRALPACA Dataset

## 1. Project Overview

This project proposes the development of a resource-efficient, reproducible, and scalable end-to-end data engineering and exploratory data analysis (EDA) pipeline for the **SPECTRAL Perfusion Arm Clamping Dataset (SPECTRALPACA)**, designed specifically to operate within constrained local hardware environments while establishing a reliable foundation for subsequent hyperspectral image processing and machine learning research.

Given the dataset's approximately 82 GB storage footprint and its combination of high-dimensional hyperspectral image arrays, ROI tracking coordinates, optical calibration references, spectrometer measurements, and experimental metadata across ten healthy subjects, the proposed architecture will separate tabular data engineering from computationally intensive spatial-spectral image processing.

## 2. Data Engineering Architecture

Rather than loading multi-gigabyte raw hyperspectral image cubes (`.b2nd`) into system memory simultaneously, the pipeline will recursively inspect the dataset directory, identify supported structured files, and ingest ROI coordinates, spectrometer readings, calibration tables, and relevant metadata through a memory-safe, chunk-based streaming process using Python, Pandas, and PyArrow.

Compatible tabular datasets will be converted into Snappy-compressed Parquet files, with separate master datasets maintained for distinct data categories where their schemas or measurement structures differ, rather than forcing incompatible records into a single table.

The resulting data architecture will include:

- A consolidated ROI dataset (`master_rois.parquet`).
- Organized spectrometer measurement tables.
- Optical calibration and metadata tables.
- Supporting conversion manifests documenting source files, row counts, schemas, data types, processing status, and validation results.

Data provenance will be preserved through appropriate subject identifiers, ROI identifiers, frame references, experimental conditions, and source-file information wherever these fields are available.

Before full-scale conversion, the pipeline will execute a controlled pilot on a representative subject, followed by automated integrity checks comparing source and output file counts, row totals, column structures, data types, missing values, and selected record-level values. Raw source files will remain unchanged and be treated as read-only inputs throughout the workflow.

## 3. Hyperspectral Image Processing Architecture

In parallel, the original multidimensional hyperspectral arrays and reference images (`white.npy` and `dark.npy`) will remain in their native formats and be accessed on demand through the dataset's native `DataLoaderXIMEA` abstraction and other compatible lazy-loading mechanisms.

This approach will enable targeted frame-level retrieval and processing without requiring complete image cubes to reside in RAM.

The image-processing workflow will incorporate:

- Dark- and white-reference correction.
- Reflectance normalization where supported by the acquisition data.
- Spectral channel inspection.
- Signal-to-noise assessment.
- Identification of invalid measurements, missing frames, tracking inconsistencies, and unsuitable spectral channels.
- ROI-based spectral and temporal feature extraction.

ROI coordinates will be linked with their corresponding image frames to extract localized spectral and temporal measurements across available experimental conditions, including baseline, pressure-induced clamping stages, and post-clamping recovery or reperfusion periods.

Particular attention will be given to maintaining synchronization between image frames, ROI tracking records, spectrometer measurements, and experimental stage annotations.

## 4. Exploratory Data Analysis (EDA)

The EDA phase will investigate:

- Subject-level and ROI-level data distributions.
- Spectral-channel behavior and variation.
- Temporal response patterns during clamping and recovery.
- Inter-subject physiological variability.
- Changes across experimental conditions.
- Missing-data characteristics and data-quality issues.
- Relationships between image-derived features and reference spectrometer measurements.

Appropriate visualizations and statistical summaries will be generated to identify data-quality issues, characterize physiological response patterns, and guide the selection of meaningful features for subsequent modeling.

## 5. Computational Environment and Hardware Optimization

The complete workflow will be developed in a modular Python research environment, with a dedicated Jupyter kernel (`afrolalon`) used for interactive analysis and a reproducible project structure separating:

- Raw data.
- Intermediate outputs.
- Processed datasets.
- Scripts.
- Notebooks.
- Configurations.
- Logs.
- Research results.

CPU-efficient streaming and conservative memory allocation will be prioritized for tabular conversion, while CUDA-enabled GPU resources will be reserved for computationally appropriate downstream image-processing and deep-learning tasks.

The architecture will also support future execution against read-only external or cloud-mounted datasets, provided that the storage interface supports the required access patterns.

## 6. Reproducibility and Data Integrity

Reproducibility will be maintained through:

- Documented processing configurations.
- Dependency and environment records.
- Execution logs.
- Conversion manifests.
- Automated validation reports.
- Version-controlled source code.
- Preservation of original raw data.

The pipeline will be designed to avoid unnecessary data duplication, prevent silent data loss, and maintain traceability between processed outputs and their original source files.

## 7. Expected Outcomes

The expected outcome is a validated, query-efficient, and well-documented analytical data foundation that:

1. Reduces unnecessary memory consumption.
2. Improves structured-data accessibility.
3. Preserves the integrity of original measurements.
4. Enables efficient ROI-based image retrieval.
5. Supports synchronized spectral and temporal analysis.
6. Establishes a reproducible foundation for downstream statistical analysis and machine learning.
7. Enables reliable exploratory investigation of peripheral tissue perfusion dynamics.

## 8. Scientific Scope and Limitations

SPECTRALPACA contains measurements from ten healthy volunteers and uses a 16-channel visible-spectrum camera. Therefore, the resulting pipeline will initially support technical development and physiological response analysis rather than establish clinical diagnostic validity or demonstrate direct detection of peripheral arterial disease (PAD).

The proposed framework will provide a foundation for future research into hyperspectral assessment of peripheral tissue oxygenation and microvascular responses, subject to appropriate independent reference measurements and clinical validation in relevant patient populations.

## 9. Final Implementation Recommendation

One implementation decision should remain open until the dataset inventory is complete: whether the spectrometer, calibration, and metadata tables can be safely joined into unified analytical tables or should remain separate Parquet datasets.

That decision must be based on their actual schemas, identifiers, measurement structures, and relationships—not assumptions.

The initial implementation should therefore follow this sequence:

1. Inspect and inventory the complete dataset.
2. Identify supported tabular files and their schemas.
3. Design the Parquet conversion architecture.
4. Execute a controlled single-subject pilot.
5. Validate data integrity and conversion accuracy.
6. Perform full-scale tabular conversion.
7. Implement lazy hyperspectral image access.
8. Develop calibration and ROI-based preprocessing.
9. Perform structured EDA and generate research reports.
10. Document the validated pipeline for subsequent machine learning development.