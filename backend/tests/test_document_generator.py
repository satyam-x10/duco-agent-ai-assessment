import pytest
from pathlib import Path
from services.document_generator import doc_generator

def test_generate_scanned_image(tmp_path):
    generator = doc_generator
    generator.output_dir = tmp_path
    path = generator.generate_scanned_image(
        title="Test Medical Clinic",
        document_category="Physical Therapy Invoice",
        patient_name="Aarav Sen",
        member_id="MEM-12345",
        cpt_code="97110",
        cpt_desc="Therapeutic Exercises",
        estimated_amount=150.00
    )
    assert path.exists()
    assert path.stat().st_size > 0
