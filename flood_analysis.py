# Python Imports
import rasterio
import rasterio.enums
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
import time


def resample_raster_data(raster: rasterio.io.DatasetReader, desired_resolution: tuple) -> np.array:
    """Resample the raster data to a higher resolution."""

    resolution_multiplier = (raster.res[0] / desired_resolution[0],
                             raster.res[1] / desired_resolution[1])

    # Resample the raster to a higher resolution
    resampled_data = raster.read(
        out_shape=(
            raster.count,
            int(raster.height * resolution_multiplier[0]),
            int(raster.width * resolution_multiplier[1])
        ),
        resampling=rasterio.enums.Resampling.bilinear
    )[0]

    print('Resample Complete. New Shape:', resampled_data.shape)
    return resampled_data


def calculate_resampled_transform(raster: rasterio.io.DatasetReader, desired_resolution: tuple
                                  ) -> rasterio.transform.Affine:
    """Calculate the transform for the resampled raster."""
    transform = raster.transform
    return rasterio.transform.from_origin(
        transform.c,
        transform.f,
        desired_resolution[0],
        desired_resolution[1]
    )


def classify_score(depth: float, velocity: float) -> str:
    """Inner-function to classify the flood hazard vulnerability based on the flood depth and velocity.
    Based on Section 5.5 of Smith et al. (2014)."""
    score = depth * velocity

    if score <= 0.3 and depth <= 0.3 and velocity <= 2.0:
        return 1
    if score <= 0.6 and depth <= 0.5 and velocity <= 2.0:
        return 2
    if score <= 0.6 and depth <= 1.2 and velocity <= 2.0:
        return 3
    if score <= 1.0 and depth <= 2.0 and velocity <= 2.0:
        return 4
    if score <= 4.0 and depth <= 2.0 and velocity <= 4.0:
        return 5
    return 6


def classify_flood_hazard_vulnerability(flood_depth: np.array, flood_velocity: np.array) -> np.array:
    """Classify the flood hazard vulnerability based on the flood depth and velocity."""

    start = time.perf_counter()  # 118.43s

    flood_vulnerability_classification = np.vectorize(classify_score)(flood_depth, flood_velocity)

    print(f'Classification Took: {time.perf_counter() - start:.2f} seconds.')

    return flood_vulnerability_classification


def save_flood_vulnerability_classification_raster(flood_vulnerability_classification: np.array,
                                                   metadata: dict, transform: rasterio.transform.Affine
                                                   ) -> None:
    """Save the flood vulnerability classification raster."""
    print('Saving Flood Vulnerability Classification Raster...', end=' ', flush=True)

    with rasterio.open(
        './data/task1/outputs/Flood_vulnerability_classification.tif',
        'w',
        driver=metadata['driver'],
        height=flood_vulnerability_classification.shape[0],
        width=flood_vulnerability_classification.shape[1],
        count=1,
        dtype=flood_vulnerability_classification.dtype,
        crs=metadata['crs'],
        transform=transform
    ) as dst:
        dst.write(flood_vulnerability_classification, 1)

    print('Done.')


def save_flood_vulnerability_classification_colourmap(flood_vulnerability_classification: np.array) -> None:
    """Save the flood vulnerability classification raster as a colourmap."""
    print('Saving Flood Vulnerability Classification Colormap...', end=' ', flush=True)

    plt.imsave(
        'data/task1/outputs/Flood_vulnerability_classification_Colormap.png',
        flood_vulnerability_classification,
        cmap=mpl.colors.ListedColormap(['darkblue', 'lightblue', 'darkgreen', 'lightgreen', 'yellow', 'red'])
    )

    print('Done.')


def main():
    desired_resolution = (1, 1)

    # Open, process the flood depth raster data, and close the raster
    # Also get the metadata for creating the new raster, and the transform for the resampled raster
    # This can be done for either dataset, as they have the same resolution
    with rasterio.open('./data/task1/inputs/Flood_depth_metres.tif') as flood_depth_raster:
        flood_depth_data = resample_raster_data(flood_depth_raster, desired_resolution)
        flood_depth_metadata = flood_depth_raster.meta
        one_meter_transform = calculate_resampled_transform(flood_depth_raster, desired_resolution)

    # Open, process the flood velocity raster data, and close the raster
    with rasterio.open('./data/task1/inputs/Flood_velocity_metres_per_second.tif') as flood_velocity_raster:
        flood_velocity_data = resample_raster_data(flood_velocity_raster, desired_resolution)

    # Classify the flood hazard vulnerability
    flood_vulnerability_classification = classify_flood_hazard_vulnerability(flood_depth_data, flood_velocity_data)

    # Save the hazard score raster, using the appropriate metadata and transform
    save_flood_vulnerability_classification_raster(flood_vulnerability_classification, flood_depth_metadata,
                                                   one_meter_transform)

    # Save the raster as a colourmap
    save_flood_vulnerability_classification_colourmap(flood_vulnerability_classification)


if __name__ == '__main__':
    import os
    os.system('clear')

    main()
