# AI Agent Instructions for IntentGuard

Welcome! As an AI coding assistant on this project, you must adhere strictly to these engineering guidelines to keep the codebase maintainable, reliable, and secure.

## Core Architectural Rules
1. **Separation of Concerns**: Keep the three primary layers—**Observer**, **Brain**, and **Actor**—in completely separate modules. 
2. **Logic Isolation**: Never mix classification logic (Brain) with intervention logic (Actor). The Brain should only evaluate state; the Actor should only execute interventions.
3. **Configuration & Secrets**: Never hardcode API keys or secrets. Always use `.env` files and load configurations securely.

## Workflow & Task Execution Rules
1. **Check Tasks Directory**: Always check the `tasks/` directory before starting any development. Read and follow the active task details.
2. **One Step at a Time**: Work incrementally. Implement a single feature, test it, verify it works, and only then proceed to the next step.
3. **Code Simple Before Elegant**: Write readable, straightforward, and working code first. Refactor for elegance only after correctness has been verified.
4. **No Destructive Deletions**: Never delete existing code or functionality without explaining your reasoning first.
5. **Dependency Management**: Never install external Python packages or frontend libraries without confirming with the user first.
6. **Blocker Management**: If you hit a blocker or need to note a future technical debt, append it immediately to `SCRATCH.md` under the appropriate section.
