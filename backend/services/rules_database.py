import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

MOCK_DATA_DIR = Path(__file__).resolve().parent.parent / "mock_data"


class RulesDatabaseService:
    """Service providing query interface for ICD, CPT, and Pre-Authorization JSON rules databases."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or MOCK_DATA_DIR
        self._icd_cpt_data: Optional[Dict[str, Any]] = None
        self._preauth_data: Optional[Dict[str, Any]] = None

    def _load_icd_cpt(self) -> Dict[str, Any]:
        if self._icd_cpt_data is None:
            file_path = self.data_dir / "icd_cpt_database.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self._icd_cpt_data = json.load(f)
            else:
                logger.warning(f"File {file_path} not found. Using fallback empty dictionary.")
                self._icd_cpt_data = {"icd_codes": {}, "cpt_codes": {}}
        return self._icd_cpt_data

    def _load_preauth(self) -> Dict[str, Any]:
        if self._preauth_data is None:
            file_path = self.data_dir / "preauth_rules.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self._preauth_data = json.load(f)
            else:
                logger.warning(f"File {file_path} not found. Using fallback empty dictionary.")
                self._preauth_data = {"rules": {}}
        return self._preauth_data

    def get_cpt_code(self, cpt_code: str) -> Optional[Dict[str, Any]]:
        """Queries CPT code details, description, allowed amount, and pre-auth requirement."""
        data = self._load_icd_cpt()
        return data.get("cpt_codes", {}).get(str(cpt_code))

    def get_icd_code(self, icd_code: str) -> Optional[Dict[str, Any]]:
        """Queries ICD-10 diagnosis details, category, and validity."""
        data = self._load_icd_cpt()
        return data.get("icd_codes", {}).get(str(icd_code))

    def list_cpt_codes(self) -> List[Dict[str, Any]]:
        """Lists all registered CPT procedure codes."""
        data = self._load_icd_cpt()
        return list(data.get("cpt_codes", {}).values())

    def list_icd_codes(self) -> List[Dict[str, Any]]:
        """Lists all registered ICD-10 diagnosis codes."""
        data = self._load_icd_cpt()
        return list(data.get("icd_codes", {}).values())

    def get_preauth_rule(self, cpt_code: str) -> Optional[Dict[str, Any]]:
        """Queries pre-authorization requirement criteria and document checklists for a CPT code."""
        data = self._load_preauth()
        return data.get("rules", {}).get(str(cpt_code))

    def is_preauth_required(self, cpt_code: str) -> bool:
        """Determines if a CPT procedure code requires prior authorization."""
        rule = self.get_preauth_rule(cpt_code)
        if rule:
            return rule.get("requires_preauth", False)
        # Fallback check against CPT database definition
        cpt = self.get_cpt_code(cpt_code)
        if cpt:
            return cpt.get("requires_prior_authorization", False)
        return False


rules_db = RulesDatabaseService()
