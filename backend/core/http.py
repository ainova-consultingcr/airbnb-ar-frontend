from fastapi import HTTPException

from core.modules import MODULE_REGISTRY, ModuleConfigurationError, ModuleDisabledError
from rag import load_property_data


def require_entity_module(entity_id: str, module_name: str) -> dict:
    """Load an entity and enforce module activation for an HTTP request."""
    try:
        entity = load_property_data(entity_id)
        MODULE_REGISTRY.require_enabled(entity, module_name)
        return entity
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Property not found")
    except ModuleDisabledError as error:
        raise HTTPException(status_code=403, detail=str(error))
    except ModuleConfigurationError as error:
        raise HTTPException(status_code=500, detail=str(error))
