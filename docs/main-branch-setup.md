# Setting Up `main` and Merging Phase 1 + Phase 2

A narrative walkthrough of how `main` was created and both feature branches (`phase-1-core-api`, `phase-2-identity-auth`) were merged into it via GitHub pull requests — including a real GitHub limitation hit along the way, why the first approach didn't work, and how it was fixed. Written as its own document rather than folded into `docs/decisions.md`, since the git mechanics here are involved enough to deserve a full explanation, not just a log entry.

**Context:** by the time this happened, both `phase-1-core-api` and `phase-2-identity-auth` already existed and were fully built — `phase-2-identity-auth` had been branched from `phase-1-core-api` early on and contained its full history, so it was already a complete superset of both phases' work. `main` itself had never been created — `git branch -a` confirmed only the two feature branches existed, locally and on the remote.

---

## 1. The goal, and why a PR over a direct push

The simplest option would have been creating `main` directly from `phase-2-identity-auth` (`git checkout -b main` + `git push`) — done in one step, no review process. **Chosen instead: merge via GitHub pull requests**, specifically because this is a portfolio/interview project — a PR gives a permanent, browsable page (title, full diff, description, merge timestamp) that's far more legible to someone skimming the repo for 90 seconds than digging through raw commit history would be. The extra few minutes of ceremony was judged worth it for that reason specifically; on a purely personal project with no audience, direct push would have been the simpler, equally valid choice.

**Further decision, once PRs were chosen:** merge *both* phases as separate PRs (Phase 1, then Phase 2), rather than merging only `phase-2-identity-auth` (which already contained Phase 1's history) and letting Phase 1 disappear into it silently. Two individually-reviewable PRs — one per phase — was judged the more complete, consistent portfolio artifact.

---

## 2. Attempt 1: a true orphan `main`

**Command sequence run:**
```bash
git checkout --orphan main
git status                          # confirmed all files staged (--orphan keeps the working directory)
git reset                           # unstaged everything, without touching any files on disk
git commit --allow-empty -m "Initial empty commit"
git push -u origin main
```

**Why this approach was chosen initially:** the reasoning was that `main` should start genuinely empty — no artificial content, a clean slate for both feature-branch PRs to merge into symmetrically. `--orphan` creates a branch with zero commit ancestry; `--allow-empty` lets you commit with nothing staged, since git normally refuses an empty commit.

**What `git reset` (without `--hard`) does here, specifically:** it unstages files from the index without touching the working directory at all — meaning nothing on disk gets deleted or modified. This mattered because `--orphan` had left every file from `phase-2-identity-auth` sitting there staged; committing at that point would have accidentally made `main` identical to `phase-2-identity-auth` instead of empty. `git reset` cleanly separated "what's on disk" from "what's about to be committed."

This part worked exactly as intended — `main` was pushed to GitHub as a genuinely empty branch (one commit, zero files).

---

## 3. The problem: GitHub refuses to show "Create pull request" for unrelated histories

Navigating to the compare page —
```
github.com/.../compare/main...phase-1-core-api
```
— showed:
```
There isn't anything to compare.
main and phase-1-core-api are entirely different commit histories.
```

Below that, a real file diff was shown (26 changed files) — but critically, **no "Create pull request" button appeared anywhere on the page.**

**Root cause, confirmed via research (not just inferred):** this is a genuine, documented GitHub web-UI limitation, not a bug or a misconfiguration — multiple independent reports of the exact same situation confirm it. When two branches share **zero common commit ancestry** ("unrelated histories," in git's own terminology), GitHub's compare view shows the "There isn't anything to compare... entirely different commit histories" banner and, in this repo's case, also displayed a file-level diff summary beneath it (26 changed files) — but **no "Create pull request" button appeared anywhere on the page regardless.** (Whether GitHub always shows a diff alongside that banner, or only does so in some circumstances, isn't fully consistent across reports found during research — but the PR-button absence itself is the consistently confirmed, load-bearing fact here, and it's what actually blocked us.) The underlying reason is that a normal merge relies on git being able to find a common ancestor to compute the merge; unrelated histories have none, and GitHub's web-based merge button has no equivalent of git's `--allow-unrelated-histories` command-line flag.

**Alternative considered and rejected: `git merge --allow-unrelated-histories` locally, then push directly to `main`, with no PR at all.** This is git's own supported way to force a merge across unrelated histories — and it would have worked technically. **Rejected** because it happens entirely on the command line with no PR involved at all, which defeats the entire reason PRs were chosen in section 1 — there would be nothing to click "Create pull request" on, ever, for either phase.

**A second real alternative, not used here but worth naming:** run `git merge origin/main --allow-unrelated-histories` **on the feature branch itself** (`phase-1-core-api`), then push that branch back to GitHub — at that point, the feature branch and `main` would share history via the new merge commit, and the compare page's PR button would appear normally. This genuinely works, and is arguably simpler than resetting `main`. **The trade-off that ruled it out here:** it permanently adds a merge commit into the feature branch's own history — `phase-1-core-api` (and separately, `phase-2-identity-auth`) would no longer be a clean, self-contained record of just that phase's work; it would also carry a commit merging in `main`. The approach actually used (resetting `main` to `db600b8`) never touched either feature branch at all — only the brand-new `main`, which had no other value riding on it yet, making it the lower-risk choice specifically in this situation.

---

## 4. The fix: start `main` from a real shared commit instead

**Key insight:** `phase-1-core-api` and `phase-2-identity-auth` already shared a real common ancestor — `db600b8`, Phase 1's very first commit (`git log --oneline` on both branches confirmed this identical commit at the tail of both histories, since `phase-2-identity-auth` had been branched from `phase-1-core-api` and never diverged). If `main` were reset to point at that same commit, instead of a fabricated empty one, GitHub would recognize normal shared ancestry — because there genuinely *is* shared ancestry — and PR creation would work correctly.

**Commands run:**
```bash
git checkout main
git reset --hard db600b8
git push --force origin main
```

- `git reset --hard db600b8` — moves `main`'s branch pointer to that specific commit, and (unlike the earlier plain `git reset`) also overwrites the working directory to match it exactly, discarding the empty-commit attempt entirely.
- `git push --force origin main` — a normal `git push` would have been rejected here, since GitHub's `main` (still pointing at the orphan empty commit) and the local `main` (now pointing at `db600b8`) share no history from git's perspective — the same "unrelated histories" problem, just from push's point of view instead of the PR UI's. `--force` overwrites GitHub's version unconditionally. This is safe specifically because `main` was brand new and nothing else depended on it yet — force-pushing to a branch other people are actively working from would be a much riskier move.

Retrying the compare page after this showed **"Able to merge"** and a working **"Create pull request"** button — confirming the fix.

---

## 5. A near-miss caught along the way: `secure-notes/` briefly untracked

While `main` was checked out at `db600b8` (during the fix above), `git status --ignored` showed something worth flagging: **`secure-notes/` appeared under "Untracked files," not "Ignored files."**

**Root cause:** `db600b8` is Phase 1's *very first* commit — it predates the commit that later added the root-level `.gitignore` (`755db27`, "restructure: move phase 1 into app/ subfolder, add root-level .gitignore"). Since `.gitignore` rules only apply as they exist *at the currently checked-out commit*, and this particular commit genuinely doesn't have that file yet, git had no rule telling it to ignore `secure-notes/` at that specific point in history.

**Why this mattered:** if a broad `git add -A` or `git add .` had been run while `main` was sitting at this exact point, `secure-notes/credentials-index.md` would have been staged with nothing stopping it — the exact scenario the whole `secure-notes/` convention exists to prevent.

**How it was avoided:** no broad `git add` was run during this window — the fix moved on directly to `git checkout phase-2-identity-auth` (which has the full, current `.gitignore`), and `secure-notes/` was confirmed back under "Ignored files" before any further work continued. Genuinely narrow miss, worth naming as a lesson: **when moving a branch pointer to an old historical commit, double-check `.gitignore` protection is actually in effect at that specific commit before running any staging command** — don't assume protection that exists on your usual working branch also exists at an arbitrary point in history.

---

## 6. Completing the merge

With `main` correctly pointing at `db600b8`:

1. **PR #1:** base `main`, compare `phase-1-core-api` → reviewed, merged
2. **PR #2:** base `main`, compare `phase-2-identity-auth` → opened *after* PR #1 merged (so it would show only Phase 2's genuine additions on top of Phase 1, not a redundant combined diff) → reviewed, merged

Both merges landed cleanly and in the correct order, confirmed via:
```bash
git checkout main
git pull
git log --oneline -5
```
showing `d5b7a22` (Merge PR #2) → `ae1d333` (Merge PR #1) → the full prior history beneath both.

## 7. Setting `main` as the default branch

GitHub's default branch (what visitors land on, and what a repo's README/badges implicitly refer to) was still set to `phase-1-core-api` after both merges — merging *into* `main` doesn't automatically make it the *default*. Changed via Settings → Branches in the browser.

**Verified from the command line afterward**, two ways:
```bash
gh repo view kuldeepjain1920/swift-devsecops-lab --json defaultBranchRef -q .defaultBranchRef.name
```
or, without needing `gh` installed at all (public repo, no auth needed):
```bash
curl -s https://api.github.com/repos/kuldeepjain1920/swift-devsecops-lab | python3 -c "import sys,json;print(json.load(sys.stdin)['default_branch'])"
```
**Note:** the `gh` command returned a stale cached value (`phase-1-core-api`) on its first run, then the correct updated value (`main`) on a second run moments later — worth knowing `gh` can serve a locally cached answer briefly after a change made in the browser.

---

## 8. Summary of lessons

- **GitHub cannot create a PR across genuinely unrelated commit histories, full stop** — this isn't a setting to change or a permission to grant; the only fixes are (a) don't create unrelated histories in the first place, or (b) merge locally with `--allow-unrelated-histories` and skip the PR entirely.
- **When you want a "clean start" branch that still needs to PR-merge with existing branches, start it from a real shared commit, not a true orphan** — an empty/orphan branch feels cleaner in the moment but actively breaks the GitHub PR workflow if any existing branch needs to merge into it later.
- **`.gitignore` protection is commit-specific, not global** — checking out an old commit can genuinely leave sensitive paths unprotected if that commit predates the `.gitignore` rule covering them. Worth an explicit `git status --ignored` check after any checkout to an unfamiliar or historical commit, before running any staging command.
- **`git reset` (no flag) vs. `git reset --hard`** — the former only touches the staging area; the latter also overwrites the working directory. Knowing which one to reach for prevented data loss twice in this process (once when un-staging the orphan branch's files, once when confirming `--hard` was the correct — and safe, since nothing there needed preserving — choice for pointing `main` at `db600b8`).
