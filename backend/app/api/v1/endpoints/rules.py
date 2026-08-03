from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from services.rules_database import rules_db

router = APIRouter()


@router.get("/cpt", response_model=List[Dict[str, Any]])
def list_cpt_rules():
    """Lists all registered CPT codes and procedure rules."""
    return rules_db.list_cpt_codes()


@router.get("/cpt/{code}", response_model=Dict[str, Any])
def get_cpt_rule(code: str):
    """Retrieves standard allowed amounts and pre-authorization requirements for a specific CPT procedure code."""
    cpt_info = rules_db.get_cpt_code(code)
    if not cpt_info:
        raise HTTPException(status_code=404, detail=f"CPT code '{code}' not found in rules database.")
    return cpt_info


@router.get("/icd", response_model=List[Dict[str, Any]])
def list_icd_rules():
    """Lists all registered ICD-10 diagnosis codes."""
    return rules_db.list_icd_codes()


@router.get("/icd/{code}", response_model=Dict[str, Any])
def get_icd_rule(code: str):
    """Retrieves description and validity criteria for an ICD-10 diagnosis code."""
    icd_info = rules_db.get_icd_code(code)
    if not icd_info:
        raise HTTPException(status_code=404, detail=f"ICD-10 code '{code}' not found in rules database.")
    return icd_info


@router.get("/preauth/{cpt_code}", response_model=Dict[str, Any])
def get_preauth_rule(cpt_code: str):
    """Retrieves clinical pre-authorization requirements, required documents, and turnaround criteria for a CPT procedure code."""
    preauth_info = rules_db.get_preauth_rule(cpt_code)
    if not preauth_info:
        # Check basic CPT requirement
        is_req = rules_db.is_preauth_required(cpt_code)
        return {
            "cpt_code": cpt_code,
            "requires_preauth": is_req,
            "clinical_criteria": [],
            "required_documents": [],
            "turnaround_days": 0,
            "auto_approval_eligible": not is_req
        }
    return preauth_info
