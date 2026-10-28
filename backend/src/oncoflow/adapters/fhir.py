"""Allowlist report-status fields without persisting source payloads."""

from ..exceptions import ReportFormatError


class FHIRReportAdapter:
    """Normalize the synthetic DiagnosticReport-shaped demo input."""

    SUPPORTED_STATUSES = frozenset(
        {
            "registered",
            "partial",
            "preliminary",
            "final",
            "corrected",
            "cancelled",
            "entered-in-error",
        }
    )
    FINAL_OR_REVIEW_STATUSES = frozenset(
        {"final", "corrected", "cancelled", "entered-in-error"}
    )

    @classmethod
    def normalize(cls, payload: dict) -> dict[str, str]:
        """Return only identifier and status; errors never echo input."""
        if payload.get("resourceType") != "DiagnosticReport":
            raise ReportFormatError("Expected a DiagnosticReport resource.")
        status = payload.get("status")
        if not isinstance(status, str) or status not in cls.SUPPORTED_STATUSES:
            raise ReportFormatError("Unsupported report status.")
        report_id = payload.get("id")
        if not isinstance(report_id, str) or not 1 <= len(report_id) <= 100:
            raise ReportFormatError("A valid report identifier is required.")
        return {
            "report_id": report_id,
            "status": (
                status if status in cls.FINAL_OR_REVIEW_STATUSES else "pending"
            ),
        }
