import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.schemas.insurance_engine import (
    InsurancePolicy,
    Member,
    CoverageRule,
    CoverageDecision,
)

logger = logging.getLogger(__name__)

# Base directory of the backend package (c:\Projects\hcl\duco-agent-ai-assessment\backend)
BASE_DIR = Path(__file__).resolve().parent.parent


class InsuranceService:
    """Service class for loading and querying mock insurance policies."""

    def __init__(self, mock_data_dir: Optional[Path] = None):
        if mock_data_dir is None:
            self.mock_data_dir = BASE_DIR / "mock_data"
        else:
            self.mock_data_dir = Path(mock_data_dir)

        self._policies: Dict[str, InsurancePolicy] = {}
        self.load_policies()

    def load_policies(self) -> None:
        """Loads all policy JSON configurations from the mock data directory."""
        logger.info(f"Loading insurance policies from {self.mock_data_dir}")
        if not self.mock_data_dir.exists():
            logger.warning(f"Mock data directory does not exist: {self.mock_data_dir}")
            return

        for file_path in self.mock_data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Only load if it contains policy structure
                if "policy_id" in data and "provider_name" in data:
                    policy = InsurancePolicy(**data)
                    self._policies[policy.policy_id] = policy
                    logger.info(f"Successfully loaded policy: {policy.provider_name} ({policy.policy_id})")
            except Exception as e:
                logger.error(f"Failed to load policy file {file_path}: {e}")

    def get_policy(self, member_id: str) -> Optional[InsurancePolicy]:
        """Retrieves the policy associated with the given member ID."""
        for policy in self._policies.values():
            for member in policy.members:
                if member.member_id == member_id:
                    return policy
        return None

    def get_member(self, member_id: str) -> Optional[Member]:
        """Retrieves the member details for a given member ID."""
        for policy in self._policies.values():
            for member in policy.members:
                if member.member_id == member_id:
                    return member
        return None

    def get_member_role(self, member_id: str) -> Optional[str]:
        """Retrieves the role (subscriber or dependent) for a given member ID."""
        member = self.get_member(member_id)
        if member:
            return member.role
        return None

    def is_procedure_covered(self, member_id: str, cpt_code: str) -> bool:
        """Determines if a procedure is covered under the member's active policy."""
        policy = self.get_policy(member_id)
        if not policy:
            logger.warning(f"No policy found for member ID: {member_id}")
            return False

        # Find coverage rule for the cpt code
        for rule in policy.coverage_rules:
            if rule.cpt_code == cpt_code:
                return rule.is_covered

        # By default, if no rule is found, assume not covered
        return False

    def requires_preauthorization(self, member_id: str, cpt_code: str) -> bool:
        """Determines if a procedure requires pre-authorization under the member's active policy."""
        policy = self.get_policy(member_id)
        if not policy:
            logger.warning(f"No policy found for member ID: {member_id}")
            return False

        # Find coverage rule for the cpt code
        for rule in policy.coverage_rules:
            if rule.cpt_code == cpt_code:
                return rule.requires_preauth

        # By default, if no rule is found, assume no pre-authorization rule exists/needed (or false)
        return False

    def evaluate_coverage(self, member_id: str, cpt_code: str) -> CoverageDecision:
        """Performs a full coverage decision evaluation for a member and procedure code."""
        policy = self.get_policy(member_id)
        member = self.get_member(member_id)

        if not policy or not member:
            return CoverageDecision(
                is_covered=False,
                requires_preauth=False,
                deductible_applies=False,
                coinsurance_rate=0.0,
                message=f"Member ID '{member_id}' not found under any active policy."
            )

        # Look for matching coverage rule
        matching_rule: Optional[CoverageRule] = None
        for rule in policy.coverage_rules:
            if rule.cpt_code == cpt_code:
                matching_rule = rule
                break

        if not matching_rule:
            return CoverageDecision(
                is_covered=False,
                requires_preauth=False,
                deductible_applies=False,
                coinsurance_rate=0.0,
                message=f"CPT code '{cpt_code}' is not recognized or covered under the {policy.provider_name} policy."
            )

        if not matching_rule.is_covered:
            return CoverageDecision(
                is_covered=False,
                requires_preauth=False,
                deductible_applies=False,
                coinsurance_rate=0.0,
                message=f"CPT code '{cpt_code}' is explicitly excluded from coverage."
            )

        # Determine if deductible applies. Normally yes, for standard clinical procedures.
        # Coinsurance rate is retrieved from policy.
        coins_rate = policy.coinsurance.rate
        preauth = matching_rule.requires_preauth

        limitations_msg = f" (Limitations: {matching_rule.limitations})" if matching_rule.limitations else ""
        msg = f"Procedure {cpt_code} is covered under {policy.provider_name}."
        if preauth:
            msg += f" Pre-authorization IS required.{limitations_msg}"
        else:
            msg += f" No pre-authorization required.{limitations_msg}"

        return CoverageDecision(
            is_covered=True,
            requires_preauth=preauth,
            deductible_applies=True,
            coinsurance_rate=coins_rate,
            message=msg
        )
