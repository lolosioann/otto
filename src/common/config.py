"""
Configuration management for OTTO orchestration system.

This module uses Pydantic Settings for environment-based configuration with
support for .env files. Configuration is organized into logical sections:
- Docker settings
- MQTT broker settings
- Monitoring settings
- NFR default thresholds
- Migration settings

Environment variables can be prefixed with OTTO_ (e.g., OTTO_LOG_LEVEL).
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DockerSettings(BaseSettings):
    """
    Docker daemon connection settings.

    Parameters
    ----------
    docker_host : str, optional
        Docker daemon URL (default: unix:///var/run/docker.sock)
    docker_tls_verify : bool
        Enable TLS verification
    docker_cert_path : Path, optional
        Path to TLS certificates

    Environment Variables
    ---------------------
    DOCKER_HOST : str
        Override Docker daemon URL
    DOCKER_TLS_VERIFY : bool
        Enable TLS
    DOCKER_CERT_PATH : str
        TLS certificate path

    Examples
    --------
    >>> config = DockerSettings()
    >>> config.docker_host
    'unix:///var/run/docker.sock'
    >>> config = DockerSettings(docker_host="tcp://localhost:2375")
    >>> config.docker_host
    'tcp://localhost:2375'
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    docker_host: str = Field(
        default="unix:///var/run/docker.sock",
        description="Docker daemon URL",
    )
    docker_tls_verify: bool = Field(default=False, description="Enable TLS verification")
    docker_cert_path: Path | None = Field(None, description="TLS certificate path")

    @field_validator("docker_host")
    @classmethod
    def validate_docker_host(cls, v: str) -> str:
        """Validate Docker host URL format."""
        valid_schemes = ("unix://", "tcp://", "http://", "https://")
        if not any(v.startswith(scheme) for scheme in valid_schemes):
            raise ValueError(f"Docker host must start with one of: {valid_schemes}. Got: {v}")
        return v


class MQTTSettings(BaseSettings):
    """
    MQTT broker connection settings.

    Parameters
    ----------
    mqtt_broker_url : str
        MQTT broker URL (e.g., "mqtt://localhost:1883")
    mqtt_username : str, optional
        MQTT username
    mqtt_password : str, optional
        MQTT password
    mqtt_client_id_prefix : str
        Prefix for MQTT client IDs
    mqtt_qos : int
        Quality of Service level (0, 1, or 2)
    mqtt_keepalive : int
        Keepalive interval in seconds

    Environment Variables
    ---------------------
    MQTT_BROKER_URL : str
        MQTT broker URL
    MQTT_USERNAME : str
        MQTT username
    MQTT_PASSWORD : str
        MQTT password (sensitive)
    MQTT_QOS : int
        QoS level

    Examples
    --------
    >>> config = MQTTSettings(mqtt_broker_url="mqtt://broker:1883")
    >>> config.mqtt_qos
    1
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    mqtt_broker_url: str = Field(
        default="mqtt://localhost:1883",
        description="MQTT broker URL",
    )
    mqtt_username: str | None = Field(None, description="MQTT username")
    mqtt_password: str | None = Field(None, description="MQTT password")
    mqtt_client_id_prefix: str = Field(default="otto", description="Client ID prefix")
    mqtt_qos: Literal[0, 1, 2] = Field(default=1, description="Quality of Service")
    mqtt_keepalive: int = Field(default=60, ge=10, le=3600, description="Keepalive (s)")

    @field_validator("mqtt_broker_url")
    @classmethod
    def validate_mqtt_url(cls, v: str) -> str:
        """Validate MQTT broker URL format."""
        valid_schemes = ("mqtt://", "mqtts://", "ws://", "wss://")
        if not any(v.startswith(scheme) for scheme in valid_schemes):
            raise ValueError(f"MQTT URL must start with one of: {valid_schemes}. Got: {v}")
        return v


class MonitoringSettings(BaseSettings):
    """
    Monitoring and metrics collection settings.

    Parameters
    ----------
    monitoring_interval_seconds : int
        Interval between metric collections (seconds)
    metrics_publish_interval_seconds : int
        Interval between MQTT metric publications (seconds)
    heartbeat_interval_seconds : int
        Interval between heartbeat messages (seconds)
    heartbeat_timeout_seconds : int
        Timeout before marking node unhealthy (seconds)
    nfr_grace_period_seconds : int
        Grace period before triggering NFR violation (seconds)

    Environment Variables
    ---------------------
    MONITORING_INTERVAL_SECONDS : int
        Metric collection interval
    HEARTBEAT_INTERVAL_SECONDS : int
        Heartbeat interval
    HEARTBEAT_TIMEOUT_SECONDS : int
        Heartbeat timeout

    Examples
    --------
    >>> config = MonitoringSettings()
    >>> config.monitoring_interval_seconds
    5
    >>> config.heartbeat_timeout_seconds
    90
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    monitoring_interval_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Metric collection interval",
    )
    metrics_publish_interval_seconds: int = Field(
        default=10,
        ge=1,
        le=300,
        description="Metrics publish interval",
    )
    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Heartbeat interval",
    )
    heartbeat_timeout_seconds: int = Field(
        default=90,
        ge=10,
        le=600,
        description="Heartbeat timeout",
    )
    nfr_grace_period_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="NFR violation grace period",
    )

    @field_validator("heartbeat_timeout_seconds")
    @classmethod
    def validate_heartbeat_timeout(cls, v: int, info: any) -> int:
        """Ensure timeout is greater than interval."""
        if "heartbeat_interval_seconds" in info.data:
            interval = info.data["heartbeat_interval_seconds"]
            if v <= interval:
                raise ValueError(f"Heartbeat timeout ({v}s) must be > interval ({interval}s)")
        return v


class NFRDefaultSettings(BaseSettings):
    """
    Default NFR thresholds.

    Parameters
    ----------
    default_max_cpu_percent : float
        Default max CPU utilization %
    default_max_memory_percent : float
        Default max memory utilization %
    default_max_latency_ms : float
        Default max latency (ms)
    default_min_availability : float
        Default min availability (0-1)

    Environment Variables
    ---------------------
    DEFAULT_MAX_CPU_PERCENT : float
        Default CPU threshold
    DEFAULT_MAX_MEMORY_PERCENT : float
        Default memory threshold

    Examples
    --------
    >>> config = NFRDefaultSettings()
    >>> config.default_max_cpu_percent
    80.0
    >>> config.default_min_availability
    0.99
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    default_max_cpu_percent: float = Field(
        default=80.0,
        ge=0,
        le=100,
        description="Default max CPU %",
    )
    default_max_memory_percent: float = Field(
        default=85.0,
        ge=0,
        le=100,
        description="Default max memory %",
    )
    default_max_latency_ms: float = Field(
        default=100.0,
        gt=0,
        description="Default max latency (ms)",
    )
    default_min_availability: float = Field(
        default=0.99,
        ge=0.0,
        le=1.0,
        description="Default min availability",
    )


class MigrationSettings(BaseSettings):
    """
    Migration strategy and behavior settings.

    Parameters
    ----------
    migration_strategy : str
        Default migration strategy ("simple_stop_start", "export_import", "criu_checkpoint")
    migration_timeout_seconds : int
        Maximum time for migration (seconds)
    migration_cooldown_seconds : int
        Minimum time between migrations of same container (seconds)
    enable_migration_rollback : bool
        Enable automatic rollback on migration failure

    Environment Variables
    ---------------------
    MIGRATION_STRATEGY : str
        Default migration strategy
    MIGRATION_TIMEOUT_SECONDS : int
        Migration timeout
    ENABLE_MIGRATION_ROLLBACK : bool
        Enable rollback

    Examples
    --------
    >>> config = MigrationSettings()
    >>> config.migration_strategy
    'simple_stop_start'
    >>> config.migration_timeout_seconds
    300
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    migration_strategy: Literal["simple_stop_start", "export_import", "criu_checkpoint"] = Field(
        default="simple_stop_start",
        description="Default migration strategy",
    )
    migration_timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Migration timeout",
    )
    migration_cooldown_seconds: int = Field(
        default=60,
        ge=0,
        le=3600,
        description="Migration cooldown period",
    )
    enable_migration_rollback: bool = Field(
        default=True,
        description="Enable rollback on failure",
    )


class LoggingSettings(BaseSettings):
    """
    Logging configuration.

    Parameters
    ----------
    log_level : str
        Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    log_format : str
        Log format ("json", "console")
    log_file : Path, optional
        Log file path (None for stdout only)

    Environment Variables
    ---------------------
    LOG_LEVEL : str
        Logging level
    LOG_FORMAT : str
        Log format
    LOG_FILE : str
        Log file path

    Examples
    --------
    >>> config = LoggingSettings()
    >>> config.log_level
    'INFO'
    >>> config.log_format
    'json'
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "console"] = Field(
        default="json",
        description="Log format",
    )
    log_file: Path | None = Field(None, description="Log file path")


class OTTOConfig(BaseSettings):
    """
    Main OTTO configuration aggregating all settings.

    Parameters
    ----------
    docker : DockerSettings
        Docker configuration
    mqtt : MQTTSettings
        MQTT configuration
    monitoring : MonitoringSettings
        Monitoring configuration
    nfr_defaults : NFRDefaultSettings
        NFR default thresholds
    migration : MigrationSettings
        Migration configuration
    logging : LoggingSettings
        Logging configuration

    Examples
    --------
    >>> config = OTTOConfig()
    >>> config.docker.docker_host
    'unix:///var/run/docker.sock'
    >>> config.mqtt.mqtt_qos
    1
    >>> config.monitoring.monitoring_interval_seconds
    5

    Using environment variables:
    >>> import os
    >>> os.environ["MQTT_BROKER_URL"] = "mqtt://broker:1883"
    >>> os.environ["LOG_LEVEL"] = "DEBUG"
    >>> config = OTTOConfig()
    >>> config.mqtt.mqtt_broker_url
    'mqtt://broker:1883'
    >>> config.logging.log_level
    'DEBUG'
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="OTTO_",
    )

    docker: DockerSettings = Field(default_factory=DockerSettings)
    mqtt: MQTTSettings = Field(default_factory=MQTTSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    nfr_defaults: NFRDefaultSettings = Field(default_factory=NFRDefaultSettings)
    migration: MigrationSettings = Field(default_factory=MigrationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


# =============================================================================
# Convenience functions
# =============================================================================


def load_config(env_file: Path | str | None = None) -> OTTOConfig:
    """
    Load OTTO configuration from environment and optional .env file.

    Parameters
    ----------
    env_file : Path or str, optional
        Path to .env file (default: .env in current directory)

    Returns
    -------
    OTTOConfig
        Loaded configuration

    Examples
    --------
    >>> config = load_config()
    >>> config.docker.docker_host
    'unix:///var/run/docker.sock'

    >>> config = load_config(env_file="/path/to/.env")
    >>> config.mqtt.mqtt_broker_url
    'mqtt://custom-broker:1883'
    """
    if env_file:
        # Create config with explicit env_file
        return OTTOConfig(
            docker=DockerSettings(_env_file=str(env_file)),
            mqtt=MQTTSettings(_env_file=str(env_file)),
            monitoring=MonitoringSettings(_env_file=str(env_file)),
            nfr_defaults=NFRDefaultSettings(_env_file=str(env_file)),
            migration=MigrationSettings(_env_file=str(env_file)),
            logging=LoggingSettings(_env_file=str(env_file)),
        )
    return OTTOConfig()
