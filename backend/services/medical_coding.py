import os
import json
import logging
from typing import List
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure

logger = logging.getLogger(__name__)


# Helper schema mirroring the response expectation from Gemini model
class GeminiCodingResponse(BaseModel):
    diagnoses: List[Diagnosis]
    procedures: List[Procedure]


class MedicalCodingService:
    """Service responsible for extracting CPT and ICD-10 medical codes from clinical texts."""

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")

    async def analyze_document(self, doc: ProcessedDocument) -> CodingResult:
        """
        Processes the extracted document text content and returns structured coding results.
        Always attempts LLM reasoning when API key is available.
        """
        if not doc.extracted_text.strip():
            logger.warning("Empty document text passed to MedicalCodingService. Returning empty CodingResult.")
            return CodingResult()

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Using local simulated reasoning fallback.")
            return self._simulate_llm_reasoning(doc)

        prompt = self._build_prompt(doc.extracted_text)

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            logger.info("Calling Gemini API to infer medical codes from clinical text.")
            response = model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiCodingResponse,
                ),
            )

            raw_text = response.text
            logger.debug(f"Gemini medical coding output: {raw_text}")

            parsed_data = json.loads(raw_text)
            validated = GeminiCodingResponse(**parsed_data)

            return CodingResult(
                diagnoses=validated.diagnoses,
                procedures=validated.procedures,
                raw_response=raw_text,
            )
        except Exception as e:
            logger.error(f"Failed to infer medical codes using Gemini LLM: {e}", exc_info=True)
            # Handle malformed response or API exceptions gracefully
            return CodingResult(
                raw_response=json.dumps({"error": f"Inference failure: {str(e)}"})
            )

    def _build_prompt(self, text: str) -> str:
        return f"""
You are an expert clinical medical coder.
Analyze the following clinical document text and extract all relevant medical codes:
1. ICD-10-CM Diagnosis Codes: Look for patient diagnoses, symptoms, or conditions mentioned in the text.
2. CPT Procedure Codes (5-digit): Look for treatments, evaluations, surgical procedures, or therapies performed or proposed.

For each identified code, specify:
- The standard code value (e.g. M23.231 for tear of meniscus, 29881 for meniscectomy, 97110 for therapeutic exercise)
- The medical description of the condition or procedure
- A confidence score between 0.0 and 1.0 based on how explicitly it is documented in the text.

Extracted Text:
\"\"\"
{text}
\"\"\"
"""

    def _simulate_llm_reasoning(self, doc: ProcessedDocument) -> CodingResult:
        """Simulates LLM reasoning using keyword parsing for development fallback when API key is missing."""
        text = doc.extracted_text.lower()
        diagnoses = []
        procedures = []

        # 1. Diagnoses
        if "meniscus" in text or "meniscectomy" in text:
            diagnoses.append(
                Diagnosis(
                    code="M23.231",
                    description="Complete tear of medial meniscus, right knee",
                    confidence=0.95,
                )
            )
        if "acl tear" in text or "acl reconstruction" in text:
            diagnoses.append(
                Diagnosis(
                    code="S83.511A",
                    description="Sprain of anterior cruciate ligament of right knee, initial encounter",
                    confidence=0.90,
                )
            )
        if "knee pain" in text and not any(
            d.code == "M23.231" or d.code == "S83.511A" for d in diagnoses
        ):
            diagnoses.append(
                Diagnosis(code="M25.561", description="Pain in right knee", confidence=0.85)
            )

        # 2. Procedures
        if "meniscectomy" in text or "cpt 29881" in text:
            procedures.append(
                Procedure(
                    code="29881",
                    description="Arthroscopy, knee, surgical; with meniscectomy (medial OR lateral)",
                    confidence=0.98,
                )
            )
        if "acl reconstruction" in text or "cpt 29888" in text:
            procedures.append(
                Procedure(
                    code="29888",
                    description="Arthroscopy, knee, surgical; anterior cruciate ligament repair/reconstruction",
                    confidence=0.95,
                )
            )
        if "physical therapy evaluation" in text or "evaluation" in text or "97161" in text:
            procedures.append(
                Procedure(
                    code="97161",
                    description="Physical therapy evaluation: low complexity",
                    confidence=0.94,
                )
            )
        if "physical therapy" in text or "therapeutic exercise" in text or "97110" in text:
            procedures.append(
                Procedure(
                    code="97110",
                    description="Therapeutic procedure, 1 or more areas, each 15 minutes; therapeutic exercises",
                    confidence=0.92,
                )
            )
        if "mri" in text or "cpt 73721" in text:
            procedures.append(
                Procedure(
                    code="73721",
                    description="Magnetic resonance (eg, MRI), lower extremity joint; without contrast material(s)",
                    confidence=0.97,
                )
            )

        return CodingResult(
            diagnoses=diagnoses,
            procedures=procedures,
            raw_response=json.dumps(
                {
                    "diagnoses": [d.model_dump() for d in diagnoses],
                    "procedures": [p.model_dump() for p in procedures],
                }
            ),
        )
