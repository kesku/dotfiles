---
name: pr-review-guide
description: "Given a GitHub PR link, write a short guide for reading it: what the PR changes in plain words, logic vs test LOC, the files grouped into steps in reading order with the key symbols in each, the data flow, and the tests worth reading. Use when asked to help review, walk through, or explain how to read a PR."
---

# PR review guide

Turn a PR link into a guide that tells a reviewer where to start, what each
part of the diff does, and how the pieces connect. Every extra line makes it
less useful: when in doubt, cut. The skill reads and reports; it
does not comment on, approve or change the PR.

## 1. Gather

```bash
PR=<url>   # https://github.com/<owner>/<repo>/pull/<N>
gh pr view "$PR" --json title,body,files,baseRefName
gh pr diff "$PR"
```

Read the whole diff and the PR body. Open the base version of a file when the
diff alone does not say what changed for the product. A diff GitHub refuses
(over 300 files) is read from a fetched head instead (`git_fetch` `#<N>`, then
`git diff` against the merge-base).

## 2. Count logic LOC

Logic LOC is additions + deletions in files that are not tests, lockfiles or
generated code, rounded to the nearest 10. Compute it; never estimate it. It
is the only LOC figure the guide states:

```bash
REPO=$(echo "$PR" | sed -E 's#https://github.com/([^/]+/[^/]+)/pull/.*#\1#')
N=${PR##*/pull/}; N=${N%%[/?#]*}
gh api --paginate "repos/$REPO/pulls/$N/files?per_page=100" --jq '.[] | [.filename, .additions + .deletions] | @tsv' |
  awk -F'\t' '
    $1 ~ /(^|\/)(tests?|__tests__|__snapshots__|spec|specs|e2e|fixtures?|testdata)\// ||
    $1 ~ /([._-](test|spec|vitest)\.[^\/]+|\/test_[^\/]+\.py|_test\.(go|py|rs)|\.snap)$/ { t += $2; next }
    $1 ~ /(^|\/)(pnpm-lock\.yaml|package-lock\.json|yarn\.lock|bun\.lockb?|poetry\.lock|Cargo\.lock|uv\.lock|flake\.lock|project\.lock|go\.sum)$/ ||
    $1 ~ /(^|\/)generated\/|_pb2(_grpc)?\.pyi?$|\.pb\.go$|\.min\.js$/ { g += $2; next }
    { l += $2 }
    END { printf "~%d\n", int((l + 5) / 10) * 10 }'
```

If the diff holds a generated file the patterns miss (a file whose header says
it is generated, a checked-in fixture), move its lines out of logic by hand.

## 3. Write the guide

Exactly this shape. Markdown, no preamble or closing line.

```
**How to read [PR <N>](<url>)**

It makes <k> changes. <one plain sentence per change>. ~<logic> lines of
logic. Paths below are under `<common prefix>/` unless they say otherwise.

**Reading order**

1. **<what this step is about>:** `file-a.ts`, then `file-b.ts`
   - <what a named symbol now does, one short sentence>
2. **<next concept>:** `tool.ts` → `run.ts` `functionName`
   - ...

**Data flow**
`<entry> → <hop> → <new hop> → ... → <exit>`

**Tests worth reading**
- `<file>`: <what it covers>

<optional: one oddity worth a glance>
```

Rules:

- **Intro**: count the PR's distinct changes and say each in one plain
  sentence a newcomer understands. Then `~N lines of logic` (step 2; no other
  line counts anywhere), then the shared path prefix so the steps can use
  short paths.
- **Steps** are concepts, not files. Name each step for what it is about
  ("Storing attachments in Files", "The beta flag", "Running a card"); group
  the files that implement it, in the order to read them, with `→` for a
  call chain (`tool.ts` → `agent-run.ts` `runAgentAsUser`).
- **Order** the steps as a request travels: storage and contracts first, then
  the gate or decision, then the path that uses it, then error handling, then
  the UI or other consumers.
- **Sub-bullets**: one or two per step, each one short sentence naming the
  real function, type, constant or flag in backticks and saying what it does
  now. Spend them only on behaviour a reviewer must check: the fallback, the
  retry, what counts as an error, what fails closed.
- **Length**: at most six steps; merge small ones. The whole guide fits in
  about 25 lines.
- **Plumbing** (env vars, packaging, deploy config, re-exports, a component
  that just uses a new one) goes in a sub-bullet of the step it serves, and
  says it is plumbing, in a few words.
- **Data flow**: one line of arrows from entry to exit, naming the gates and
  checks in order. Omit the section when the PR does not move data.
- **Tests worth reading**: at most three, the ones that exercise the most of
  the change. Skip the rest.
- **Oddity**: at most one line, only for something you noticed while
  reading (an inconsistent import, a dead branch). Say whether you checked it.
  Omit it otherwise.
- Never repeat the PR body, list commits, praise, or give a verdict.
