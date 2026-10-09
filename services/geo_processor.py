
from pathlib import Path
import json
import math
import tempfile
import zipfile

import geopandas as gpd
from shapely.geometry import mapping


SUPPORTED_EXTENSIONS = {".kml", ".zip"}
AREA_TYPES = {"Polygon", "MultiPolygon"}
LENGTH_TYPES = {"LineString", "MultiLineString"}



def _json_safe(value):
    """Convert property values into JSON-compatible Python values."""
    if value is None:
        return None

    # Convert NumPy scalar values to regular Python values.
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    # Handle missing values such as pandas NaT and NaN.
    if value is None:
        return None

    if str(value) in ("NaT", "nan", "NaN", "<NA>"):
        return None

    if isinstance(value, float) and not math.isfinite(value):
        return None

    # Convert date/time values to ISO-formatted strings.
    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)

def _read_dataset(path: Path) -> gpd.GeoDataFrame:
    """Read a KML file or a ZIP containing one Shapefile."""
    if path.suffix.lower() == ".kml":
        return gpd.read_file(path)

    if not zipfile.is_zipfile(path):
        raise ValueError("The uploaded ZIP file is invalid.")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir).resolve()

        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()

            if len(members) > 1000:
                raise ValueError("ZIP contains too many files.")

            total_size = sum(item.file_size for item in members)
            if total_size > 100 * 1024 * 1024:
                raise ValueError("Uncompressed ZIP exceeds 100 MB.")

            for item in members:
                target = (root / item.filename).resolve()

                if not target.is_relative_to(root):
                    raise ValueError("Unsafe path in ZIP archive.")

            shp_members = [
                item for item in members
                if not item.is_dir()
                and Path(item.filename).suffix.lower() == ".shp"
            ]

            if len(shp_members) != 1:
                raise ValueError(
                    "ZIP must contain exactly one .shp file."
                )

            archive.extractall(root)

        shp_path = root / shp_members[0].filename

        # Read while the temporary extraction directory still exists.
        return gpd.read_file(shp_path)


def process_geospatial_file(file_path: str) -> dict:
    """Extract features and calculate area/length in metres."""
    path = Path(file_path)

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .kml and .zip files are supported.")

    gdf = _read_dataset(path)

    if gdf.empty:
        raise ValueError("The uploaded file contains no features.")

    if gdf.crs is None:
        if path.suffix.lower() == ".kml":
            # KML coordinates conventionally use WGS 84.
            gdf = gdf.set_crs("EPSG:4326")
        else:
            raise ValueError(
                "Shapefile CRS is missing. Include a valid .prj file."
            )

    source_crs = gdf.crs.to_string()

    # Choose a local UTM CRS using geographic coordinates.
    geographic = gdf.to_crs("EPSG:4326")
    measurement_crs = geographic.estimate_utm_crs()

    if measurement_crs is None:
        raise ValueError(
            "Could not determine a suitable projected CRS."
        )

    measured = gdf.to_crs(measurement_crs)

    features = []

    for index, (original_row, measured_row) in enumerate(
        zip(gdf.iterrows(), measured.iterrows())
    ):
        _, source_feature = original_row
        _, measured_feature = measured_row

        geometry = source_feature.geometry
        projected_geometry = measured_feature.geometry

        measurement = None

        if geometry is not None and not geometry.is_empty:
            if projected_geometry is None or projected_geometry.is_empty:
                pass
            elif not projected_geometry.is_valid:
                measurement = {
                    "status": "unavailable",
                    "reason": "Geometry is invalid.",
                }
            elif geometry.geom_type in AREA_TYPES:
                measurement = {
                    "type": "area",
                    "value": float(projected_geometry.area),
                    "unit": "square_metres",
                }
            elif geometry.geom_type in LENGTH_TYPES:
                measurement = {
                    "type": "length",
                    "value": float(projected_geometry.length),
                    "unit": "metres",
                }

        properties = source_feature.drop(
            labels=[gdf.geometry.name]
        ).to_dict()

        features.append({
            "feature_id": str(index),
            "geometry_type": (
                geometry.geom_type if geometry is not None else None
            ),
            "geometry": (
                mapping(geometry) if geometry is not None else None
            ),
            "crs": source_crs,
            "properties": _json_safe(properties),
            "measurement": measurement,
        })

    # Verify the result can be serialized as JSON.
    json.dumps(features, allow_nan=False)

    return {
        "filename": path.name,
        "crs": source_crs,
        "measurement_crs": measurement_crs.to_string(),
        "feature_count": len(features),
        "features": features,
    }
