---
name: Source candidate
about: Propose a dataset for inventory and profiling
title: "Source candidate: "
labels: ""
assignees: ""
---

A candidate is not a useful source until it has been acquired, inventoried, and profiled.

## Source

- Name:
- Publisher / agency:
- URL or acquisition method:
- Format (as published):

## Why it might matter

Which stakeholder decision or analytical need could it inform? Mark each point as **documented**, **mentor-validated**, or **assumed**.

## What we expect it to contain (UNVERIFIED)

Expected grain, geographic level, years covered, and join keys. All of these are guesses until profiling confirms them.

## Access and licensing

Can we access it? Are we allowed to use it? Should we use it?

## Next step

- [ ] Acquire the file and record its origin
- [ ] Create `docs/source_inventory/<source_id>/README.md` from the template and add the source to `config/sources.json`
- [ ] Profile it in `docs/source_inventory/<source_id>/profile.md`
- [ ] Generate `docs/source_inventory/<source_id>/data_dictionary.md` with a script in `notebooks/profiling/`

## AI help

Rules: [Using AI](https://github.com/reached-hq/edu-access-intelligence/blob/main/CONTRIBUTING.md#using-ai). Tick one.

- [ ] No AI help
- [ ] AI helped, and it passed all four gates:
  - [ ] **Data:** only public or made-up data was shared; no keys, tokens, passwords, credentials, or personal information
  - [ ] **AI claims:** every fact from the AI was checked against a source I can link
  - [ ] **Output:** I checked the result myself; where there is something to run, it works, is safe to rerun, and can be traced
  - [ ] **Accountability:** I can explain every part without the AI and I answer for it

**What the AI did** (leave blank if no AI help):
