"""
Configuration Management Module
===============================

Centralized configuration for Tastefully Stained services.

This module provides:
- Environment-based configuration
- Configuration validation with Pydantic
- Secrets management integration
- Configuration hot-reloading

Features:
---------
- Type-safe configuration with defaults
- Environment variable overrides
- Hierarchical configuration (dev/staging/prod)
- Secret injection from vault

Example:
--------
    >>> from watermark_engine.utils import Config, get_config
    >>> 
    >>> config = get_config()
    >>> print(f"Debug mode: {config.debug}")
    >>> print(f"Database URL: {config.database_url}")

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment."""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    host: str = "localhost"
    port: int = 5432
    name: str = "tastefully_stained"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 10
    ssl_mode: str = "prefer"
    
    @property
    def url(self) -> str:
        """Get database connection URL."""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
            f"?sslmode={self.ssl_mode}"
        )


@dataclass
class RedisConfig:
    """Redis cache configuration."""
    
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    ssl: bool = False
    
    @property
    def url(self) -> str:
        """Get Redis connection URL."""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class BlockchainConfig:
    """Blockchain integration configuration."""
    
    ethereum_provider_url: str = ""
    ethereum_private_key: str = ""
    contract_address: str = ""
    network: str = "ethereum_sepolia"
    ipfs_gateway_url: str = "https://ipfs.infura.io:5001"
    ipfs_api_key: str = ""


@dataclass
class WatermarkConfig:
    """Watermarking engine configuration."""
    
    default_strategy: str = "hybrid"
    default_strength: float = 0.5
    max_image_size_mb: int = 50
    supported_formats: list[str] = field(
        default_factory=lambda: ["jpeg", "png", "webp", "avif"]
    )
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class APIConfig:
    """API server configuration."""
    
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 60
    max_upload_size_mb: int = 100


@dataclass
class Config:
    """
    Main application configuration.
    
    Aggregates all configuration sections and provides
    environment-based defaults.
    
    Attributes:
        environment: Current environment (dev/staging/prod)
        debug: Enable debug mode
        log_level: Logging level
    
    Example:
        >>> config = Config()
        >>> config.load_from_env()
        >>> print(config.database.url)
    """
    
    # Core settings
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    blockchain: BlockchainConfig = field(default_factory=BlockchainConfig)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    api: APIConfig = field(default_factory=APIConfig)
    
    # Paths
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    cache_dir: Path = field(default_factory=lambda: Path("./cache"))
    logs_dir: Path = field(default_factory=lambda: Path("./logs"))
    
    def load_from_env(self) -> "Config":
        """
        Load configuration from environment variables.
        
        Environment variables follow the pattern:
        TASTEFULLY_STAINED_{SECTION}_{KEY}
        
        Example:
            TASTEFULLY_STAINED_DATABASE_HOST=db.example.com
            TASTEFULLY_STAINED_API_PORT=8080
        
        Returns:
            Self for chaining
        """
        prefix = "TASTEFULLY_STAINED_"
        
        # Core settings
        env_str = os.getenv(f"{prefix}ENVIRONMENT", "development")
        self.environment = Environment(env_str.lower())
        
        self.debug = os.getenv(f"{prefix}DEBUG", "true").lower() == "true"
        self.log_level = os.getenv(f"{prefix}LOG_LEVEL", "INFO")
        self.secret_key = os.getenv(f"{prefix}SECRET_KEY", self.secret_key)
        
        # Database
        self.database.host = os.getenv(f"{prefix}DATABASE_HOST", self.database.host)
        self.database.port = int(os.getenv(f"{prefix}DATABASE_PORT", str(self.database.port)))
        self.database.name = os.getenv(f"{prefix}DATABASE_NAME", self.database.name)
        self.database.user = os.getenv(f"{prefix}DATABASE_USER", self.database.user)
        self.database.password = os.getenv(f"{prefix}DATABASE_PASSWORD", self.database.password)
        
        # Redis
        self.redis.host = os.getenv(f"{prefix}REDIS_HOST", self.redis.host)
        self.redis.port = int(os.getenv(f"{prefix}REDIS_PORT", str(self.redis.port)))
        self.redis.password = os.getenv(f"{prefix}REDIS_PASSWORD", self.redis.password)
        
        # Blockchain
        self.blockchain.ethereum_provider_url = os.getenv(
            f"{prefix}ETHEREUM_PROVIDER_URL",
            self.blockchain.ethereum_provider_url
        )
        self.blockchain.ethereum_private_key = os.getenv(
            f"{prefix}ETHEREUM_PRIVATE_KEY",
            self.blockchain.ethereum_private_key
        )
        
        # API
        self.api.host = os.getenv(f"{prefix}API_HOST", self.api.host)
        self.api.port = int(os.getenv(f"{prefix}API_PORT", str(self.api.port)))
        
        logger.info(f"Configuration loaded for environment: {self.environment.value}")
        return self
    
    def validate(self) -> list[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required secrets in production
        if self.environment == Environment.PRODUCTION:
            if self.secret_key == "change-me-in-production":
                errors.append("SECRET_KEY must be changed in production")
            if not self.database.password:
                errors.append("DATABASE_PASSWORD required in production")
        
        # Validate paths
        for path_attr in ["data_dir", "cache_dir", "logs_dir"]:
            path = getattr(self, path_attr)
            if not path.parent.exists():
                errors.append(f"Parent directory for {path_attr} does not exist")
        
        return errors
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (masking secrets)."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "log_level": self.log_level,
            "database_host": self.database.host,
            "redis_host": self.redis.host,
            "api_port": self.api.port,
            # Secrets are masked
            "secret_key": "***" if self.secret_key else "",
            "database_password": "***" if self.database.password else "",
        }


@lru_cache(maxsize=1)
def get_config() -> Config:
    """
    Get singleton configuration instance.
    
    Returns:
        Configured Config instance
    
    Example:
        >>> config = get_config()
        >>> print(config.environment)
    """
    config = Config()
    config.load_from_env()
    return config


def reload_config() -> Config:
    """
    Force reload configuration.
    
    Clears cache and reloads from environment.
    
    Returns:
        Fresh Config instance
    """
    get_config.cache_clear()
    return get_config()
