"""
Service to dynamically generate SVG cost-flow waterfall diagrams and markdown EOB artifacts
from live COB decisions and financial state.
"""

from decimal import Decimal
import html
from typing import Optional

from app.schemas.cob_engine import COBDecision
from app.schemas.reports import FinancialSummary


def format_currency_inr(amount: float | Decimal | int | None) -> str:
    """Format a monetary amount in Indian Rupee notation (e.g. ₹1,12,000.00)."""
    if amount is None:
        return "₹0.00"
    val = float(amount)
    is_neg = val < 0
    val = abs(val)
    
    parts = f"{val:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]
    
    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        # Group in pairs of 2 from right to left
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_int = ",".join(groups) + "," + last3
        
    return f"{'-' if is_neg else ''}₹{formatted_int}.{dec_part}"


class CostFlowVisualizerService:
    """Generates visual artifacts (SVG waterfall diagrams and Markdown EOBs) from live COB results."""

    @staticmethod
    def generate_svg(
        billed: float,
        primary_paid: float,
        secondary_paid: float,
        patient_responsibility: float,
        primary_payer: str = "Primary Payer",
        secondary_payer: Optional[str] = None,
        patient_name: str = "Patient",
        lines_summary: Optional[list[dict]] = None,
        currency_symbol: str = "₹"
    ) -> str:
        """Dynamically builds an SVG waterfall diagram reflecting exact adjudicated financial amounts."""
        has_secondary = bool(secondary_payer and secondary_payer.strip() and secondary_payer != "None")
        
        # Calculate coverage percentages
        total_insurer_paid = primary_paid + (secondary_paid if has_secondary else 0.0)
        insurer_pct = (total_insurer_paid / billed * 100) if billed > 0 else 0.0
        patient_pct = (patient_responsibility / billed * 100) if billed > 0 else 0.0

        billed_fmt = format_currency_inr(billed)
        pri_paid_fmt = format_currency_inr(primary_paid)
        sec_paid_fmt = format_currency_inr(secondary_paid)
        patient_fmt = format_currency_inr(patient_responsibility)
        total_ins_fmt = format_currency_inr(total_insurer_paid)

        # Lines text summary
        lines_svg_text = ""
        if lines_summary:
            y_offset = 120
            for idx, item in enumerate(lines_summary[:3]):  # Show up to 3 lines
                cpt = html.escape(str(item.get("cpt_code", "")))
                amt = format_currency_inr(item.get("billed_amount", 0.0))
                lines_svg_text += f'<text x="20" y="{y_offset}" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">CPT {cpt}: {amt}</text>\n'
                y_offset += 22
        else:
            lines_svg_text = f'<text x="20" y="125" font-family="system-ui, sans-serif" font-size="12" font-weight="600" fill="#475569">Adjudicated Claim Lines</text>\n'

        escaped_patient = html.escape(patient_name)
        escaped_pri_payer = html.escape(primary_payer or "Primary Payer")
        escaped_sec_payer = html.escape(secondary_payer or "Secondary Payer")

        if has_secondary:
            # 4-Column Waterfall Layout (Width: 960, Height: 440)
            return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 440" width="100%" height="100%">
  <defs>
    <linearGradient id="primaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7" />
      <stop offset="100%" stop-color="#0369a1" />
    </linearGradient>
    <linearGradient id="secondaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6" />
      <stop offset="100%" stop-color="#6d28d9" />
    </linearGradient>
    <linearGradient id="patientGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>
    <filter id="cardShadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0f172a" flood-opacity="0.08" />
    </filter>
  </defs>

  <!-- Background Canvas -->
  <rect width="960" height="440" fill="#f8fafc" rx="16" />

  <!-- Header -->
  <text x="40" y="45" font-family="system-ui, -apple-system, sans-serif" font-size="20" font-weight="800" fill="#0f172a">Dual Coverage Cost-Flow Waterfall</text>
  <text x="40" y="70" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="500" fill="#64748b">Patient: {escaped_patient} — Total Billed: {billed_fmt}</text>

  <!-- Node 1: Total Billed -->
  <g transform="translate(40, 110)" filter="url(#cardShadow)">
    <rect width="190" height="260" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" />
    <rect width="190" height="6" rx="3" fill="#64748b" />
    <text x="20" y="35" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#64748b" text-transform="uppercase">TOTAL BILLED</text>
    <text x="20" y="68" font-family="system-ui, sans-serif" font-size="22" font-weight="800" fill="#0f172a">{billed_fmt}</text>
    <line x1="20" y1="90" x2="170" y2="90" stroke="#f1f5f9" stroke-width="1.5" />
    {lines_svg_text}
    <text x="20" y="210" font-family="system-ui, sans-serif" font-size="11" font-weight="500" fill="#94a3b8">Patient: {escaped_patient}</text>
    <text x="20" y="230" font-family="system-ui, sans-serif" font-size="11" font-weight="500" fill="#94a3b8">Dual Coordination Active</text>
  </g>

  <!-- Connector 1 -->
  <path d="M 230 240 L 270 240" fill="none" stroke="#cbd5e1" stroke-width="2.5" stroke-dasharray="4 4" />

  <!-- Node 2: Primary Payer -->
  <g transform="translate(270, 110)" filter="url(#cardShadow)">
    <rect width="200" height="260" rx="12" fill="#ffffff" stroke="#bae6fd" stroke-width="1.5" />
    <rect width="200" height="6" rx="3" fill="url(#primaryGrad)" />
    <text x="20" y="35" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#0284c7">PRIMARY PAYER</text>
    <text x="20" y="58" font-family="system-ui, sans-serif" font-size="14" font-weight="800" fill="#0369a1">{escaped_pri_payer}</text>
    <text x="20" y="90" font-family="system-ui, sans-serif" font-size="20" font-weight="800" fill="#0369a1">Paid: {pri_paid_fmt}</text>
    <line x1="20" y1="110" x2="180" y2="110" stroke="#f1f5f9" stroke-width="1.5" />
    <text x="20" y="140" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">Primary Adjudication</text>
    <text x="20" y="165" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">Deductible/Coinsurance applied</text>
    <text x="20" y="205" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#0369a1">Balance Rolled Over</text>
    <text x="20" y="225" font-family="system-ui, sans-serif" font-size="11" font-weight="500" fill="#64748b">Transferred to Secondary</text>
  </g>

  <!-- Connector 2 -->
  <path d="M 470 240 L 510 240" fill="none" stroke="#cbd5e1" stroke-width="2.5" stroke-dasharray="4 4" />

  <!-- Node 3: Secondary Payer -->
  <g transform="translate(510, 110)" filter="url(#cardShadow)">
    <rect width="200" height="260" rx="12" fill="#ffffff" stroke="#ddd6fe" stroke-width="1.5" />
    <rect width="200" height="6" rx="3" fill="url(#secondaryGrad)" />
    <text x="20" y="35" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#8b5cf6">SECONDARY PAYER</text>
    <text x="20" y="58" font-family="system-ui, sans-serif" font-size="14" font-weight="800" fill="#6d28d9">{escaped_sec_payer}</text>
    <text x="20" y="90" font-family="system-ui, sans-serif" font-size="20" font-weight="800" fill="#6d28d9">Paid: {sec_paid_fmt}</text>
    <line x1="20" y1="110" x2="180" y2="110" stroke="#f1f5f9" stroke-width="1.5" />
    <text x="20" y="140" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">COB Coordination</text>
    <text x="20" y="165" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">Normal Benefit Comparison</text>
    <text x="20" y="205" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#16a34a">Total Insurer Paid:</text>
    <text x="20" y="228" font-family="system-ui, sans-serif" font-size="13" font-weight="800" fill="#16a34a">{total_ins_fmt} ({insurer_pct:.1f}%)</text>
  </g>

  <!-- Connector 3 -->
  <path d="M 710 240 L 750 240" fill="none" stroke="#cbd5e1" stroke-width="2.5" stroke-dasharray="4 4" />

  <!-- Node 4: Patient Responsibility -->
  <g transform="translate(750, 110)" filter="url(#cardShadow)">
    <rect width="170" height="260" rx="12" fill="#fffbeb" stroke="#fde68a" stroke-width="1.5" />
    <rect width="170" height="6" rx="3" fill="url(#patientGrad)" />
    <text x="16" y="35" font-family="system-ui, sans-serif" font-size="10.5" font-weight="700" fill="#d97706">PATIENT OUT-OF-POCKET</text>
    <text x="16" y="68" font-family="system-ui, sans-serif" font-size="22" font-weight="800" fill="#b45309">{patient_fmt}</text>
    <line x1="16" y1="90" x2="154" y2="90" stroke="#fef3c7" stroke-width="1.5" />
    <text x="16" y="125" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#78350f">Final Copay/Ded</text>
    <text x="16" y="150" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#78350f">Share: {patient_pct:.1f}%</text>
    <text x="16" y="195" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#047857">Patient Savings:</text>
    <text x="16" y="220" font-family="system-ui, sans-serif" font-size="13" font-weight="800" fill="#047857">{total_ins_fmt}</text>
  </g>
</svg>"""
        else:
            # 3-Column Single Payer Waterfall Layout (Width: 760, Height: 440)
            return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 440" width="100%" height="100%">
  <defs>
    <linearGradient id="primaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7" />
      <stop offset="100%" stop-color="#0369a1" />
    </linearGradient>
    <linearGradient id="patientGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>
    <filter id="cardShadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0f172a" flood-opacity="0.08" />
    </filter>
  </defs>

  <!-- Background Canvas -->
  <rect width="760" height="440" fill="#f8fafc" rx="16" />

  <!-- Header -->
  <text x="40" y="45" font-family="system-ui, -apple-system, sans-serif" font-size="20" font-weight="800" fill="#0f172a">Single Payer Claim Cost-Flow Waterfall</text>
  <text x="40" y="70" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="500" fill="#64748b">Patient: {escaped_patient} — Total Billed: {billed_fmt}</text>

  <!-- Node 1: Total Billed -->
  <g transform="translate(40, 110)" filter="url(#cardShadow)">
    <rect width="200" height="260" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" />
    <rect width="200" height="6" rx="3" fill="#64748b" />
    <text x="20" y="35" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#64748b" text-transform="uppercase">TOTAL BILLED</text>
    <text x="20" y="68" font-family="system-ui, sans-serif" font-size="22" font-weight="800" fill="#0f172a">{billed_fmt}</text>
    <line x1="20" y1="90" x2="180" y2="90" stroke="#f1f5f9" stroke-width="1.5" />
    {lines_svg_text}
    <text x="20" y="210" font-family="system-ui, sans-serif" font-size="11" font-weight="500" fill="#94a3b8">Patient: {escaped_patient}</text>
  </g>

  <!-- Connector 1 -->
  <path d="M 240 240 L 280 240" fill="none" stroke="#cbd5e1" stroke-width="2.5" stroke-dasharray="4 4" />

  <!-- Node 2: Primary Payer -->
  <g transform="translate(280, 110)" filter="url(#cardShadow)">
    <rect width="210" height="260" rx="12" fill="#ffffff" stroke="#bae6fd" stroke-width="1.5" />
    <rect width="210" height="6" rx="3" fill="url(#primaryGrad)" />
    <text x="20" y="35" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#0284c7">PRIMARY PAYER</text>
    <text x="20" y="58" font-family="system-ui, sans-serif" font-size="14" font-weight="800" fill="#0369a1">{escaped_pri_payer}</text>
    <text x="20" y="90" font-family="system-ui, sans-serif" font-size="20" font-weight="800" fill="#0369a1">Paid: {pri_paid_fmt}</text>
    <line x1="20" y1="110" x2="190" y2="110" stroke="#f1f5f9" stroke-width="1.5" />
    <text x="20" y="140" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">Primary Coverage Only</text>
    <text x="20" y="165" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#475569">Direct Adjudication</text>
    <text x="20" y="205" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#16a34a">Total Insurer Paid:</text>
    <text x="20" y="228" font-family="system-ui, sans-serif" font-size="13" font-weight="800" fill="#16a34a">{pri_paid_fmt} ({insurer_pct:.1f}%)</text>
  </g>

  <!-- Connector 2 -->
  <path d="M 490 240 L 530 240" fill="none" stroke="#cbd5e1" stroke-width="2.5" stroke-dasharray="4 4" />

  <!-- Node 3: Patient Responsibility -->
  <g transform="translate(530, 110)" filter="url(#cardShadow)">
    <rect width="190" height="260" rx="12" fill="#fffbeb" stroke="#fde68a" stroke-width="1.5" />
    <rect width="190" height="6" rx="3" fill="url(#patientGrad)" />
    <text x="16" y="35" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#d97706">PATIENT OUT-OF-POCKET</text>
    <text x="16" y="68" font-family="system-ui, sans-serif" font-size="22" font-weight="800" fill="#b45309">{patient_fmt}</text>
    <line x1="16" y1="90" x2="174" y2="90" stroke="#fef3c7" stroke-width="1.5" />
    <text x="16" y="125" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#78350f">Deductible + Coinsurance</text>
    <text x="16" y="150" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#78350f">Patient Share: {patient_pct:.1f}%</text>
    <text x="16" y="195" font-family="system-ui, sans-serif" font-size="11" font-weight="700" fill="#047857">Insurer Covered:</text>
    <text x="16" y="220" font-family="system-ui, sans-serif" font-size="13" font-weight="800" fill="#047857">{pri_paid_fmt}</text>
  </g>
</svg>"""
