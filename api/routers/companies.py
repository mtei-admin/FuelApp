"""Company master data routes."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.access import MasterDataUser
from api.core.dependencies import get_db_path
from api.schemas.auth import MessageResponse
from api.schemas.company import CompanyCreateRequest, CompanyResponse, CompanyUpdateRequest
from api.services import company_service

router = APIRouter(prefix="/companies", tags=["companies"])

def _handle_service_error(error: Exception) -> HTTPException:
    """Convert service RuntimeError to HTTP 400."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("", response_model=List[CompanyResponse])
def list_companies_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> List[CompanyResponse]:
    """List all companies (active and inactive)."""
    try:
        rows = company_service.get_all_companies(db_path)
        return [
            CompanyResponse(
                id=row["id"],
                code=row["code"],
                name=row["name"],
                is_active=bool(row.get("is_active")),
                created_at=row.get("created_at"),
            )
            for row in rows
        ]
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.get("/active-codes")
def active_company_codes_route(
    db_path: Annotated[str, Depends(get_db_path)],
    _user: MasterDataUser,
) -> dict:
    """Return active company codes for assignment dropdowns."""
    try:
        return {"companies": company_service.get_active_company_codes(db_path)}
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company_route(
    payload: CompanyCreateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> CompanyResponse:
    """Create a new company."""
    try:
        company_id = company_service.add_company(
            db_path, payload.code, payload.name, actor=user
        )
        row = next(
            (item for item in company_service.get_all_companies(db_path) if item["id"] == company_id),
            None,
        )
        if not row:
            raise HTTPException(status_code=500, detail="Company created but not found")
        return CompanyResponse(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            is_active=bool(row.get("is_active")),
            created_at=row.get("created_at"),
        )
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company_route(
    company_id: int,
    payload: CompanyUpdateRequest,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> CompanyResponse:
    """Update company display name."""
    try:
        company_service.save_company(db_path, company_id, payload.name, actor=user)
        row = next(
            (item for item in company_service.get_all_companies(db_path) if item["id"] == company_id),
            None,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")
        return CompanyResponse(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            is_active=bool(row.get("is_active")),
            created_at=row.get("created_at"),
        )
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{company_id}/deactivate", response_model=MessageResponse)
def deactivate_company_route(
    company_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> MessageResponse:
    """Deactivate a company (existing vehicle/user links preserved)."""
    try:
        company_service.deactivate_company(db_path, company_id, actor=user)
        return MessageResponse(message="Company deactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error


@router.post("/{company_id}/reactivate", response_model=MessageResponse)
def reactivate_company_route(
    company_id: int,
    db_path: Annotated[str, Depends(get_db_path)],
    user: MasterDataUser,
) -> MessageResponse:
    """Reactivate a deactivated company."""
    try:
        company_service.restore_company(db_path, company_id, actor=user)
        return MessageResponse(message="Company reactivated")
    except RuntimeError as error:
        raise _handle_service_error(error) from error
