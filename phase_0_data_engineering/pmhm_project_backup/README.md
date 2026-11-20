# SPECTRAL Perfusion Arm Clamping dAtaset (SPECTRALPACA) 

![files.svg](assets%2Ffiles.svg) ![size.svg](assets%2Fsize.svg) ![videos.svg](assets%2Fvideos.svg) 
![subjects.svg](assets%2Fsubjects.svg) ![images.svg](assets%2Fimages.svg) ![channels.svg](assets%2Fchannels.svg)
![perfusion.svg](assets%2Fperfusion.svg)

![Oxygenation estimation based on a machine learning model for one subject](assets%2Fanimation.gif){width=100%}

Welcome to the `SPECTRAL Perfusion Arm Clamping dAtaset (SPECTRALPACA)`.
This is a carefully curated dataset composed of video-rate spectral images of healthy volunteer human right hand 
palms. For each subject, a baseline and eight different pressure levels applied to the upper arm were recorded in a 
consecutive video stream, lasting approximately 18 minutes. In between each pressure stage, a resting state (no 
pressure applied) was also recorded for approximately one minute. These spectral videos were recorded with a 
snapshot XIMEA camera of model MQ022HG-IM-SM4x4-VIS. This camera records 16 channels for each image at wavelengths 
(nm): `[488, 496, 478, 465, 598, 609, 585, 574, 641, 493, 632, 622, 538, 550, 524, 511]`. 

To compliment these spectral videos, four different regions of interest (ROIs) were tracked in the surface of the hands 
for the entire duration of the sequence. In addition, spectrometer diffuse reflectance measurements are included for 
each ROI. Such spectrometer measurements were recorded using the HR2000+ spectrometer from Ocean Insight.

# Download
This dataset can be downloaded by running the following python script. Keep in mind that you would need to install the `synapseclient` first via `pip install synapseclient`

```python
 import synapseclient 
 import synapseutils 
 
 syn = synapseclient.Synapse() 
 syn.login() 
 files = synapseutils.syncFromSynapse(syn, ' syn51625685 ') 
```

# Usage
To facilitate the usage of this dataset, we provide sample code written in Python that can be used to load the data.
The python package can be found in the folder named `code` within the downloaded directory. Instruction on 
installing the python package can be found below.

## Installing code
To set up the environment for the code, we recommend to use Anaconda. Information on its installation 
can be found in the official page of [Anaconda](https://docs.anaconda.com/free/anaconda/install/index.html).
After installing Anaconda, you can install the code and its dependencies based on the snippet below:

```bash
conda create -n spectralpaca python=3.10
conda activate spectralpaca

cd path-to-code-root-folder
pip install .
```

Finally, you will have to create a `.env` file in the root directory of the code and populate it with the following 
information.

```bash
PATH_SPECTRALPACA_DATA="path-to-dataset-root-directory"
```

Alternatively, you can also define this variable in your environment with bash `export 
PATH_SPECTRALPACA_DATA="path-to-dataset-root-directory"`.

## Accessing spectral images 
The spectral images can be accessed through the `DataLoaderXIMEA` class. An example of its usage can be found below:
```python
from src.data import DataLoaderXIMEA

dl = DataLoaderXIMEA()
df = dl.get_file_database(
    subjects=['subject_01']
)
image = dl['subject_01'][0]
print(image)
df.head()
```

Spectral images are usually normalized using a white and dark reference image. Such reference images can be accessed 
through the data loader:

```python
from src.data import DataLoaderXIMEA

dl = DataLoaderXIMEA()
reference_map = dl._get_reference_map(load_files=True, subjects='subject_01')
print(reference_map)
```

The data associated with specific stages (e.g. 160 mmHg pressure), can be accessed as follows:
```python
from tqdm import tqdm
from src.data import DataLoaderXIMEA

dl = DataLoaderXIMEA()
subject = 'subject_01'
df = dl.get_file_database(
    subjects=['subject_01']
)
stage = 'during_clamping_160mmHg'
index = df[df.stage == stage].ind
for i in tqdm(index):
    image = dl[subject][i]
df.head()
```

## Accessing tracked ROIs
The locations of the tracked ROIs can be found in the folder `intermediates/rois`. All ROIs are stored as `csv` 
files that can be loaded with any library that supports this file format. The locations of each ROI is located in 
columns identified with the names `[x1, y1, x2, y2]`. Each row corresponds to one ROI identified by the ROI ID (file 
name), the subject ID (folder name) and the image name (`file` column). 
The data associated with each ROI can be extracted from its corresponding image `image` as follows:

```python
from src.data import DataLoaderXIMEA
import pandas as pd

dl = DataLoaderXIMEA()
df = dl.get_file_database(
    subjects=['subject_01']
)
image = dl['subject_01'][0]
roi_df = pd.read_csv(dl.data_dir / 'intermediates' / 'rois' / 'subject_01' / 'roi_1.csv', index_col=None)
x1 = int(roi_df.iloc[0].x1)
x2 = int(roi_df.iloc[0].x2)
y1 = int(roi_df.iloc[0].y1)
y2 = int(roi_df.iloc[0].y2)

image_roi = image[y1:y2, x1:x2, ...]
print(image_roi.shape)
```

## Accessing spectrometer data
The spectrometer data are located in the file `data/spectrometer/spectrometer.csv`. It can be loaded with any standard 
library that supports this file format. Within this file you will find useful identifiers such as the subject ID number,
the ROI ID, and the functional state of the tissue: baseline (before_clamping) and 160 mmHg pressure applied to the 
upper arm. 

## Converting data to other formats
For convenience, we provide a script to convert the spectral images to other formats, if desired. The
script can be accessed in `src/data/convert_data.py`.

# Dataset structure
The dataset structure can be found below. Notice that the `.dat` file format in this dataset correspond to compressed 
[blosc2 NDArrays](https://www.blosc.org/python-blosc2/python-blosc2.html#ndarray-an-n-dimensional-store). Each file 
can be read individually via `blosc2.opne(file_path, mode='r')`. A simple way to access each file was presented in 
the section `Usage` of this file.

```
├── data/ % Primary human data
│   ├── README.md % this README file
│   ├── assets/ % folder containing images to be rendered in the README file by differend IDEs
│   ├── code/ % directory containing a python package that can be used to load the data
│   ├── ximea/ % Individual recordings collected with the XIMEA camera
│   │   ├── white.npy % white target reference
│   │   ├── dark.npy % dark measurement reference
│   │   ├── subject_##.dat % spectral data for subject number: <##>
│   │   └── [more subjects]
│   ├── spectrometer/ % folder containing all spectrometer data for each subject
│   │   ├── spectrometer.csv % file containing diffuse reflectance data for all ROIs and for all subjects
│   │   └── spectrometer.feather % same as spectrometer.csv, but in `feather` format for faster loading
│   └── metadata.json  % JSON file containing metadata used by the data loader and data set descriptors
│
└── intermediates/ % Processed data
    ├── optics/
    │   ├──  ximea_filters.csv % spectral response of the camera filters
    │   ├──  ximea_filters.feather % spectral response of the camera filters in feather format
    │   ├──  xenon_light_source.csv % relative irradiance of xenon light source
    │   └──  xenon_light_source.feather % relative irradiance of xenon light source in feather format
    └── rois/  % folder containing all the tracked regions of interest
        ├── subject_##/ % Folder with all tracker regions of interest for subject number: <##>
        │    ├── roi_N.csv % file containing the coordinates of one ROI identified with the number <N> for the entire video sequence
        │    ├── roi_N.feather % same as roi_N.csv, but in `feather` format for faster loading
        │    ├── [more ROIs]
        │    └──  roi_tracking_rgb.mp4 % animation showing the entire video sequence of each subject and all tracked ROIs
        └── [more subjects]
```

# Questions?
If you have questions regarding this dataset, you can contact us via e-mail at [office-maier-hein@dkfz-heidelberg.de](mailto:office-maier-hei@dkfz-heidelberg.de).

# License
<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.

# Acknowledgements 

This project has received funding from the European Research Council (ERC) under the European Union’s Horizon 2020 
research and innovation programme (NEURAL SPICING, Grant agreement No. 101002198) and was supported by the 
German Cancer Research Center (DKFZ) and the Helmholtz Association under the joint research school 
HIDSS4Health (Helmholtz Information and Data Science School for Health).
