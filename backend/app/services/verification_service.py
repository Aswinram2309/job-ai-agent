import logging
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class VerificationService:
    """
    Service responsible for verifying whether an application was truly submitted
    and recognized by the provider system.
    """

    @staticmethod
    def verify_provider_receipt(provider: str, response_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates provider API response and extracts verifiable confirmation reference.
        Returns: (is_verified, status_str, verification_evidence)
        """
        evidence = {
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "raw_evidence": response_data
        }

        if provider == "greenhouse":
            # Greenhouse returns application id upon accepted candidate creation
            app_id = response_data.get("id") or response_data.get("candidate_id")
            if app_id:
                evidence["receipt_id"] = str(app_id)
                evidence["channel"] = "greenhouse_api"
                return True, "verified", evidence

        elif provider == "lever":
            # Lever returns application posting response
            post_id = response_data.get("applicationId") or response_data.get("id")
            if post_id:
                evidence["receipt_id"] = str(post_id)
                evidence["channel"] = "lever_api"
                return True, "verified", evidence

        # If evidence cannot be conclusively determined
        return False, "submission_unknown", evidence
