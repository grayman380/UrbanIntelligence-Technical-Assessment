# Python Imports
import os
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib as mpl
from typing import Literal
import time

import rasterio
import rasterio.plot


def load_school_demographics() -> gpd.GeoDataFrame:
    """Load the demographics_by_school.geojson file and return it as a GeoDataFrame."""

    if 'demographics_by_school.geojson' not in os.listdir('./data/task2/outputs'):
        print('The demographics_by_school.geojson file does not exist. ' +
              'Please run the national_schools_analysis.py script first.')
        return

    return gpd.read_file('./data/task2/outputs/demographics_by_school.geojson').set_index('School Name')


def generate_overlay_of_schools_and_classification(demographics_by_school: gpd.GeoDataFrame,
                                                   mode: Literal['view', 'save']) -> None:
    """Generate an overlay of the schools and the flood vulnerability classification raster.
    The schools will be plotted as magenta points with the school name as a label. The flood vulnerability
    classification will be plotted as a raster with colours differentiating the classifications."""

    if mode not in ['view', 'save']:
        raise ValueError('mode must be either "view" or "save"')

    with rasterio.open('./data/task1/outputs/Flood_vulnerability_classification.tif') as src:

        fig, ax = plt.subplots(figsize=(15, 15*(3253/2090)))  # Set the aspect ratio to match the raster

        # Plot the Schools
        demographics_by_school = demographics_by_school.to_crs('epsg:2193')   # changing to the raster coordinate system
        demographics_by_school.plot(ax=ax, color='magenta', markersize=15)    # plot the schools (scatter plot)

        # Add labels to the schools
        label_iter = zip(demographics_by_school.geometry.x,
                         demographics_by_school.geometry.y,
                         demographics_by_school.index)
        for x, y, label in label_iter:
            if x < src.bounds.left or x > src.bounds.right or y < src.bounds.bottom or y > src.bounds.top:
                continue  # Skip the label if it's outside the bounds of the raster

            ax.annotate(label, xy=(x, y), xytext=(3, 3), textcoords="offset points", fontsize=6, color='white')

        # Plot the flood vulnerability classification with a legend
        cmap = mpl.colors.ListedColormap(['darkblue', 'lightblue', 'darkgreen', 'lightgreen', 'yellow', 'red'])
        rasterio.plot.show(src, ax=ax, cmap=cmap)
        plt.legend(handles=[
            mpatches.Patch(color='red', label='H6'),
            mpatches.Patch(color='yellow', label='H5'),
            mpatches.Patch(color='lightgreen', label='H4'),
            mpatches.Patch(color='darkgreen', label='H3'),
            mpatches.Patch(color='lightblue', label='H2'),

        ], loc='lower left')

        # Set the title and legend
        ax.set_title('School Locations on Flood Hazard Vulnerability Classifications in Selwyn')
        ax.set_axis_off()

    if mode == 'view':
        plt.show()
    else:
        start = time.perf_counter()
        print('Saving the map...', end=' ', flush=True)
        plt.savefig('./data/task3/outputs/School_and_classification_overlay.png', bbox_inches='tight', dpi=1000)
        print(f'Done. Took: {time.perf_counter() - start:.2f} seconds.')


def calculate_square_meter_for_each_classification() -> dict:
    """Calculate the square meters for each classification in the flood vulnerability classification raster."""

    with rasterio.open('./data/task1/outputs/Flood_vulnerability_classification.tif') as src:
        flood_vulnerability_classification = src.read(1)

        unique, counts = np.unique(flood_vulnerability_classification, return_counts=True)
        counts = dict(zip(unique, counts))

        for classification, count in counts.items():
            print(f'H{classification}: Count: {count} square meters')


def main():

    demographics_by_school = load_school_demographics()

    generate_overlay_of_schools_and_classification(demographics_by_school, 'save')

    calculate_square_meter_for_each_classification()


if __name__ == '__main__':
    os.system('clear')

    main()
