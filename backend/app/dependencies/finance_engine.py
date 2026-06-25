from services.finance_engine import FinanceEngine

_finance_engine_instance = None


def get_finance_service() -> FinanceEngine:
    """Dependency provider resolving the FinanceEngine singleton."""
    global _finance_engine_instance
    if _finance_engine_instance is None:
        _finance_engine_instance = FinanceEngine()
    return _finance_engine_instance
