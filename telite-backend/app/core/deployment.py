"""
Deployment validation and safety checks.

This module provides utilities for validating deployment readiness
and ensuring safe production deployments.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from app.core.runtime import is_production_like

logger = logging.getLogger("telite.deployment")


def update_http_metrics(requests_total: int, errors_total: int) -> None:
    """Compatibility helper for app startup and request middleware metrics sync."""
    from app.core.health import update_http_metrics as _update_http_metrics

    _update_http_metrics(requests_total, errors_total)


def validate_environment_variables() -> dict[str, Any]:
    """
    Validate critical environment variables.
    
    Returns validation results for each required variable.
    In production, missing critical variables will cause deployment failure.
    """
    results = {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "is_production": is_production_like(),
        "variables": {},
        "critical_errors": [],
        "warnings": [],
    }
    
    # Critical variables for production
    critical_vars = {
        "TELITE_AUTH_SECRET": {
            "required_in_production": True,
            "min_length": 32,
            "description": "JWT signing secret",
        },
        "TELITE_PASSWORD_SALT": {
            "required_in_production": True,
            "min_length": 16,
            "description": "Password hashing salt",
        },
    }
    
    # Required variables for all environments
    required_vars = {
        "TELITE_POSTGRES_HOST": {
            "required_in_production": True,
            "description": "Database host",
        },
        "TELITE_POSTGRES_PORT": {
            "required_in_production": True,
            "description": "Database port",
        },
        "TELITE_POSTGRES_DB": {
            "required_in_production": True,
            "description": "Database name",
        },
        "TELITE_POSTGRES_USER": {
            "required_in_production": True,
            "description": "Database user",
        },
        "TELITE_POSTGRES_PASSWORD": {
            "required_in_production": True,
            "description": "Database password",
        },
    }
    
    # Check critical variables
    for var_name, config in critical_vars.items():
        value = os.getenv(var_name, "").strip()
        is_valid = True
        error = None
        
        if results["is_production"] and config["required_in_production"]:
            if not value:
                is_valid = False
                error = f"{var_name} is required in production"
                results["critical_errors"].append(error)
            elif config.get("min_length") and len(value) < config["min_length"]:
                is_valid = False
                error = f"{var_name} must be at least {config['min_length']} characters"
                results["critical_errors"].append(error)
        
        results["variables"][var_name] = {
            "set": bool(value),
            "valid": is_valid,
            "error": error,
            "description": config["description"],
        }
    
    # Check required variables
    for var_name, config in required_vars.items():
        value = os.getenv(var_name, "").strip()
        is_valid = True
        error = None
        
        if results["is_production"] and config["required_in_production"]:
            if not value:
                is_valid = False
                error = f"{var_name} is required in production"
                results["critical_errors"].append(error)
        
        results["variables"][var_name] = {
            "set": bool(value),
            "valid": is_valid,
            "error": error,
            "description": config["description"],
        }
    
    # Optional variables with warnings
    optional_vars = {
        "REDIS_HOST": "Redis host for caching",
        "REDIS_PORT": "Redis port",
        "STORAGE_PROVIDER": "Storage provider (local/s3)",
    }
    
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name, "").strip()
        if not value:
            results["warnings"].append(f"{var_name} ({description}) is not set")
        
        results["variables"][var_name] = {
            "set": bool(value),
            "valid": True,
            "error": None,
            "description": description,
        }
    
    return results


def validate_deployment_readiness() -> tuple[bool, dict[str, Any]]:
    """
    Validate overall deployment readiness.
    
    Returns:
        Tuple of (is_ready, validation_results)
        is_ready: True if deployment can proceed
        validation_results: Detailed validation results
    """
    validation = validate_environment_variables()
    
    if validation["critical_errors"]:
        logger.error("Deployment validation failed with critical errors:")
        for error in validation["critical_errors"]:
            logger.error(f"  - {error}")
        return False, validation
    
    if validation["warnings"]:
        logger.warning("Deployment validation warnings:")
        for warning in validation["warnings"]:
            logger.warning(f"  - {warning}")
    
    logger.info("Deployment validation passed")
    return True, validation


def fail_deployment_if_invalid() -> None:
    """
    Fail deployment if validation fails.
    
    This function is called during application startup to ensure
    that critical configuration is valid before the application starts.
    """
    is_ready, validation = validate_deployment_readiness()
    
    if not is_ready:
        logger.error("CRITICAL: Deployment validation failed. Application cannot start.")
        logger.error("Please fix the configuration errors above and retry deployment.")
        sys.exit(1)
    
    logger.info("Deployment validation successful. Application can start.")