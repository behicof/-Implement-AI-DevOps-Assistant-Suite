"""
GitHub workflow and PR monitoring module
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from github import Github
from github.Repository import Repository

logger = logging.getLogger(__name__)


class WorkflowMonitor:
    """GitHub workflow monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.github_token = config.get("token")
        self.github = Github(self.github_token) if self.github_token else None
        
    async def monitor_repository(self, repository: str, interval: int = 300):
        """Monitor workflows for a specific repository"""
        if not self.github:
            logger.error("GitHub token not configured")
            return
            
        repo = self.github.get_repo(repository)
        logger.info(f"Starting workflow monitoring for {repository}")
        
        while True:
            try:
                await self._check_workflows(repo)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Workflow monitoring error: {e}")
                await asyncio.sleep(60)  # Brief pause on error
                
    async def _check_workflows(self, repo: Repository):
        """Check workflow status"""
        workflows = repo.get_workflows()
        
        for workflow in workflows:
            runs = workflow.get_runs()
            for run in runs[:5]:  # Check last 5 runs
                logger.info(f"Workflow: {workflow.name}, Status: {run.status}, Conclusion: {run.conclusion}")


class PRMonitor:
    """GitHub pull request monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.github_token = config.get("token")
        self.github = Github(self.github_token) if self.github_token else None
        
    async def monitor_repository(self, repository: str, interval: int = 180):
        """Monitor pull requests for a specific repository"""
        if not self.github:
            logger.error("GitHub token not configured")
            return
            
        repo = self.github.get_repo(repository)
        logger.info(f"Starting PR monitoring for {repository}")
        
        while True:
            try:
                await self._check_pull_requests(repo)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"PR monitoring error: {e}")
                await asyncio.sleep(60)  # Brief pause on error
                
    async def _check_pull_requests(self, repo: Repository):
        """Check pull request status"""
        prs = repo.get_pulls(state='open')
        
        for pr in prs:
            logger.info(f"PR: {pr.title}, Status: {pr.state}, Reviews: {pr.get_reviews().totalCount}")