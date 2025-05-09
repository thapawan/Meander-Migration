import ee
import geemap
import math
import numpy as np
from typing import List, Tuple, Dict

# Initialize Google Earth Engine
try:
    ee.Initialize()
except Exception as e:
    print(f"An error occurred while initializing Earth Engine: {e}")
    print("Please check your authentication and try again.")
    exit()

# 1. Define Study Area and Time Period
# ====================================
study_area = ee.FeatureCollection("users/yourusername/Yazoo_River_AOI")  # Replace with your AOI
start_year = 1995
end_year = 2025
time_intervals = 10  # Analyze every 10 years

# 2. Functions for Image Processing and Centerline Extraction
# ==========================================================

def create_binary_image(image: ee.Image) -> ee.Image:
    """
    Generates a binary image from a Landsat image using MNDWI and Otsu's thresholding.

    Args:
        image: The input Landsat image.

    Returns:
        A binary image representing water bodies.
    """
    mndwi = image.normalizedDifference(['B3', 'B6']).rename('MNDWI')  # Green and SWIR2 for Landsat 5/7
    if 'B1' in image.bandNames().getInfo():  # Check for Landsat 8
        mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI')  # Green and SWIR2 for Landsat 8

    # Apply Otsu's thresholding
    threshold = mndwi.reduceRegion(
        reducer=ee.Reducer.autoThreshold(optimize='Otsu'),
        geometry=study_area,
        scale=30  # Adjust scale as needed
    ).get('MNDWI')

    binary_image = mndwi.gt(threshold).rename('water_mask')
    return binary_image.select('water_mask')


def extract_centerline(image: ee.Image) -> ee.Feature:
    """
    Extracts the centerline of a river from a binary image using morphological operations.

    Args:
        image: A binary image representing the river.

    Returns:
        A Feature representing the river centerline.
    """

    # Erode and dilate to clean up the binary image
    eroded = image.morphology('erode', 2)  # Adjust the radius as needed
    dilated = eroded.morphology('dilate', 2)

    # Calculate distance transform
    distance = dilated.distance()

    # Calculate the medial axis (centerline)
    centerline = distance.gt(distance.focal_max(size=5)).selfMask()  # Adjust size as needed

    # Convert to vector
    centerline_vector = centerline.reduceToVectors(
        reducer=ee.Reducer.countEvery(),
        geometry=study_area,
        scale=30,  # Adjust scale as needed
        maxPixels=1e10
    )
    return centerline_vector.simplify(maxError=10) #simplify the line


def calculate_migration_rate(centerline1: ee.Feature, centerline2: ee.Feature, time_interval: int) -> float:
    """
    Calculates the average meander migration rate between two centerlines.  Uses a simplified approach.  For a more robust approach, corresponding points along the centerlines should be established.

    Args:
        centerline1: The earlier centerline.
        centerline2: The later centerline.
        time_interval: The time between the two centerlines in years.

    Returns:
        The average migration rate in meters per year.
    """

    # Get the geometry of the features.
    geom1 = centerline1.geometry()
    geom2 = centerline2.geometry()

    # Ensure both geometries are MultiLineString or LineString
    if not (geom1.type().getInfo() in ['MultiLineString', 'LineString'] and geom2.type().getInfo() in ['MultiLineString', 'LineString']):
        print("Input geometries must be LineString or MultiLineString")
        return 0

    # Get the coordinates of the points in each centerline.
    coords1 = geom1.coordinates().getInfo()
    coords2 = geom2.coordinates().getInfo()

    # Function to flatten the coordinate list
    def flatten_coords(coords):
        flat_list = []
        for sublist in coords:
            if isinstance(sublist[0], list):
                for item in sublist:
                    flat_list.append(item)
            else:
                flat_list.append(sublist)
        return flat_list

    coords1 = flatten_coords(coords1)
    coords2 = flatten_coords(coords2)


    # Calculate the distance between each point in centerline1 and its nearest point in centerline2.
    distances = []
    for point1 in coords1:
        min_distance = float('inf')
        for point2 in coords2:
            dist = math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)
            min_distance = min(min_distance, dist)
        distances.append(min_distance)

    # Calculate the average distance.
    average_distance = sum(distances) / len(distances) if distances else 0

    # Calculate the migration rate.
    migration_rate = average_distance / time_interval if time_interval > 0 else 0
    return migration_rate



def calculate_hausdorff_distance(geometry1: ee.Geometry, geometry2: ee.Geometry, max_distance: float = 1000.0) -> float:
    """
    Calculates the Hausdorff distance between two geometries.

    Args:
        geometry1: The first geometry.
        geometry2: The second geometry.
        max_distance: Maximum distance to consider (optional, default 1000 meters).

    Returns:
        The Hausdorff distance in meters.
    """
    # Use the Hausdorff distance implemented in the Earth Engine library.
    distance = geometry1.distance(geometry2, maxError=100).reduce(ee.Reducer.max()).getInfo()
    return distance



def calculate_rmse(predicted: List[List[float]], observed: List[List[float]]) -> float:
    """
    Calculates the Root Mean Square Error (RMSE) between two lists of coordinates.

    Args:
        predicted: List of predicted coordinates [[x1, y1], [x2, y2], ...].
        observed: List of observed coordinates [[x1, y1], [x2, y2], ...].

    Returns:
        The RMSE value.
    """
    if not predicted or not observed:
        return 0  # Handle empty lists

    n = min(len(predicted), len(observed))  # Ensure both lists have same length
    sum_squared_errors = 0
    for i in range(n):
        sum_squared_errors += (predicted[i][0] - observed[i][0])**2 + (predicted[i][1] - observed[i][1])**2
    mse = sum_squared_errors / n
    rmse = math.sqrt(mse)
    return rmse



def extract_coordinates(geometry: ee.Geometry) -> List[List[float]]:
    """
    Extracts coordinates from an Earth Engine Geometry object.

    Args:
      geometry:  An Earth Engine Geometry object (LineString or MultiLineString)

    Returns:
        A list of lists of coordinates.  For a LineString, this is [[x1, y1], [x2, y2], ...].
        For a MultiLineString, it is [[[x1,y1],[x2,y2]], [[x3,y3],...]]
    """
    coords = geometry.coordinates().getInfo()

    # Flatten the list if it's a MultiLineString
    if geometry.type().getInfo() == 'MultiLineString':
        flat_list = []
        for sublist in coords:
            for item in sublist:
                flat_list.append(item)
        return flat_list
    return coords



# 3. Main Analysis
# =================
def main():
    """
    Main function to perform the meander migration analysis.
    """

    # 3. 1. Create a list of years to analyze
    years = list(range(start_year, end_year + 1, time_intervals))
    print(f"Years to analyze: {years}")

    # 3.2. Load Landsat data and filter for the study period.  Use Landsat 5, 7, and 8
    landsat5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR').filterDate(str(start_year)+'-01-01', str(end_year)+'-12-31').filterBounds(study_area)
    landsat7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR').filterDate(str(start_year)+'-01-01', str(end_year)+'-12-31').filterBounds(study_area)
    landsat8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR').filterDate(str(start_year)+'-01-01', str(end_year)+'-12-31').filterBounds(study_area)

    # Combine the collections
    landsat = ee.ImageCollection(landsat5.merge(landsat7).merge(landsat8))

    # 3.3.  Get centerline for each time interval
    centerlines = []
    for year in years:
        # Create a composite for the given year.  Use a median reducer to reduce noise.
        composite = landsat.filterDate(str(year)+'-01-01', str(year)+'-12-31').median().clip(study_area)
        binary_image = create_binary_image(composite)
        centerline = extract_centerline(binary_image)
        centerlines.append(centerline)


    # 3.4. Calculate migration rates
    migration_rates = []
    for i in range(len(centerlines) - 1):
        rate = calculate_migration_rate(centerlines[i], centerlines[i+1], time_intervals)
        migration_rates.append(rate)
    print("Migration Rates (m/year):", migration_rates)


    # 3.5.  Calculate Performance Metrics (RMSE and Hausdorff Distance)
    # ---------------------------------------------------------------
    rmse_values = []
    hausdorff_values = []

    # Use the first centerline as the "observed" and compare subsequent years to it.
    observed_coords = extract_coordinates(centerlines[0].geometry())

    for i in range(1, len(centerlines)):
        predicted_coords = extract_coordinates(centerlines[i].geometry())
        rmse = calculate_rmse(predicted_coords, observed_coords)
        hausdorff = calculate_hausdorff_distance(centerlines[0].geometry(), centerlines[i].geometry())
        rmse_values.append(rmse)
        hausdorff_values.append(hausdorff)

    print("RMSE Values (m):", rmse_values)
    print("Hausdorff Distances (m):", hausdorff_values)

    # 3.6. Display Results on a Map
    # --------------------------
    m = geemap.Map(center=study_area.centroid().coordinates().getInfo(), zoom=10)
    m.add_layer(study_area, {}, "Study Area")

    # Add each centerline as a separate layer
    for i, year in enumerate(years):
        m.add_layer(centerlines[i], {'color': 'red' if i == 0 else 'blue'}, f"Centerline {year}")

    # Add a layer showing migration rate.  This is a simplified visualization.  A more accurate approach would involve calculating migration vectors.
    for i in range(len(centerlines) - 1):
        # Create a feature collection showing the shift from one year to the next.
        migration_line = ee.Geometry.LineString([
            centerlines[i].geometry().centroid().coordinates(),
            centerlines[i+1].geometry().centroid().coordinates()
        ])
        migration_feature = ee.Feature(migration_line, {'migration_rate': migration_rates[i]})
        m.add_layer(migration_feature, {'color': 'green'}, f"Migration {years[i]}-{years[i+1]}")


    m.add_legend(title="Centerlines", labels=[f"Centerline {year}" for year in years], colors=['red'] + ['blue'] * (len(years)-1))
    m.add_legend(title="Migration", labels=[f"Migration {years[i]}-{years[i+1]}" for i in range(len(years)-1)], colors=['green'])
    m.layer_control()
    m.show()

if __name__ == "__main__":
    main()
