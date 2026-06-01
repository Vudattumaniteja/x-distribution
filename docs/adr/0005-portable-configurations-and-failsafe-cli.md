# 0005: Portable Configurations and Fail-safe CLI Routing

## Status
Proposed

## Context
The original configuration structure hardcoded machine-specific absolute file paths directly inside the shared `config/source_registry.json` file. This pattern broke codebase locality and prevented portability when running the codebase across different environments. Additionally, the routing implementation lacked a robust seam to resolve relative locations cleanly. Finally, the post generation module required strict validation to ensure that editorial drafting conforms to fail-safe standards, preventing automated publication of unverified copy.

## Decision
To address these challenges, we made the following architectural changes:
1. **Decouple Configuration Layers**: We separated operational settings from machine-specific settings. Operational configuration remains in `config/source_registry.json`, while runtime execution paths are moved to a local `config/runtime_paths.json` module layer.
2. **Relative Path Locality**: We updated the CLI adapter implementation (`scripts/source_clis.py`) to leverage relative resolution. Any configured relative paths are resolved dynamically using a deep seam relative to the workspace root.
3. **Fail-safe Drafting Interface**: We hardened the implementation in `scripts/generated_codegen.py`. The interface strictly filters items against `ALLOWED_VERDICTS` using deep checks on the fact-checking status, maintaining a clean seam where the generated post copy text remains empty (`""`) to force manual oversight.
4. **Shallow Schema Validation**: We updated the validation module (`scripts/validate_schemas.py`) to verify the merged configuration structure across both layers, ensuring safety and compliance without violating locality.

## Consequences
- Codebase portability is restored; developers can run the system on different machines by leveraging a local config layer.
- Operational and runtime environments are cleanly decoupled.
- The editorial drafting pipeline conforms to strict fail-safe standards.
