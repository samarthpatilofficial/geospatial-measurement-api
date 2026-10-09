# Geospatial File Measurement API

A REST API built with FastAPI and GeoPandas to upload geospatial files, extract feature information, and calculate geometric measurements.

## Features

- Accepts KML files and ZIP archives containing a Shapefile.
- Extracts feature IDs, geometry types, geometries, CRS information, and properties.
- Calculates line lengths in metres.
- Calculates polygon areas in square metres.
- Returns `null` measurements for point geometries.
- Transforms geographic coordinates into a suitable projected CRS before measurement.
- Provides endpoints to upload files, retrieve file metadata, and retrieve measurements.

## Technology Stack

- Python
- FastAPI
- Uvicorn
- GeoPandas
- Pyogrio
- Shapely
- PyProj

## Project Structure

```text
geospatial-measurement-api/
├── main.py
├── requirements.txt
├── README.md
├── create_sample_shapefile.py
├── sample.kml
├── sample_shapefile/
└── services/
    └── geo_processor.py
```

The sample files and sample-generation script are for local testing.

## Prerequisites

- Python 3.13 or a compatible Python version
- pip

## Installation

Clone the repository and navigate to the project directory:

```bash
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd geospatial-measurement-api
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the API

Start the development server:

```bash
uvicorn main:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

Health check:

http://127.0.0.1:8000/health

## API Endpoints

### 1. Upload a file

`POST /api/files/`

Accepts a KML file or a ZIP archive containing exactly one Shapefile (`.shp`) and its associated files.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -F "file=@sample.kml"
```

A successful upload returns HTTP `201 Created`, a unique file ID, the filename, feature count, source CRS, measurement CRS, and processing status.

### 2. Retrieve file information

`GET /api/files/{file_id}/`

Returns metadata for a previously uploaded file.

### 3. Retrieve measurements

`GET /api/files/{file_id}/measurements/`

Returns feature details and geometric measurements.

## Measurement Logic

- **Point and MultiPoint:** No measurement is calculated.
- **LineString and MultiLineString:** Length is returned in metres.
- **Polygon and MultiPolygon:** Area is returned in square metres.

Measurements are calculated using projected geometries rather than directly using longitude and latitude coordinates.

## Coordinate Reference System (CRS) Handling

The API reads the source CRS from the input dataset. If a KML file has no CRS metadata, the implementation assumes EPSG:4326, consistent with the usual KML coordinate convention.

For measurement, the implementation transforms features to EPSG:4326 to estimate a suitable UTM CRS, then projects the geometries to that CRS before calculating lengths and areas.

For ZIP-based Shapefiles, a valid CRS should be provided, typically through the `.prj` file.

## Processing Flow

1. Receive and validate the uploaded file.
2. Save it temporarily for processing.
3. Read the KML or extract and read the Shapefile from the ZIP archive.
4. Validate the dataset and CRS.
5. Transform geometries into a suitable projected CRS.
6. Extract feature details and calculate applicable measurements.
7. Return the processed data through the API.
8. Remove the temporary uploaded file.

## Architecture

- `main.py`: Defines API routes, upload validation, temporary-file handling, and in-memory storage.
- `services/geo_processor.py`: Reads geospatial datasets, processes geometries, handles CRS transformations, and calculates measurements.
- `requirements.txt`: Lists the project's direct Python dependencies.

## Current Limitations

- Uploaded file metadata and results are stored in memory and are lost when the server restarts.
- The ZIP archive must contain exactly one `.shp` file.
- Shapefiles without CRS information are rejected.
- The API is currently a local development prototype and is not configured for production deployment.

## Future Improvements

- Persistent database storage.
- Automated unit and integration tests.
- More comprehensive validation for invalid geometries and malformed files.
- Configurable upload and processing limits.
- Production deployment with authentication, monitoring, and persistent storage.

## License

Add a license if you intend to distribute this project as open source.
