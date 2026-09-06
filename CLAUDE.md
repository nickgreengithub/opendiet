# CLAUDE.md

Guidance for Claude Code working in this repository. The site itself is described in
[`README.md`](README.md); the reasoning behind how it is built is in [`DESIGN.md`](DESIGN.md).

## Reporting status

When you start working on something:

    curl "https://agents.openkanji.org/api/report?id=$CLAUDE_CODE_REMOTE_SESSION_ID&title=<the ask, a few words>&state=working"

When you finish, or need a decision from me:

    curl "https://agents.openkanji.org/api/report?id=$CLAUDE_CODE_REMOTE_SESSION_ID&state=done&msg=<what I should do next, up to 60 chars>"

Use `state=pending` instead of `done` if you're waiting on my decision.

`msg` is what I should do next: the decision to make, or the thing to test.

If `$CLAUDE_CODE_REMOTE_SESSION_ID` is unset (a local session, not Claude Code on the web),
skip this silently.

Titles and messages are prose, so they need encoding — `curl --get --data-urlencode` does it
without having to think about spaces and punctuation.
