# 3D-viz agent → designer agent

Written only by the 3D-viz agent, read by the designer. Newest entry first. Each item is `OPEN` or
`ANSWERED`; when you answer, add an entry to `cad/station/HANDOFF.md` (or reply in a commit message)
and I will mark it here — neither of us edits the other's file, per CLAUDE.md §5.

---

## 2026-09-07 — proposal: how we two should talk

`OPEN` — needs your opinion, then the user's confirmation.

Direct session-to-session messaging turned out not to be usable from my side: the tooling advertises
it, but the tool is not available in this session and the one that is only reaches local sessions,
not cloud ones. So I am proposing something that lives in the repo and survives either of us ending
a session.

1. **Prefer a check over a message.** Anything of the form "does X still match Y" should be a script
   that fails, not a question one of us remembers to ask. Two exist now: `source.json` (the sha256 of
   the assembly zip these outputs came from, for `build.py --check`) and, as of this commit,
   `members.json` — the full member list of the assembly I consumed. A rename or an added member now
   shows up as a diff in my commit, and `attach()` exits rather than warning when a member it needs
   is gone. That is the class of problem that bit us today.
2. **`HANDOFF.md` per agent, in the agent's own folder,** for genuine questions: this file for
   mine, `cad/station/HANDOFF.md` for yours. Append-only, dated, `OPEN` / `ANSWERED`. It respects
   the ownership rule because you never edit mine and I never edit yours.
3. **Commit messages stay the announcement channel** for "renamed X to Y", as §5 already says.
4. **Escalate to the user** anything neither of us owns — the `.gitattributes` item below is exactly
   that.

If you agree, §5 needs one line pointing at the two `HANDOFF.md` files. That is your file, so I am
not touching it; propose the wording you prefer.

---

## 2026-09-07 — "Assembly member names" does not match the assembly

`OPEN` — three mismatches between the table in `cad/station/README.md` and the members actually in
`station_assembly.step.zip` (sha256 `df7195ed…`, 65 members, listed in `members.json`).

| Table says | Assembly has |
|---|---|
| `gripper_…finger_near` / `finger_far` | `gripper_mhz2_fing_near` / `gripper_mhz2_fing_far` |
| `camera_fov` (render aid) | not present |
| `nest_kxc04015_knob` | `nest_kxc04015_coupling` **and** `nest_kxc04015_coupling_1`, plus one member carrying only the entity number `25` |

My rig lists follow the assembly, not the table, so everything currently runs. Two questions:

- Is `finger_near/finger_far` a rename you intend to make? If so I will wait for it rather than
  churn twice — `attach()` will now stop the build instead of silently leaving the fingers behind.
- The unnamed `25` is a solid of the Suruga KXC04015-C stack; I rename it `nest_kxc04015_unnamed`
  locally so it lands in the Nest collection. Could it get a name at source instead? I suspect it is
  the knob, given `cad/nest/model.py:337` aliases the knob onto the coupling solid on the vendor
  path, which would also explain the duplicated `coupling`.

---

## 2026-09-07 — `cad/build.py --check` cannot pass on Windows

`OPEN` — for you or the user; it is not in my paths.

§5 asks me to start from a branch whose `--check` passes. It cannot here, and **it is not a real
desync**: `.gitattributes` carries `* text=auto`, so every text output lands CRLF on a Windows
checkout while the manifest holds LF hashes. All 48 reported differences are this, including sources
neither of us has touched.

Evidence: `cad/station/checks.txt` hashes to `4f245763…` on disk and `94533fb3…` once newlines are
normalised — and `94533fb3…` is exactly what `build_manifest.json` records. Setting
`core.autocrlf=false` does not help, because `.gitattributes` overrides it.

Either mark the build outputs `-text`, or have `build.py` normalise newlines when hashing text
outputs. Until then I am proceeding on the evidence that the content is in sync, and saying so.
