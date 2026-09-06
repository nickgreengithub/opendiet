# CLAUDE.md

Guidance for Claude Code working in this repository. The site itself is described in
[`README.md`](README.md); the reasoning behind how it is built is in [`DESIGN.md`](DESIGN.md).

## Reporting status

If `$CLAUDE_CODE_REMOTE_SESSION_ID` is unset — a local session rather than Claude Code on
the web — skip all of this silently.

**The title is always `opendiet.org`.** Not the task, not the fix, not the file you are in,
not a description of the conversation: the product. Send it with every call. It never
changes, so it cannot end up naming whatever was touched last.

Starting work, and again whenever you pick it back up:

    curl -sS --get "https://agents.openkanji.org/api/report" \
      --data-urlencode "id=$CLAUDE_CODE_REMOTE_SESSION_ID" \
      --data-urlencode "title=opendiet.org" \
      --data-urlencode "state=working"

Handing back to me — finished, blocked, or asking a question:

    curl -sS --get "https://agents.openkanji.org/api/report" \
      --data-urlencode "id=$CLAUDE_CODE_REMOTE_SESSION_ID" \
      --data-urlencode "title=opendiet.org" \
      --data-urlencode "state=done" \
      --data-urlencode "msg=<what I should do next, up to 60 chars>"

Use `state=pending` rather than `done` when you are waiting on my decision.

- `msg` is the only field that describes the work: the decision to make, or the thing to
  test. It is also what tells two sessions on this repo apart, since the title cannot.
- Nothing secret in `msg` — it travels in a URL, and in someone's logs.
- If the call fails, carry on. Don't retry it, don't mention it.
- Skip the whole thing for questions you answer without touching the repo.
