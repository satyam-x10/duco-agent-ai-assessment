import os
import json
import logging
from typing import List
from pydantic import BaseModel
from google import genai
from google.genai import types
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure

logger = logging.getLogger(__name__)


# Helper schema mirroring the response expectation from Gemini model
class GeminiCodingResponse(BaseModel):
    diagnoses: List[Diagnosis]
    procedures: List[Procedure]


class MedicalCodingService:
    """Service responsible for extracting CPT and ICD-10 medical codes from clinical texts using Gemini."""

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")

    async def analyze_document(self, doc: ProcessedDocument) -> CodingResult:
        """
        Processes the extracted document text content and returns structured coding results.
        Requires a valid GEMINI_API_KEY. Raises RuntimeError if unavailable.
        """
        if not doc.extracted_text.strip():
            logger.warning("Empty document text passed to MedicalCodingService. Returning empty CodingResult.")
            return CodingResult()

        if not self.api_key:
            raise RuntimeError(
                "Medical Coding unavailable: GEMINI_API_KEY is not configured. "
                "Please set GEMINI_API_KEY in your environment to enable Gemini-based medical code inference."
            )

        prompt = self._build_prompt(doc.extracted_text)

        try:
            client = genai.Client(api_key=self.api_key)

            logger.info("Calling Gemini API to infer medical codes from clinical text.")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": GeminiCodingResponse,
                },
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
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Failed to infer medical codes using Gemini LLM: {e}", exc_info=True)
            raise RuntimeError(
                f"Gemini medical coding inference failed for document '{doc.document_type.value}': {str(e)}"
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
