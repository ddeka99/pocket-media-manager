# AGENTS.md

This repository is being developed collaboratively with a strong emphasis on
keeping documentation current and useful for a non-specialist project owner.

## Primary Project Preference

Documentation quality is a first-class requirement.

When making relevant changes, always update the documentation in the same body
of work. Do not treat documentation as optional follow-up polish.

## Documentation Expectations

Whenever a meaningful change is introduced, update the appropriate README files
to reflect it. This includes changes to:

- user-visible features
- current limitations or known issues
- setup or run workflows
- how the Windows helper and iPhone app interact
- important stored data or behavior flow
- new scripts, commands, or operational steps

## Documentation Style

Prefer documentation that explains:

- what the feature does
- why it exists
- how a user experiences it
- how the major parts connect

Avoid excessive low-level code commentary unless it is needed to understand the
functional behavior of the system.

## Documentation Targets

- `README.md`
  Keep this as the high-level product and architecture overview.
- `pc-helper/README.md`
  Explain backend/helper behavior, routes, storage, scripts, and operator flow.
- `ios-app/README.md`
  Explain the iPhone app at a functional level and its relationship to the
  helper.

## Default Rule For Future Changes

If a change would make the current documentation even slightly misleading or out
of date, update the docs before considering the work complete.
