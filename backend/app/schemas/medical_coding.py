from typing import List, Optional
from pydantic import BaseModel, Field


class MedicalCode(BaseModel):
    """Representing any generic medical code (CPT or ICD-10)."""
    code: str = Field(..., description="The standard CPT or ICD-10 code string")
    code_type: str = Field(..., description="The type of medical code ('CPT' or 'ICD-10')")
    description: str = Field(..., description="Clinical description of the code")
    confidence: float = Field(..., description="AI confidence score for this inference")


class Diagnosis(BaseModel):
    """Structured ICD-10 diagnosis code details."""
    code: str = Field(..., description="The ICD-10 classification code (e.g. M23.231)")
    description: str = Field(..., description="Inferred diagnosis description")
    confidence: float = Field(..., description="Inference confidence score")


class Procedure(BaseModel):
    """Structured CPT procedure code details."""
    code: str = Field(..., description="The CPT-4 procedure code (e.g. 29881)")
    description: str = Field(..., description="Inferred procedure description")
    confidence: float = Field(..., description="Inference confidence score")


class CodingResult(BaseModel):
    """Aggregated output containing all procedures and diagnoses identified in a document."""
    job_id: Optional[str] = Field(None, description="Optional job ID linking back to the intake analysis run")
    diagnoses: List[Diagnosis] = Field(default_factory=list, description="Identified ICD-10 diagnosis codes")
    procedures: List[Procedure] = Field(default_factory=list, description="Identified CPT procedure codes")
    raw_response: Optional[str] = Field(None, description="Raw JSON text response from the Gemini API")

    @property
    def all_codes(self) -> List[MedicalCode]:
        """Exposes both CPT and ICD-10 codes under a unified MedicalCode format."""
        codes = []
        for d in self.diagnoses:
            codes.append(
                MedicalCode(
                    code=d.code,
                    code_type="ICD-10",
                    description=d.description,
                    confidence=d.confidence,
                )
            )
        for p in self.procedures:
            codes.append(
                MedicalCode(
                    code=p.code,
                    code_type="CPT",
                    description=p.description,
                    confidence=p.confidence,
                )
            )
        return codes
