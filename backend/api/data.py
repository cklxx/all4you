"""
Data management API endpoints
Handle file uploads, validation, preview, and processing
"""

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from loguru import logger

from core.config import Settings
from core.database import DataFile, get_db
from core.data_processor import DataProcessor, validate_data_format
from models.schemas import (
    DataFileResponse,
    DataValidationRequest,
    DataValidationResponse,
    DataPreviewRequest,
    DataPreviewResponse,
    ApiResponse,
)

router = APIRouter()
settings = Settings()


@router.post("/upload", response_model=DataFileResponse)
async def upload_data_file(
    file: UploadFile = File(...),
    format_type: str = "alpaca",
    db: Session = Depends(get_db)
):
    """
    Upload and process a data file

    Supported formats:
    - JSON: List of dictionaries
    - JSONL: One JSON object per line
    - CSV: With headers
    - TXT: One sample per line

    Supported data structures:
    - alpaca: instruction, input, output
    - sharegpt: conversations with role and content
    - raw: plain text
    """
    try:
        logger.info(f"Uploading file: {file.filename}")

        # Validate file extension
        file_ext = Path(file.filename).suffix.lstrip('.').lower()
        if file_ext not in DataProcessor.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported: {DataProcessor.SUPPORTED_FORMATS}"
            )

        # Generate file ID
        file_id = str(uuid.uuid4())

        # Save file
        file_path = settings.DATA_DIR / file_id / file.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved to {file_path}")

        # Load and validate data
        data = DataProcessor.load_file(str(file_path), file_ext, format_type)
        validation_report = validate_data_format(data, format_type)

        if not validation_report["valid"]:
            logger.warning(f"Data validation issues: {validation_report['issues']}")

        # Create database record
        db_file = DataFile(
            id=file_id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_ext,
            format_type=format_type,
            total_samples=len(data),
            file_size=len(content),
            metadata={
                "validation": validation_report,
                "original_filename": file.filename
            }
        )

        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        logger.info(f"Data file registered: {file_id} with {len(data)} samples")

        return DataFileResponse(
            id=db_file.id,
            filename=db_file.filename,
            file_type=db_file.file_type,
            format_type=db_file.format_type,
            total_samples=db_file.total_samples,
            file_size=db_file.file_size,
            created_at=db_file.created_at
        )

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_data_files(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """List all uploaded data files"""
    try:
        files = db.query(DataFile).offset(skip).limit(limit).all()
        total = db.query(DataFile).count()

        file_list = [
            DataFileResponse(
                id=f.id,
                filename=f.filename,
                file_type=f.file_type,
                format_type=f.format_type,
                total_samples=f.total_samples,
                file_size=f.file_size,
                created_at=f.created_at
            )
            for f in files
        ]

        return ApiResponse(
            success=True,
            message="Data files listed successfully",
            data={
                "total": total,
                "skip": skip,
                "limit": limit,
                "files": [f.model_dump() for f in file_list]
            }
        )
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}")
async def get_data_file(
    file_id: str,
    db: Session = Depends(get_db)
) -> DataFileResponse:
    """Get data file information"""
    db_file = db.query(DataFile).filter(DataFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    return DataFileResponse(
        id=db_file.id,
        filename=db_file.filename,
        file_type=db_file.file_type,
        format_type=db_file.format_type,
        total_samples=db_file.total_samples,
        file_size=db_file.file_size,
        created_at=db_file.created_at
    )


@router.post("/validate")
async def validate_data(
    request: DataValidationRequest,
    db: Session = Depends(get_db)
) -> DataValidationResponse:
    """Validate data file format and content"""
    try:
        # Get file from database
        db_file = db.query(DataFile).filter(DataFile.id == request.file_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Load and validate data
        data = DataProcessor.load_file(
            db_file.file_path,
            db_file.file_type,
            request.format_type
        )

        validation_report = validate_data_format(data, request.format_type)

        return DataValidationResponse(
            valid=validation_report["valid"],
            total_samples=validation_report["total_samples"],
            issues=validation_report["issues"],
            statistics=validation_report["statistics"]
        )

    except Exception as e:
        logger.error(f"Error validating data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
async def preview_data(
    request: DataPreviewRequest,
    db: Session = Depends(get_db)
) -> DataPreviewResponse:
    """Preview data file content"""
    try:
        # Get file from database
        db_file = db.query(DataFile).filter(DataFile.id == request.file_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Load data
        data = DataProcessor.load_file(
            db_file.file_path,
            db_file.file_type,
            db_file.format_type
        )

        # Format data
        formatted_data = DataProcessor.format_data(data, db_file.format_type)

        # Get preview
        preview_data = formatted_data[:request.limit]

        return DataPreviewResponse(
            file_id=request.file_id,
            total_samples=len(formatted_data),
            preview_count=len(preview_data),
            format_type=db_file.format_type,
            samples=preview_data
        )

    except Exception as e:
        logger.error(f"Error previewing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_data_file(
    file_id: str,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """Delete data file"""
    try:
        db_file = db.query(DataFile).filter(DataFile.id == file_id).first()
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete file from disk
        file_dir = Path(db_file.file_path).parent
        import shutil
        if file_dir.exists():
            shutil.rmtree(file_dir)

        # Delete from database
        db.delete(db_file)
        db.commit()

        logger.info(f"Data file deleted: {file_id}")

        return ApiResponse(
            success=True,
            message=f"Data file {file_id} deleted successfully"
        )

    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
