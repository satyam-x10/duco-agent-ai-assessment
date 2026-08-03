import io
import os
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)


class SyntheticDocumentGenerator:
    """Generates realistic synthetic scanned medical notes, invoices, and insurance documents."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (Path(__file__).resolve().parent.parent / "uploads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_scanned_image(
        self,
        title: str = "SUMMIT HEALTHCARE CLINIC",
        document_category: str = "Surgeon Cost Estimate",
        patient_name: str = "Priya Sen",
        member_id: str = "MEM-882194",
        cpt_code: str = "29881",
        cpt_desc: str = "Knee Arthroscopy with Meniscectomy",
        estimated_amount: float = 3200.00,
        add_noise: bool = True,
        rotate_angle: float = 1.2
    ) -> Path:
        """
        Generates a synthetic scanned image file with simulated scan rotation, texture noise,
        header branding, tabular breakdown, and clinician signature stamp.
        """
        width, height = 800, 1050
        # Background paper color (slightly off-white / aged paper)
        paper_color = (250, 248, 242)
        image = Image.new("RGB", (width, height), paper_color)
        draw = ImageDraw.Draw(image)

        # Draw borders and header line
        draw.rectangle([20, 20, width - 20, height - 20], outline=(180, 180, 180), width=2)
        draw.rectangle([30, 30, width - 30, 120], fill=(230, 240, 250), outline=(100, 140, 180), width=2)

        # Default system font fallback
        try:
            title_font = ImageFont.truetype("arial.ttf", 26)
            subtitle_font = ImageFont.truetype("arial.ttf", 18)
            body_font = ImageFont.truetype("arial.ttf", 15)
            small_font = ImageFont.truetype("arial.ttf", 12)
        except Exception:
            title_font = subtitle_font = body_font = small_font = ImageFont.load_default()

        # Header text
        draw.text((45, 45), title.upper(), fill=(20, 50, 90), font=title_font)
        draw.text((45, 80), f"DOCUMENT TYPE: {document_category.upper()}", fill=(60, 60, 60), font=subtitle_font)

        # Metadata Section
        y = 140
        draw.text((45, y), f"Patient Name: {patient_name}", fill=(0, 0, 0), font=body_font)
        draw.text((450, y), f"Member ID: {member_id}", fill=(0, 0, 0), font=body_font)
        y += 30
        draw.text((45, y), "Date of Service: 2026-08-01", fill=(0, 0, 0), font=body_font)
        draw.text((450, y), "Facility: Summit Medical Center", fill=(0, 0, 0), font=body_font)
        y += 40

        # Divider line
        draw.line([40, y, width - 40, y], fill=(150, 150, 150), width=2)
        y += 20

        # Procedure Table Header
        draw.rectangle([40, y, width - 40, y + 30], fill=(220, 225, 230))
        draw.text((50, y + 6), "CPT Code", fill=(0, 0, 0), font=body_font)
        draw.text((160, y + 6), "Description", fill=(0, 0, 0), font=body_font)
        draw.text((620, y + 6), "Billed Amount", fill=(0, 0, 0), font=body_font)
        y += 35

        # Procedure Row
        draw.text((50, y), str(cpt_code), fill=(0, 0, 0), font=body_font)
        draw.text((160, y), cpt_desc[:40], fill=(0, 0, 0), font=body_font)
        draw.text((620, y), f"${estimated_amount:.2f}", fill=(0, 0, 0), font=body_font)
        y += 40

        draw.line([40, y, width - 40, y], fill=(200, 200, 200), width=1)
        y += 20

        # Clinical Notes / Findings
        draw.text((45, y), "CLINICAL FINDINGS & IMPRESSION:", fill=(20, 50, 90), font=subtitle_font)
        y += 30
        notes = (
            f"Patient presents with persistent right knee pain and localized tenderness along the joint line.\n"
            f"MRI findings confirm right medial meniscal tear. Conservative physical therapy trial completed.\n"
            f"Surgical intervention ({cpt_code} - {cpt_desc}) is recommended."
        )
        for line in notes.split("\n"):
            draw.text((45, y), line, fill=(40, 40, 40), font=body_font)
            y += 24

        # Stamp / Signature simulation
        y = height - 180
        draw.rectangle([50, y, 280, y + 80], outline=(180, 40, 40), width=3)
        draw.text((60, y + 15), "[ APPROVED STAMP ]", fill=(180, 40, 40), font=subtitle_font)
        draw.text((60, y + 45), "Dr. Sarah Jenkins, MD", fill=(180, 40, 40), font=small_font)

        # Apply scan rotation and noise artifacts if requested
        if rotate_angle != 0.0:
            image = image.rotate(rotate_angle, expand=False, fillcolor=paper_color)

        if add_noise:
            # Add subtle gaussian blur or grain simulation
            image = image.filter(ImageFilter.GaussianBlur(radius=0.4))

        filename = f"scanned_doc_{random.randint(1000, 9999)}.png"
        save_path = self.output_dir / filename
        image.save(save_path, format="PNG")
        logger.info(f"Synthetic scanned document generated at {save_path}")
        return save_path


doc_generator = SyntheticDocumentGenerator()
