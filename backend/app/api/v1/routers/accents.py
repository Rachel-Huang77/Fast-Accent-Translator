# app/api/v1/routers/accents.py
from fastapi import APIRouter

router = APIRouter(prefix="/accents", tags=["accents"])

@router.get("")
async def get_accents():
    """
    Get list of available accent options for TTS.
    
    Returns a list of supported accents that users can select for
    text-to-speech synthesis. Currently only supports American English.
    
    Returns:
        dict: Response containing:
            - success: bool (always True)
            - data: dict with "accents" list containing:
                - code: str (accent code, e.g., "us")
                - label: str (human-readable accent name)
                - available: bool (whether accent is currently available)
    
    Example response:
        {
            "success": True,
            "data": {
                "accents": [
                    {"code": "us", "label": "American English (US)", "available": True}
                ]
            }
        }
    """
    return {"success": True, "data": {"accents": [
        {"code": "us", "label": "American English (US)", "available": True}
    ]}}
