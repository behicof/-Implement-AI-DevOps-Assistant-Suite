"""
Configuration manager for AI DevOps Assistant Suite
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import keyring


class ConfigManager:
    """Manages configuration for the AI DevOps Assistant"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_dir = Path.home() / ".ai_devops"
        self.config_dir.mkdir(exist_ok=True)
        
        if config_path:
            self.config_file = Path(config_path)
        else:
            self.config_file = self.config_dir / "config.yaml"
        
        self.secrets_file = self.config_dir / "secrets.enc"
        self._cipher_suite = None
        self._config_cache = None
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing config
        self._load_config()
    
    def _init_encryption(self):
        """Initialize encryption for sensitive data"""
        key_file = self.config_dir / ".key"
        
        if key_file.exists():
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            key_file.chmod(0o600)  # Secure permissions
        
        self._cipher_suite = Fernet(key)
    
    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self._config_cache = yaml.safe_load(f) or {}
        else:
            self._config_cache = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "version": "1.0.0",
            "general": {
                "debug": False,
                "log_level": "INFO",
                "data_dir": str(self.config_dir / "data"),
                "reports_dir": str(self.config_dir / "reports"),
                "feedback_dir": str(self.config_dir / "feedback"),
            },
            "github": {
                "api_base_url": "https://api.github.com",
                "timeout": 30,
                "max_retries": 3,
            },
            "exchanges": {
                "default_timeout": 30,
                "max_retries": 3,
                "rate_limit_delay": 1.0,
                "supported": [
                    "binance",
                    "coinbase",
                    "wallex",
                    "bitpin", 
                    "nobitex"
                ],
                "international": ["binance", "coinbase"],
                "iranian": ["wallex", "bitpin", "nobitex"]
            },
            "ai": {
                "default_provider": "openai",
                "default_model": "gpt-4",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60,
            },
            "monitor": {
                "default_interval": 60,
                "max_concurrent_monitors": 10,
                "enable_notifications": True,
                "notification_channels": ["console", "file"],
            },
            "dashboard": {
                "host": "localhost",
                "port": 8080,
                "debug": False,
                "auto_refresh_interval": 30,
                "theme": "light",
                "language": "en",
            },
            "analyzer": {
                "security_checks": True,
                "performance_analysis": True,
                "maintainability_checks": True,
                "exchange_specific_analysis": True,
                "max_file_size": 1048576,  # 1MB
                "supported_languages": [
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "go",
                    "rust",
                    "solidity"
                ]
            },
            "reports": {
                "default_format": "json",
                "include_charts": True,
                "retention_days": 30,
                "supported_formats": ["json", "html", "pdf", "csv"]
            }
        }
    
    def save_config(self):
        """Save configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, "w") as f:
            yaml.dump(self._config_cache, f, default_flow_style=False, indent=2)
    
    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration section or entire config"""
        if section:
            return self._config_cache.get(section, {})
        return self._config_cache
    
    def set_config(self, section: str, key: str, value: Any):
        """Set configuration value"""
        if section not in self._config_cache:
            self._config_cache[section] = {}
        
        self._config_cache[section][key] = value
        self.save_config()
    
    def get_github_config(self) -> Dict[str, Any]:
        """Get GitHub configuration"""
        config = self.get_config("github")
        
        # Add token from secure storage
        token = self.get_secret("github", "token")
        if token:
            config["token"] = token
            
        return config
    
    def get_exchange_config(self) -> Dict[str, Any]:
        """Get exchange configuration"""
        config = self.get_config("exchanges")
        
        # Add exchange credentials from secure storage
        for exchange in config.get("supported", []):
            creds = self.get_exchange_credentials(exchange)
            if creds:
                if "credentials" not in config:
                    config["credentials"] = {}
                config["credentials"][exchange] = creds
        
        return config
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        config = self.get_config("ai")
        
        # Add API keys from secure storage
        for provider in ["openai", "anthropic"]:
            api_key = self.get_secret("ai", f"{provider}_api_key")
            if api_key:
                if "credentials" not in config:
                    config["credentials"] = {}
                config["credentials"][provider] = {"api_key": api_key}
        
        return config
    
    def get_monitor_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.get_config("monitor")
    
    def get_analyzer_config(self) -> Dict[str, Any]:
        """Get analyzer configuration"""
        return self.get_config("analyzer")
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard configuration"""
        return self.get_config("dashboard")
    
    def get_reports_config(self) -> Dict[str, Any]:
        """Get reports configuration"""
        return self.get_config("reports")
    
    def set_secret(self, service: str, key: str, value: str):
        """Store secret securely"""
        secret_key = f"ai_devops_{service}_{key}"
        
        try:
            # Try to use system keyring first
            keyring.set_password("ai_devops", secret_key, value)
        except Exception:
            # Fallback to encrypted file storage
            self._store_secret_file(secret_key, value)
    
    def get_secret(self, service: str, key: str) -> Optional[str]:
        """Retrieve secret securely"""
        secret_key = f"ai_devops_{service}_{key}"
        
        try:
            # Try system keyring first
            secret = keyring.get_password("ai_devops", secret_key)
            if secret:
                return secret
        except Exception:
            pass
        
        # Fallback to encrypted file storage
        return self._get_secret_file(secret_key)
    
    def _store_secret_file(self, key: str, value: str):
        """Store secret in encrypted file"""
        secrets = {}
        
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file, "rb") as f:
                    encrypted_data = f.read()
                decrypted_data = self._cipher_suite.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data.decode())
            except Exception:
                pass
        
        secrets[key] = value
        
        encrypted_data = self._cipher_suite.encrypt(
            json.dumps(secrets).encode()
        )
        
        with open(self.secrets_file, "wb") as f:
            f.write(encrypted_data)
        
        self.secrets_file.chmod(0o600)  # Secure permissions
    
    def _get_secret_file(self, key: str) -> Optional[str]:
        """Get secret from encrypted file"""
        if not self.secrets_file.exists():
            return None
        
        try:
            with open(self.secrets_file, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_data = self._cipher_suite.decrypt(encrypted_data)
            secrets = json.loads(decrypted_data.decode())
            
            return secrets.get(key)
        except Exception:
            return None
    
    def set_exchange_credentials(self, exchange: str, api_key: str, api_secret: str, **kwargs):
        """Set exchange credentials"""
        self.set_secret("exchange", f"{exchange}_api_key", api_key)
        self.set_secret("exchange", f"{exchange}_api_secret", api_secret)
        
        # Store additional parameters (like passphrase for some exchanges)
        for key, value in kwargs.items():
            self.set_secret("exchange", f"{exchange}_{key}", str(value))
    
    def get_exchange_credentials(self, exchange: str) -> Optional[Dict[str, str]]:
        """Get exchange credentials"""
        api_key = self.get_secret("exchange", f"{exchange}_api_key")
        api_secret = self.get_secret("exchange", f"{exchange}_api_secret")
        
        if not api_key or not api_secret:
            return None
        
        credentials = {
            "api_key": api_key,
            "api_secret": api_secret
        }
        
        # Check for additional parameters
        for param in ["passphrase", "sandbox", "testnet"]:
            value = self.get_secret("exchange", f"{exchange}_{param}")
            if value:
                credentials[param] = value
        
        return credentials
    
    def setup_initial_config(self, github_token: str, exchanges: Dict[str, Dict[str, str]], 
                           ai_config: Dict[str, Dict[str, str]]):
        """Setup initial configuration from wizard"""
        # Store GitHub token
        self.set_secret("github", "token", github_token)
        
        # Store exchange credentials
        for exchange, creds in exchanges.items():
            api_key = creds.pop("api_key")
            api_secret = creds.pop("api_secret")
            self.set_exchange_credentials(exchange, api_key, api_secret, **creds)
        
        # Store AI credentials
        for provider, creds in ai_config.items():
            api_key = creds.get("api_key")
            if api_key:
                self.set_secret("ai", f"{provider}_api_key", api_key)
            
            # Update default model if specified
            model = creds.get("model")
            if model:
                self.set_config("ai", "default_model", model)
                self.set_config("ai", "default_provider", provider)
        
        # Save updated configuration
        self.save_config()
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration completeness"""
        validation_results = {
            "github": False,
            "exchanges": False,
            "ai": False,
            "config_file": self.config_file.exists()
        }
        
        # Check GitHub configuration
        github_token = self.get_secret("github", "token")
        validation_results["github"] = bool(github_token)
        
        # Check exchange configuration
        exchange_config = self.get_exchange_config()
        has_exchanges = False
        for exchange in exchange_config.get("supported", []):
            if self.get_exchange_credentials(exchange):
                has_exchanges = True
                break
        validation_results["exchanges"] = has_exchanges
        
        # Check AI configuration
        ai_openai = self.get_secret("ai", "openai_api_key")
        ai_anthropic = self.get_secret("ai", "anthropic_api_key")
        validation_results["ai"] = bool(ai_openai or ai_anthropic)
        
        return validation_results
    
    def get_data_dir(self) -> Path:
        """Get data directory path"""
        data_dir = Path(self.get_config("general").get("data_dir", str(self.config_dir / "data")))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def get_reports_dir(self) -> Path:
        """Get reports directory path"""
        reports_dir = Path(self.get_config("general").get("reports_dir", str(self.config_dir / "reports")))
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir
    
    def get_feedback_dir(self) -> Path:
        """Get feedback directory path"""
        feedback_dir = Path(self.get_config("general").get("feedback_dir", str(self.config_dir / "feedback")))
        feedback_dir.mkdir(parents=True, exist_ok=True)
        return feedback_dir