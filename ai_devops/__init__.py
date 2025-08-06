"""
AI DevOps Assistant Suite

A comprehensive AI-powered DevOps assistant that integrates with cryptocurrency exchanges,
provides automated code analysis, monitors GitHub workflows, and offers real-time insights
through an interactive dashboard.

Features:
- Multi-exchange cryptocurrency integration (Binance, Wallex, Bitpin, Nobitex)
- AI-powered code analysis with exchange-specific security checks
- Real-time monitoring and alerting
- Interactive web dashboard
- CLI interface for automation
- GitHub Actions integration

Author: AI DevOps Team
License: MIT
"""

__version__ = "1.0.0"
__author__ = "AI DevOps Team"
__email__ = "devops@example.com"

# Core imports
from .main import cli
from .monitor import WorkflowMonitor, PRMonitor
from .analyzer import CodeAnalyzer, ExchangeAnalyzer
from .feedback import FeedbackProcessor

# Exchange imports
from .exchanges import ExchangeManager, ExchangeMonitor

__all__ = [
    "cli",
    "WorkflowMonitor",
    "PRMonitor", 
    "CodeAnalyzer",
    "ExchangeAnalyzer",
    "FeedbackProcessor",
    "ExchangeManager",
    "ExchangeMonitor",
]