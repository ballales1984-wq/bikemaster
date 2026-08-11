"""AI audit log repository - data access for AI interaction audit logs."""

from __future__ import annotations


class AIAuditRepository:
    @staticmethod
    def save_ai_audit_log(
        athlete_id: int,
        provider: str,
        model: str,
        prompt_hash: str,
        response_length: int = 0,
        tool_calls: int = 0,
        latency_ms: int = 0,
        tenant_id: int = 0,
    ) -> None:
        """Save an AI interaction audit log entry."""
        from ...db.database import save_ai_audit_log

        return save_ai_audit_log(
            athlete_id=athlete_id,
            provider=provider,
            model=model,
            prompt_hash=prompt_hash,
            response_length=response_length,
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            tenant_id=tenant_id,
        )
