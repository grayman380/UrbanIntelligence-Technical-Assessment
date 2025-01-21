# Python Imports
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from typing import Literal


# FUNCTIONS FOR LOADING AND PROCESSING THE DATA #
def open_and_filter_schools_data() -> pd.DataFrame:
    """Opens the national schools data, filters it to only include the relevant columns,
    and cleans up the data."""
    # Load the data
    national_schools = pd.read_csv('./data/task2/inputs/national_schools.csv', header=15).iloc[1:, :]

    # Filter the data. We only want certain variables for each school.
    national_schools = national_schools[
        ['School Number', 'School Name', 'Street', 'Suburb', 'Town / City', 'School Type',
         'Equity Index (EQI)', 'Latitude', 'Longitude', 'Total School Roll']
    ]

    # Replace the street column with the full address
    address = (
        national_schools['Street'].str.strip() + ', ' +
        national_schools['Suburb'] + ', ' +
        national_schools['Town / City']
    )
    national_schools.insert(2, 'Address', address)
    national_schools = national_schools.drop(columns=['Street'])

    # Clean up the data
    national_schools = (national_schools
                        .dropna(subset=['Latitude', 'Longitude'])  # Drop rows with no location data
                        .dropna(subset=['Total School Roll'])      # Drop rows with no school roll data
                        .replace('not applicable', np.nan)         # Convert 'not applicable' to NaN
                        )

    return national_schools


def open_and_filter_census_data() -> gpd.GeoDataFrame:
    """Opens the census data, assigns usefil names to the columns via a lookup table,
    filters it to only include the relevant columns, and cleans up the data."""
    # Load the shapefile
    shapefile_name = '2023-census-totals-by-topic-for-individuals-by-statistical-a.shp'  # seperated to avoid line len
    shapefile_dir = 'statsnz-2023-census-totals-by-topic-for-individuals-by-statistical-a-SHP'  # same as above
    gdf: gpd.GeoDataFrame = gpd.read_file(f'./data/task2/inputs/{shapefile_dir}/{shapefile_name}')

    # Load and filter the lookup table
    lookup_table_fn = '2023_census_totals_by_topic_for_individuals_by_sa1_part_1_lookup_table.csv'
    lookup_table_dir = 'statsnz-2023-census-totals-by-topic-for-individuals-by-statistical-a-SHP'
    lookup_table = (
        pd.read_csv(f'./data/task2/inputs/{lookup_table_dir}/{lookup_table_fn}')
        .query('Year == 2023')
        [['Shapefile_name', 'Unit_count', 'Subject_population', 'Variable1', 'Variable1_category']]
    )

    # Swap the names of the columns in the gdf to be more useful.
    lookup_table['Variable1_name'] = lookup_table['Variable1'] + ' (' + lookup_table['Variable1_category'] + ')'
    variable_name_dict = lookup_table.set_index('Shapefile_name')['Variable1_name'].to_dict()
    gdf = gdf.rename(columns=variable_name_dict)

    gdf = gdf[gdf.columns.drop(list(gdf.filter(regex='VAR_')))]  # remove unused columns
    gdf['SA12023_V1'] = gdf['SA12023_V1'].astype(int)            # convert SA1 code to int (from object)

    # Replace -999 with NaN (obfuscated data to protect anonymity)
    gdf = gdf.replace(-999, np.nan)

    # Select only the columns we want
    gdf = gdf[[
        'SA12023_V1',
        "Census usually resident population count (Total)",
        "Census night population count (Total)",
        "Age (5-year groups) (0-4 years)",
        "Age (5-year groups) (5-9 years)",
        "Age (5-year groups) (10-14 years)",
        "Age (5-year groups) (15-19 years)",
        "Age (Median)",
        "Ethnicity (total responses) (European)",
        "Ethnicity (total responses) (Māori)",
        "Ethnicity (total responses) (Pacific Peoples)",
        "Ethnicity (total responses) (Asian)",
        "Ethnicity (total responses) (Middle Eastern/Latin American/African)",
        "Ethnicity (total responses) (Other Ethnicity)",
        "Ethnicity (total responses) (New Zealander)",
        "Ethnicity (total responses) (Other Ethnicity nec)",
        "Ethnicity (total responses) (Not Elsewhere Included)",
        "Māori descent indicator (Māori descent)",
        "Māori descent indicator (No Māori descent)",
        "Māori descent indicator (Don't know)",
        "Māori descent indicator (Not elsewhere included)",
        "Gender (Male / Tāne)",
        "Gender (Female / Wahine)",
        "Gender (Another gender / He ira kē anō)",
        "Gender (Total)",
        "Sex at birth (Male/Tāne)",
        "Sex at birth (Female/Wahine)",
        "Sex at birth (Total)",
        "Sexual identity (Heterosexual)",
        "Sexual identity (Homosexual)",
        "Sexual identity (Bisexual)",
        "Sexual identity (Sexual identity not elsewhere classified)",
        "Sexual identity (Prefer not to say)",
        "Sexual identity (Not Elsewhere Included)",
        "Sexual identity (Total)",
        "Sexual identity (Total stated)",
        "AREA_SQ_KM",
        "LAND_AREA_",
        "Shape_Leng",
        "geometry",
    ]]

    # Reproject the geo dataframe to use lat/long coordinates
    gdf = gdf.to_crs('epsg:4326')

    return gdf


def merge_both_datasets(national_schools_df: pd.DataFrame, census_data_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Merges the national schools data with the census data using a spatial join.
    Cleans up the data and returns the merged dataset."""
    # Create a GeoDataFrame from the schools data
    national_schools_gdf = gpd.GeoDataFrame(
        national_schools_df,
        geometry=gpd.points_from_xy(national_schools_df.Longitude, national_schools_df.Latitude),
        crs=census_data_gdf.crs
    )

    # Merge the two datasets with a spacial join
    demographics_by_school = gpd.sjoin(national_schools_gdf, census_data_gdf, how='left', predicate='within')

    # Clean up the data
    demographics_by_school = (
        demographics_by_school.set_index('School Name')                        # Set the school name as the index
        .query('Longitude > 0')                                                # Filter out the Chatham Islands
        .drop(columns=['Latitude', 'Longitude', 'Shape_Leng', 'index_right'])  # Drop irrelvant columns
        .rename(columns={'SA12023_V1': 'SA1 Code'})                            # Rename the SA1 column
    )

    return demographics_by_school


def build_demographics_by_school_data(force_rebuild=False) -> gpd.GeoDataFrame:
    """Builds the demographics by school data by opening and filtering the schools and census data,
    merging the two datasets, and returning the merged dataset. If the data has already been built,
    it will instead be loaded from the file system unless force_rebuild is set to True."""

    if 'demographics_by_school.geojson' not in os.listdir('./data/task2/outputs') or force_rebuild:
        national_schools_df = open_and_filter_schools_data()
        census_data_gdf = open_and_filter_census_data()
        return merge_both_datasets(national_schools_df, census_data_gdf)
    else:
        return gpd.read_file('data/task2/outputs/demographics_by_school.geojson').set_index('School Name')


# FUNCTIONS FOR VIEWING AND PLOTTING THE DATA #
def view_school_attributes_by_name(demographics_by_school: gpd.GeoDataFrame, school_name: str) -> None:
    """Prints the attributes of a specific school, if it exists in the data."""

    if school_name not in demographics_by_school.index:
        print(f'School "{school_name}" not found in the data.\n')
        return

    print(f'Viewing School Demographics for: {school_name}'.upper())
    school_data = demographics_by_school.loc[school_name]
    print(school_data)
    print()


def view_schools_ranked_by_attribute(demographics_by_school: gpd.GeoDataFrame, attribute: str, top_n=10) -> None:
    """Prints the top N schools ranked by a specified attribute, if the attribute exists in the data."""

    if attribute not in demographics_by_school.columns:
        print(f'Attribute "{attribute}" not found in the data.\n')
        return

    print(f'Viewing Top 10 Schools Ranked by: {attribute}'.upper())
    sorted_data = demographics_by_school[attribute].sort_values(ascending=False)
    sorted_data = sorted_data.dropna()
    print(sorted_data.head(top_n).to_string())
    print()


def plot_schools_on_map_by_attribute(demographics_by_school: gpd.GeoDataFrame, attribute: str,
                                     mode=Literal['view', 'save']) -> None:
    """Plots the schools on a map, coloured by the specified attribute.
    The map can be saved or viewed, depending on the mode."""

    if mode not in ['view', 'save']:
        raise ValueError('mode must be either "view" or "save"')

    # Plot the data
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    sorted_data = demographics_by_school.sort_values(attribute)
    sorted_data.plot(column=attribute, ax=ax, legend=True, markersize=3)
    ax.set_title(f'Schools by {attribute}')

    # Save or show the plot, depending on the mode
    if mode == 'view':
        plt.show()
    else:
        print(f'Saving the map of {attribute}...', end=' ', flush=True)
        plt.savefig(f'data/task2/outputs/School_demographics ({attribute}).png', dpi=200)
        print('Done.')


def save_schools_data(demographics_by_school: gpd.GeoDataFrame):
    """Saves the demographics by school data to a GeoJSON file."""

    print('Saving the school demographics data...', end=' ', flush=True)
    demographics_by_school.to_file('./data/task2/outputs/demographics_by_school.geojson', driver='GeoJSON')
    print('Done.')


def main():
    # Build the data
    demographics_by_school = build_demographics_by_school_data(force_rebuild=False)

    # Print Some Relevant Information
    view_school_attributes_by_name(demographics_by_school, 'Dunsandel School')
    view_school_attributes_by_name(demographics_by_school, 'Ellesmere College')
    view_school_attributes_by_name(demographics_by_school, 'Leeston School')

    view_schools_ranked_by_attribute(demographics_by_school, 'Age (5-year groups) (0-4 years)')
    view_schools_ranked_by_attribute(demographics_by_school, 'Census night population count (Total)')

    # Show the schools on a map
    plot_schools_on_map_by_attribute(demographics_by_school, 'Census night population count (Total)', mode='save')
    plot_schools_on_map_by_attribute(demographics_by_school, 'Age (5-year groups) (0-4 years)', mode='save')

    # Save the data
    save_schools_data(demographics_by_school)


if __name__ == '__main__':
    os.system('clear')

    main()
