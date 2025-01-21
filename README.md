# UrbanIntelligence Technical Assessment

## Setup
First, clone this repo.

Then:
1. Click [here](https://datafinder.stats.govt.nz/layer/120766-2023-census-totals-by-topic-for-individuals-by-statistical-area-1-part-1/) and export and download the shapefile with a EPSG:4326 projection.
2. Unzip the folder and place it in ./data/task2/inputs.

This is necessary because GitHub won't let me upload data of that size.

## Running the Code
1. Setup a virtual environment with `python3 -m venv venv`.
2. Install modules with `pip install -r requirements.txt`
3. Run each of the three python files in the following order:
`flood_analysis.py`
`national_schools_analysis.py`
`flood_analysis.py`

Some data will be printed in the terminal, and some files will be put in the output folders for each task.

