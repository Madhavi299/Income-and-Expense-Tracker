from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import User
from backend.app.ocr import extract_text, guess_fields

router = APIRouter(prefix="/bills", tags=["Bill OCR"])
MAX_FILE_SIZE = 10 * 1024 * 1024

@router.post("/extract")
async def extract_bill(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    del user, db  # Auth is required; extraction itself does not write to the database.
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Maximum bill upload size is 10 MB")
    try:
        text = extract_text(file.filename or "bill", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read this bill. Check OCR setup. Details: {exc}")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable text found. Try a clearer image or a text-based PDF.")
    return {"extracted_text": text, "fields": guess_fields(text)}
