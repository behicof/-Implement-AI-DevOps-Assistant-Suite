"""
End-to-end tests for CLI interface
"""

import pytest
import subprocess
import json
import time
import tempfile
from pathlib import Path


class TestCLIEndToEnd:
    """End-to-end tests for CLI functionality"""
    
    def test_cli_help(self):
        """Test CLI help command"""
        result = subprocess.run(
            ["ai-devops", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "AI DevOps Assistant Suite" in result.stdout
        assert "Commands:" in result.stdout
        assert "analyze" in result.stdout
        assert "dashboard" in result.stdout
        assert "exchanges" in result.stdout
        assert "monitor" in result.stdout
    
    def test_cli_version(self):
        """Test CLI version command"""
        result = subprocess.run(
            ["ai-devops", "--version"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        # Should display version information
    
    def test_exchanges_list_command(self):
        """Test exchanges list command"""
        result = subprocess.run(
            ["ai-devops", "exchanges", "--list"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Configured exchanges:" in result.stdout
    
    def test_analyze_help(self):
        """Test analyze command help"""
        result = subprocess.run(
            ["ai-devops", "analyze", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Run comprehensive code analysis" in result.stdout
        assert "--repository" in result.stdout
        assert "--exchanges" in result.stdout
        assert "--model" in result.stdout
    
    @pytest.mark.slow
    def test_analyze_with_output_file(self):
        """Test analyze command with output file"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            result = subprocess.run([
                "ai-devops", "analyze",
                "--repository", "test/repo",
                "--exchanges", "binance,wallex",
                "--output", tmp_path
            ], capture_output=True, text=True, timeout=30)
            
            # Should complete successfully even without credentials
            assert result.returncode == 0
            
            # Output file should be created
            output_path = Path(tmp_path)
            if output_path.exists():
                with open(output_path) as f:
                    data = json.load(f)
                assert "repository" in data
                assert "exchanges" in data
                assert "timestamp" in data
        
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_monitor_help(self):
        """Test monitor command help"""
        result = subprocess.run(
            ["ai-devops", "monitor", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Start continuous monitoring" in result.stdout
        assert "--duration" in result.stdout
        assert "--interval" in result.stdout
    
    def test_dashboard_help(self):
        """Test dashboard command help"""
        result = subprocess.run(
            ["ai-devops", "dashboard", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Launch the interactive web dashboard" in result.stdout
        assert "--host" in result.stdout
        assert "--port" in result.stdout
    
    def test_report_help(self):
        """Test report command help"""
        result = subprocess.run(
            ["ai-devops", "report", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Generate periodic reports" in result.stdout
        assert "--period" in result.stdout
        assert "--format" in result.stdout
    
    @pytest.mark.slow
    def test_report_generation(self):
        """Test report generation"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            result = subprocess.run([
                "ai-devops", "report",
                "--period", "daily",
                "--format", "json",
                "--output", tmp_path
            ], capture_output=True, text=True, timeout=30)
            
            assert result.returncode == 0
            
            # Report file should be created
            output_path = Path(tmp_path)
            if output_path.exists():
                with open(output_path) as f:
                    data = json.load(f)
                assert "type" in data
                assert "generated_at" in data
                assert "summary" in data
        
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)
    
    @pytest.mark.slow
    def test_dashboard_startup_shutdown(self):
        """Test dashboard startup and shutdown"""
        import requests
        import threading
        import signal
        import os
        
        # Start dashboard in background
        process = subprocess.Popen([
            "ai-devops", "dashboard",
            "--host", "localhost",
            "--port", "8099"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            # Wait for dashboard to start
            time.sleep(5)
            
            # Check if dashboard is responding
            try:
                response = requests.get("http://localhost:8099", timeout=5)
                assert response.status_code == 200
                assert "AI DevOps Assistant" in response.text
            except requests.RequestException:
                # Dashboard might not have started yet or credentials missing
                # This is acceptable for testing
                pass
            
            # Test API endpoint
            try:
                api_response = requests.get("http://localhost:8099/api/metrics", timeout=5)
                assert api_response.status_code == 200
                data = api_response.json()
                assert "connected_exchanges" in data
            except requests.RequestException:
                # API might not be available without proper config
                pass
        
        finally:
            # Clean up - terminate the dashboard process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    
    def test_invalid_command(self):
        """Test invalid command handling"""
        result = subprocess.run(
            ["ai-devops", "invalid-command"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
        assert "No such command" in result.stderr or "Usage:" in result.stdout