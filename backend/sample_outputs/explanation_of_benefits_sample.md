# EXPLANATION OF BENEFITS (EOB) — DUAL COVERAGE COORDINATION

**Claim ID:** CLAIM-AARAV-01  
**Patient Name:** Aarav Sen (Member ID: `98765-02`)  
**Adjudication Date:** 2026-08-14  
**Primary Payer:** BlueShield Cross (Policy ID: `BS-120-BLUE`)  
**Secondary Payer:** UnitedHealth (Policy ID: `UH-990-GOLD`)  

---

## 1. Summary of Benefits & Coordination of Benefits (COB)

| Service Description | CPT Code | Billed Amount | Primary Paid (BlueShield) | Secondary Paid (UnitedHealth) | Patient Out-of-Pocket | Adjudication Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **MRI Knee Joint** | `73721` | ₹12,000.00 | ₹0.00 *(Applied to Ded)* | ₹1,800.00 | ₹10,200.00 | Coordinated |
| **Arthroscopic Meniscectomy** | `29881` | ₹1,00,000.00 | ₹73,600.00 | ₹26,400.00 | ₹0.00 | Coordinated (Preauth Req) |
| **TOTALS** | — | **₹1,12,000.00** | **₹73,600.00** | **₹28,200.00** | **₹10,200.00** | **Conservation Law Verified** |

---

## 2. Payer Determination Rationale (Birthday Rule)
- **Primary:** BlueShield Cross — Subscriber Priya Sen (Date of Birth: April 12).
- **Secondary:** UnitedHealth — Subscriber Rajesh Sen (Date of Birth: September 20).
- **Rule Applied:** Under the National Standard Birthday Rule for dependent minor children, the policy of the parent whose birthday occurs earlier in the calendar year is designated as the **Primary Payer**.

---

## 3. Financial Invariant Verification Check
$$\text{Primary Paid (₹73,600.00)} + \text{Secondary Paid (₹28,200.00)} + \text{Patient Responsibility (₹10,200.00)} = \text{Total Billed (₹1,12,000.00)}$$
*All calculations are deterministic and verified with Decimal precision (0.01 tolerance).*
