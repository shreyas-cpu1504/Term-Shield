"""
Ask My T&C / Contract Q&A Service Facade.
Directs all inquiries to the unified modular QA pipeline in app.services.qa.
"""

from app.services.qa.service import QAService

__all__ = ["QAService"]