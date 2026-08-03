import unittest

from core.modules import AVAILABLE_MODULES, MODULE_REGISTRY, ModuleConfigurationError


class ModuleRegistryTests(unittest.TestCase):
    def test_existing_entities_keep_all_modules_enabled_by_default(self):
        self.assertEqual(MODULE_REGISTRY.enabled_modules({"id": "legacy"}), AVAILABLE_MODULES)

    def test_entity_a_configuration(self):
        entity = {"enabled_modules": ["faqs", "requests", "catalog", "customers"]}
        self.assertTrue(MODULE_REGISTRY.is_enabled(entity, "requests"))
        self.assertFalse(MODULE_REGISTRY.is_enabled(entity, "shopping"))

    def test_entity_b_configuration(self):
        entity = {"enabled_modules": ["faqs", "catalog", "shopping", "customers"]}
        self.assertFalse(MODULE_REGISTRY.is_enabled(entity, "requests"))
        self.assertTrue(MODULE_REGISTRY.is_enabled(entity, "shopping"))

    def test_unknown_module_is_rejected(self):
        with self.assertRaises(ModuleConfigurationError):
            MODULE_REGISTRY.enabled_modules({"enabled_modules": ["faqs", "invented"]})

    def test_invalid_configuration_shape_is_rejected(self):
        with self.assertRaises(ModuleConfigurationError):
            MODULE_REGISTRY.enabled_modules({"enabled_modules": "faqs"})


if __name__ == "__main__":
    unittest.main()
