# Session Continuation Template

When continuing a project, Claude should:

1. **Check Current State**
   - Review CLAUDE.md for project context
   - Check git status and recent commits
   - Identify uncommitted changes
   - Review any TODO comments in code

2. **Restore Context**
   - Load session state from .claude/session_state.json
   - Review recent conversation history
   - Identify the last task being worked on

3. **Verify Environment**
   - Ensure virtual environment is activated
   - Check if all dependencies are installed
   - Verify tests are passing

4. **Resume Work**
   - Continue from the last commit point
   - Address any uncommitted changes
   - Complete any unfinished tasks

## Session Workflow

1. **Start:** Check context and status
2. **Work:** Make changes, commit frequently
3. **Update:** Keep context.json current
4. **End:** Final commit with next steps

## Quick Status Commands

Ask Claude to run these when resuming:
- "What's the current project status?"
- "Show me recent changes and TODOs"
- "What was I working on last?"
- "Run tests and show me the results"
  
## Key Files to Update

- `CLAUDE.md` - Project description and requirements
- `.claude/context.json` - Current task and next steps
- `.claude/session_template` - How to continue the session (where you stopped, and where to start)
- Commit messages - What was done and what's next

## Remember
- Claude has no memory between sessions
- Git commits are your save points
- Context files help resume work
- Be specific about current state