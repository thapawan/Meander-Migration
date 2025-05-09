// 1. Define Study Area and Time Period
var study_area = ee.FeatureCollection("USGS/WBD/2017/h10u").filter(ee.Filter.eq('name', 'Yazoo River'));

var start_year = 1995;
var end_year = 2025;
var time_interval = 10; // Analyze every 10 years

// 2. Functions for Image Processing and Centerline Extraction
// ==========================================================

/**
 * Generates a binary image from a Landsat image using MNDWI and Otsu's thresholding.
 * @param {ee.Image} image The input Landsat image.
 * @returns {ee.Image} A binary image representing water bodies.
 */
function createBinaryImage(image) {
    var mndwi = image.normalizedDifference(['B3', 'B6']).rename('MNDWI');  // Green and SWIR2 for Landsat 5/7
    if (image.bandNames().getInfo().includes('B1')) {  // Check for Landsat 8
        mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI');  // Green and SWIR2 for Landsat 8
    }

    // Apply Otsu's thresholding
    var threshold = mndwi.reduceRegion({
        reducer: ee.Reducer.autoThreshold({optimize: 'Otsu'}),
        geometry: study_area,
        scale: 30  // Adjust scale as needed
    }).get('MNDWI');

    var binaryImage = mndwi.gt(threshold).rename('water_mask');
    return binaryImage.select('water_mask');
}

/**
 * Extracts the centerline of a river from a binary image using morphological operations.
 * @param {ee.Image} image A binary image representing the river.
 * @returns {ee.Feature} A Feature representing the river centerline.
 */
function extractCenterline(image) {
    // Erode and dilate to clean up the binary image
    var eroded = image.morphology('erode', 2);  // Adjust the radius as needed
    var dilated = eroded.morphology('dilate', 2);

    // Calculate distance transform
    var distance = dilated.distance();

    // Calculate the medial axis (centerline)
    var centerline = distance.gt(distance.focal_max({size: 5})).selfMask();  // Adjust size as needed.  Use focal_max
   
     // Convert to vector
    var centerline_vector = centerline.reduceToVectors({
        reducer: ee.Reducer.countEvery(),
        geometry: study_area,
        scale: 30,  // Adjust scale as needed
        maxPixels: 1e10
    });
    return centerline_vector.simplify({maxError: 10}); //simplify the line
}

/**
 * Calculates the average meander migration rate between two centerlines.  Uses a simplified approach.
 * @param {ee.Feature} centerline1 The earlier centerline.
 * @param {ee.Feature} centerline2 The later centerline.
 * @param {number} timeInterval The time between the two centerlines in years.
 * @returns {number} The average migration rate in meters per year.
 */
function calculateMigrationRate(centerline1, centerline2, timeInterval) {
    // Get the geometry of the features.
    var geom1 = centerline1.geometry();
    var geom2 = centerline2.geometry();

     // Ensure both geometries are MultiLineString or LineString
    if (!['MultiLineString', 'LineString'].includes(geom1.type().getInfo()) || !['MultiLineString', 'LineString'].includes(geom2.type().getInfo())) {
        console.log("Input geometries must be LineString or MultiLineString");
        return 0;
    }

    // Get the coordinates of the points in each centerline.
    var coords1 = geom1.coordinates();
    var coords2 = geom2.coordinates();

    // Function to flatten the coordinate list
    function flattenCoords(coords) {
        var flatList = [];
        function flatten(arr) {
            for (var i = 0; i < arr.length; i++) {
                if (Array.isArray(arr[i])) {
                    flatten(arr[i]);
                } else {
                    flatList.push(arr[i]);
                }
            }
        }
        flatten(coords);
        return flatList;
    }

    coords1 = flattenCoords(coords1);
    coords2 = flattenCoords(coords2);


    // Calculate the distance between each point in centerline1 and its nearest point in centerline2.
    var distances = [];
    for (var i = 0; i < coords1.length; i++) {
        var point1 = coords1[i];
        var minDistance = Infinity;
        for (var j = 0; j < coords2.length; j++) {
            var point2 = coords2[j];
            var dist = Math.sqrt(Math.pow(point2[0] - point1[0], 2) + Math.pow(point2[1] - point1[1], 2));
            minDistance = Math.min(minDistance, dist);
        }
        distances.push(minDistance);
    }

    // Calculate the average distance.
    var averageDistance = distances.reduce(function(a, b) { return a + b; }, 0) / distances.length;

    // Calculate the migration rate.
    var migrationRate = averageDistance / timeInterval;
    return migrationRate;
}



// 3. Main Analysis
// =================
function main() {
    // 3. 1. Create a list of years to analyze
    var years = [];
    for (var year = start_year; year <= end_year; year += time_interval) {
        years.push(year);
    }
    console.log('Years to analyze:', years);

    // 3.2. Load Landsat data and filter for the study period.  Use Landsat 5, 7, and 8
    var landsat5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
        .filterDate(years[0] + '-01-01', years[years.length-1] + '-12-31')
        .filterBounds(study_area);
    var landsat7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR')
        .filterDate(years[0] + '-01-01', years[years.length-1] + '-12-31')
        .filterBounds(study_area);
    var landsat8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')
        .filterDate(years[0] + '-01-01', years[years.length-1] + '-12-31')
        .filterBounds(study_area);

    // Combine the collections
    var landsat = ee.ImageCollection(landsat5.merge(landsat7).merge(landsat8));


    // 3.3.  Get centerline for each time interval and Export
    var centerlines = [];
    for (var i = 0; i < years.length; i++) {
        var year = years[i];
        // Create a composite for the given year.  Use a median reducer to reduce noise.
        var composite = landsat.filterDate(year + '-01-01', year + '-12-31').median().clip(study_area);
        var binaryImage = createBinaryImage(composite);
        var centerline = extractCenterline(binaryImage);
        centerlines.push(centerline);

        // Export the binary image as a GeoTIFF.
        Export.image.toDrive({
            image: binaryImage,
            description: 'binary_image_' + year,
            folder: 'meander_migration_results', // You can change the folder name
            scale: 30,  // Adjust scale as needed
            region: study_area.geometry(),
            fileFormat: 'GeoTIFF'
        });

        // Export the centerline as a GeoJSON.
        Export.table.toDrive({
            collection: ee.FeatureCollection(centerline),
            description: 'centerline_' + year,
            folder: 'meander_migration_results', // You can change the folder name
            fileFormat: 'GeoJSON'  // Or 'KML', 'CSV', etc.
        });
    }



    // 3.4. Calculate migration rates
    var migrationRates = [];
    for (var i = 0; i < centerlines.length - 1; i++) {
        var rate = calculateMigrationRate(centerlines[i], centerlines[i + 1], time_interval);
        migrationRates.push(rate);
        console.log('Migration Rate from ' + years[i] + ' to ' + years[i+1] + ': ' + rate.toFixed(2) + ' m/year');
    }

    // 3.5. Export Migration Rates as a CSV
     var migrationRateData = years.slice(0, -1).map(function(year, index) {
        return {
            Year1: year,
            Year2: years[index + 1],
            MigrationRate: migrationRates[index]
        };
    });
    var migrationRateFC = ee.FeatureCollection(migrationRateData.map(function(item) {
        return ee.Feature(null, item);
    }));

      Export.table.toDrive({
        collection: migrationRateFC,
        description: 'migration_rates',
        folder: 'meander_migration_results',
        fileFormat: 'CSV'
    });


    // 3.6. Display Results on a Map
    // --------------------------
    var map = geemap.Map( {center: study_area.centroid().coordinates().getInfo(), zoom: 10});
    map.addLayer(study_area, {}, 'Study Area');

    // Add each centerline as a separate layer
    for (var i = 0; i < years.length; i++) {
        map.addLayer(centerlines[i], {color: i === 0 ? 'red' : 'blue'}, 'Centerline ' + years[i]);
    }

     // Add a layer showing migration rate (simplified visualization)
    for (var i = 0; i < centerlines.length - 1; i++) {
        var migrationLine = ee.Geometry.LineString([
            centerlines[i].geometry().centroid().coordinates(),
            centerlines[i + 1].geometry().centroid().coordinates()
        ]);
        var migrationFeature = ee.Feature(migrationLine, { 'migration_rate': migrationRates[i] });
        map.addLayer(migrationFeature, { color: 'green' }, 'Migration ' + years[i] + '-' + years[i+1]);
    }

    map.add_legend({
        title: 'Centerlines',
        labels: years.map(function(year) { return 'Centerline ' + year; }),
        colors: ['red'].concat(Array(years.length - 1).fill('blue'))
    });

    map.add_legend({
        title: 'Migration',
        labels: migrationRates.map(function(_, i) { return 'Migration ' + years[i] + '-' + years[i+1]; }),
        colors: ['green']
    });
    map.layer_control();
    map.show();
}

// Run the analysis
main();
