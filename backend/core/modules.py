"""Central registry and per-entity activation policy for AVI modules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


AVAILABLE_MODULES = frozenset({"faqs", "requests", "shopping", "catalog", "customers"})


class ModuleConfigurationError(ValueError):
    """Raised when an entity references an unknown AVI module."""


class ModuleDisabledError(PermissionError):
    """Raised when an entity tries to use a disabled AVI module."""


class ModuleRegistry:
    def __init__(self, available_modules: Iterable[str] = AVAILABLE_MODULES):
        self._available_modules = frozenset(available_modules)

    @property
    def available_modules(self) -> frozenset[str]:
        return self._available_modules

    def enabled_modules(self, entity: Mapping) -> frozenset[str]:
        configured = entity.get("enabled_modules")
        if configured is None:
            return self._available_modules
        if not isinstance(configured, list) or any(not isinstance(name, str) for name in configured):
            raise ModuleConfigurationError("enabled_modules must be a list of module names")

        enabled = frozenset(configured)
        unknown = enabled - self._available_modules
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ModuleConfigurationError(f"Unknown AVI modules: {names}")
        return enabled

    def is_enabled(self, entity: Mapping, module_name: str) -> bool:
        self.validate_name(module_name)
        return module_name in self.enabled_modules(entity)

    def require_enabled(self, entity: Mapping, module_name: str) -> None:
        if not self.is_enabled(entity, module_name):
            entity_id = entity.get("id") or entity.get("entity_id") or "unknown"
            raise ModuleDisabledError(f"Module {module_name} is disabled for entity {entity_id}")

    def validate_name(self, module_name: str) -> None:
        if module_name not in self._available_modules:
            raise ModuleConfigurationError(f"Unknown AVI module: {module_name}")


def apply_module_configuration(entity: Mapping) -> dict:
    """Return entity data with disabled module content removed centrally."""
    configured = dict(entity)
    enabled = MODULE_REGISTRY.enabled_modules(configured)

    if "faqs" not in enabled:
        configured["faqs"] = []
    if "catalog" not in enabled:
        configured["catalog"] = []
        configured["offers"] = []
    if "requests" not in enabled:
        request_config = dict(configured.get("service_requests") or {})
        request_config["enabled"] = False
        configured["service_requests"] = request_config

    return configured


MODULE_REGISTRY = ModuleRegistry()
