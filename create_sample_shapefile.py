
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point

output_dir = Path("sample_shapefile")
output_dir.mkdir(exist_ok=True)

features = [
    {"name": "Point A", "geometry": Point(73.8567, 18.5204)},
    {"name": "Point B", "geometry": Point(73.8667, 18.5204)},
    {"name": "Point C", "geometry": Point(73.8567, 18.5304)},
]

gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
gdf.to_file(output_dir / "sample.shp", index=False)

print("Sample Shapefile created successfully!")
print(f"Location: {output_dir.resolve()}")
print("Files:")
for file_path in sorted(output_dir.iterdir()):
    print(f" - {file_path.name}")
