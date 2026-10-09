import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from services.geo_processor import process_geospatial_file


app = FastAPI(
    title="Geospatial File Measurement API",
    description="Upload KML or zipped Shapefiles and retrieve measurements.",
    version="1.0.0",
)

# Temporary in-memory storage for this initial implementation.
processed_files = {}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".kml", ".zip"}


@app.get("/")
def home():
    return {
        "message": "Geospatial File Measurement API is running",
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "geospatial-measurement-api",
    }


@app.post("/api/files/", status_code=201)
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a KML file or zipped Shapefile."""
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .kml and .zip files are supported.",
        )

    content = await file.read(MAX_UPLOAD_SIZE + 1)

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 50 MB upload limit.",
        )

    temp_path = None

    try:
        with NamedTemporaryFile(
            suffix=extension, delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        result = process_geospatial_file(str(temp_path))
        file_id = str(uuid4())

        processed_files[file_id] = {
            "id": file_id,
            "filename": filename,
            "feature_count": result["feature_count"],
            "crs": result["crs"],
            "measurement_crs": result["measurement_crs"],
            "status": "COMPLETED",
            "features": result["features"],
        }

        return {
            "id": file_id,
            "filename": filename,
            "feature_count": result["feature_count"],
            "crs": result["crs"],
            "measurement_crs": result["measurement_crs"],
            "status": "COMPLETED",
        }

    
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        logger.exception("Geospatial file processing failed")
        raise HTTPException(
            status_code=422,
            detail="Could not process geospatial file. Check the VS Code terminal for details.",
        ) from exc

    finally:
        await file.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.get("/api/files/{file_id}/")
def get_file_info(file_id: str):
    """Return information about a previously uploaded file."""
    stored = processed_files.get(file_id)

    if stored is None:
        raise HTTPException(status_code=404, detail="File not found.")

    return {
        "id": stored["id"],
        "filename": stored["filename"],
        "feature_count": stored["feature_count"],
        "crs": stored["crs"],
        "measurement_crs": stored["measurement_crs"],
        "status": stored["status"],
    }


@app.get("/api/files/{file_id}/measurements/")
def get_measurements(file_id: str):
    """Return measurements and feature details for an uploaded file."""
    stored = processed_files.get(file_id)

    if stored is None:
        raise HTTPException(status_code=404, detail="File not found.")

    return {
        "file_id": stored["id"],
        "filename": stored["filename"],
        "feature_count": stored["feature_count"],
        "crs": stored["crs"],
        "measurement_crs": stored["measurement_crs"],
        "measurements": [
            {
                "feature_id": feature["feature_id"],
                "geometry_type": feature["geometry_type"],
                "measurement": feature["measurement"],
            }
            for feature in stored["features"]
        ],
        "features": stored["features"],
    }

