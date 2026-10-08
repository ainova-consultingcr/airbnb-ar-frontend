/* Extension hooks that let AVI experiences contribute without coupling shared UI code. */
"use strict";

(function createExperienceExtensionRegistry(global) {
  const hooks = new Map();

  function register(hookName, extensionId, handler) {
    if (!hookName || typeof hookName !== "string") {
      throw new TypeError("hookName must be a non-empty string");
    }
    if (!extensionId || typeof extensionId !== "string") {
      throw new TypeError("extensionId must be a non-empty string");
    }
    if (typeof handler !== "function") {
      throw new TypeError("handler must be a function");
    }

    const extensions = hooks.get(hookName) || new Map();
    extensions.set(extensionId, handler);
    hooks.set(hookName, extensions);

    return function unregister() {
      extensions.delete(extensionId);
      if (extensions.size === 0) hooks.delete(hookName);
    };
  }

  function run(hookName, context = {}) {
    const extensions = hooks.get(hookName);
    if (!extensions) return [];

    const results = [];
    extensions.forEach((handler, extensionId) => {
      try {
        results.push(handler(context));
      } catch (error) {
        console.error(`AVI extension failed: ${hookName}/${extensionId}`, error);
      }
    });
    return results;
  }

  function has(hookName, extensionId) {
    return hooks.get(hookName)?.has(extensionId) === true;
  }

  global.AVIExperienceExtensions = Object.freeze({
    register,
    run,
    has
  });
})(typeof window !== "undefined" ? window : globalThis);
