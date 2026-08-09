// -----------------------------
// AOI
// -----------------------------
var bhopal = ee.Geometry.Rectangle([77.25, 23.10, 77.55, 23.40]);
Map.centerObject(bhopal, 11);

// -----------------------------
// DATE RANGE
// -----------------------------
var pre_start = '2022-06-01';
var pre_end   = '2022-06-15';

var post_start = '2022-07-20';
var post_end   = '2022-08-05';

// -----------------------------
// SENTINEL-1 DATA
// -----------------------------
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(bhopal)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
  .select('VV');

// -----------------------------
// PRE & POST IMAGES (CLIPPED)
// -----------------------------
var pre = s1.filterDate(pre_start, pre_end)
            .median()
            .clip(bhopal);

var post = s1.filterDate(post_start, post_end)
             .median()
             .clip(bhopal);

// -----------------------------
// SPECKLE FILTER
// -----------------------------
var smooth = function(img) {
  return img.focal_mean(50, 'circle', 'meters').clip(bhopal);
};

pre = smooth(pre);
post = smooth(post);

// -----------------------------
// WATER DETECTION
// -----------------------------
var water_pre = pre.lt(-14);
var water_post = post.lt(-14);

// -----------------------------
// FLOOD + STAGNANT DETECTION
// -----------------------------
var ratio = post.divide(pre);
var flood_pixels = ratio.lt(0.75);

var flood = water_post.and(water_pre.not()).or(flood_pixels);

var diff = post.subtract(pre);
var stagnant = water_post.and(water_pre)
                .and(diff.lt(-1));

// -----------------------------
// REMOVE PERMANENT WATER
// -----------------------------
var permanentWater = ee.Image('JRC/GSW1_3/GlobalSurfaceWater')
                        .select('seasonality')
                        .gte(10);

flood = flood.updateMask(permanentWater.not());
stagnant = stagnant.updateMask(permanentWater.not());

// -----------------------------
// BUILT-UP (FIXED DATASET)
// -----------------------------
var builtUp = ee.ImageCollection('ESA/WorldCover/v200')
                .first()
                .select('Map')
                .eq(50)
                .clip(bhopal);

// -----------------------------
// URBAN FLOOD
// -----------------------------
var urbanFlood = flood.updateMask(builtUp);
var urbanStagnant = stagnant.updateMask(builtUp);

// -----------------------------
// VISUALIZATION
// -----------------------------
Map.addLayer(pre, {min: -25, max: 0}, 'Pre SAR');
Map.addLayer(post, {min: -25, max: 0}, 'Post SAR');

Map.addLayer(flood, {palette: ['blue']}, 'Flood');
Map.addLayer(stagnant, {palette: ['yellow']}, 'Stagnant');

Map.addLayer(urbanFlood, {palette: ['red']}, 'Urban Flood');
Map.addLayer(urbanStagnant, {palette: ['orange']}, 'Urban Stagnant');

// -----------------------------
// AREA CALCULATION
// -----------------------------
var areaImage = ee.Image.pixelArea().rename('area');

var pre_area = water_pre.multiply(areaImage).rename('area');
var post_area = water_post.multiply(areaImage).rename('area');
var flood_area = flood.multiply(areaImage).rename('area');

// Safe extractor
var getSafe = function(dict) {
  dict = ee.Dictionary(dict);
  return ee.Number(dict.get('area', 0));
};

// Reduce
var pre_stats = pre_area.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: bhopal,
  scale: 30,
  maxPixels: 1e10
});

var post_stats = post_area.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: bhopal,
  scale: 30,
  maxPixels: 1e10
});

var flood_stats = flood_area.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: bhopal,
  scale: 30,
  maxPixels: 1e10
});

// Convert to sq km
var pre_km = getSafe(pre_stats).divide(1e6);
var post_km = getSafe(post_stats).divide(1e6);
var flood_km = getSafe(flood_stats).divide(1e6);

// Absolute increase
var increase = post_km.subtract(pre_km).abs();

// -----------------------------
// PRINT RESULTS
// -----------------------------
print('Pre-flood water area (sq km):', post_km);
print('Post-flood water area (sq km):', pre_km);
print('Absolute flood increase (sq km):', increase);

// -----------------------------
// GRAPH
// -----------------------------
var chart = ui.Chart.array.values({
  array: ee.Array([post_km, pre_km]),
  axis: 0,
  xLabels: ['Pre-Flood', 'Post-Flood']
})
.setChartType('ColumnChart')
.setOptions({
  title: 'Flood Area Comparison - Bhopal',
  hAxis: {title: 'Time'},
  vAxis: {title: 'Area (sq km)'},
  colors: ['blue']
});

print(chart);
