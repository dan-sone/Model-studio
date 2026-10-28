# Development instructions

## Product intent

Build a real AI modeling assistant, not a drawing tool or command editor. The user speaks Swedish and uses ordinary language without memorizing syntax. Model Studio is a web app intended for Mac, iPad and mobile.

## Requirements

- Use actual AI inference through a server-side integration. Never replace it with regex commands, keyword matching, canned responses or silent demo fallback.
- Provide relevant current model state and conversation context to the AI. Bound input and context size.
- Ask for clarification when ambiguity materially affects the model. Clarification must not mutate the model.
- Separate application logic, model content and diagram rendering/layout. Do not hardcode Order to Cash into the modeling engine.
- Use stable object IDs and explicit typed relations. Preserve IDs for existing objects during edits.
- Validate AI output server-side before application: schema, allowed types, unique IDs, referential integrity and operation preconditions. Invalid output leaves the prior model intact.
- Apply changes atomically against a base version. Prevent stale and duplicate requests from overwriting newer work.
- Support visible change summaries, version history and undo.
- Distinguish proposed knowledge from verified facts, especially system functionality.
- Automatically lay out diagrams, including decision branches, without manual drawing.
- Keep API credentials server-side and out of source, browser code, logs and generated artifacts.
- Do not claim full ArchiMate or BPMN compliance without implementing and validating the relevant metamodel and constraints.

## Working approach

Read README.md and docs/implementation-plan.md first. Inspect the environment before choosing dependencies. Prefer a small end-to-end implementation over extensive scaffolding. Document the selected architecture and setup.

Use GitHub as the source of truth. Develop implementation work on a branch and provide a reviewable pull request. Do not require local development on the user's Mac. Do not add the discarded command-based prototype.

Consult current official documentation for API and library choices. Prefer provider-supported structured outputs and validate independently. Treat AI suggestions about Dynamics 365 F&O as assumptions unless backed by applicable verified sources.

If an AI credential or hosting configuration is missing, continue independent implementation and checks, then explain the exact remaining setup. Never present an unconnected app as working AI.

## Verification

Test meaningful behavior: free-language creation, contextual revision, identity preservation, branching, referential integrity, clarification without mutation, atomic rejection of invalid output, stale-response protection and undo. Mock provider responses only for deterministic tests; do not use mocks in production. Verify live inference separately when configured.

Use Swedish UI text with clear loading, error, retry and unconfigured states. Report what works, how it was verified and remaining limitations.
