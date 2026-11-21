# PC connectivity development

- Develop the two-player USB mode in this directory; keep the standalone and unified projects intact.
- Use the existing standalone MEGALOVANIA chart and melody as the initial song. Keep the library extensible.
- Flash a separate micro:bit V2 MicroPython program using Chrome Python Editor; do not assume the board can hold the combined program.
- Transfer and verify the complete chart on each board before starting. Never claim hardware synchronization or memory capacity without device measurements.
- Keep P0/P1 for the joystick and the existing D-pad pin mapping. The PC owns audio; the board owns timing-sensitive judgment.
- Run desktop tests after changes, document hardware validation limits, and avoid committing audio caches or generated local data.



## Execution Efficiency — Batch Editing and Validation

**Primary principle: Work in coherent batches, not tiny edit-verify loops. Optimize for task completion speed while preserving correctness.**

### 1. Analyze First, Edit in Batches

* Inspect the relevant code and understand dependencies before editing.
* Form a concise internal implementation plan.
* Group related changes into coherent batches, preferably covering the complete feature or fix.
* Avoid repeatedly editing the same file in tiny increments.
* Prefer applying multiple related edits in one operation when practical.
* Do not reread files whose contents are already known unless they have changed or new information is needed.

### 2. Avoid Excessive Verification

* Do not run tests, builds, linters, or type checks after every small edit.
* Complete a coherent batch of changes before running verification.
* Use the following validation strategy:

  * Small changes: targeted checks only, when appropriate.
  * Medium changes: targeted tests after implementation.
  * Large changes: validate at meaningful milestones and perform broader verification at the end.
* Do not repeatedly run the same successful check without relevant changes.
* Reserve full test suites and full builds for cases where their coverage is justified or explicitly required.

### 3. Fix Related Issues Together

* When validation fails, collect and analyze the relevant errors before editing.
* Fix multiple related errors in one batch rather than one error per iteration.
* Rerun only the affected checks when possible.
* Expand verification scope if failures suggest wider regressions.

### 4. Minimize Tool Calls and Overhead

* Prefer targeted file searches over reading the entire repository.
* Combine related read operations and independent shell commands where practical.
* Avoid redundant status checks, repetitive planning, and unnecessary documentation.
* Do not create extra scripts, reports, or temporary files unless they materially help complete the task.
* Keep progress updates concise and only at meaningful milestones.

### 5. Autonomous Execution

* For routine, reversible code changes, proceed without asking for approval at every step.
* Make reasonable implementation decisions independently.
* Do not stop after each small milestone to request confirmation.
* Ask for clarification only when a missing decision materially affects correctness, scope, or safety.
* Preserve existing security, approval, and deployment boundaries.

### 6. Completion Criteria

* Deliver the requested behavior, not merely a partial implementation.
* Perform the minimum sufficient verification based on change risk and repository requirements.
* Report what changed, what was verified, and any remaining risks.
* Never claim tests passed unless they actually ran successfully.

**Default workflow: Inspect → Plan → Batch Edit → Targeted Verify → Fix if Needed → Finish.**

Avoid: Inspect → Edit One Line → Test → Edit One Line → Test → Repeat.
