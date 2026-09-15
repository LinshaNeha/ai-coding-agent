from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.services.file_tools import read_file
from app.services.fix_loop import fix_and_verify

router = APIRouter()


class FixRequest(BaseModel):
    file_path: str
    test_path: str = "tests"


@router.post("/agent/fix", dependencies=[Depends(verify_api_key)])
def trigger_fix(request: FixRequest):
    original_code = read_file(request.file_path)

    result = fix_and_verify(request.file_path, request.test_path)

    final_code = read_file(request.file_path)

    return {
        "success": result["success"],
        "attempts": result["attempts"],
        "original_code": original_code,
        "final_code": final_code,
        "changed": original_code != final_code,
        "final_output": result["final_output"],
    }