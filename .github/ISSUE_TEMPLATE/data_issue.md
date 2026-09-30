---
name: Data issue
about: Report a data-quality problem found in a source or pipeline layer
title: "Data issue: "
labels: ""
assignees: ""
---

## Where

- Source / table:
- Layer: source / bronze / silver / integration / gold / analytics
- File, batch, or reporting period:

## What

Is this **observed** (you have evidence) or **suspected** (a hypothesis still to test)?

Describe the problem.

## Evidence

The query or check you ran, the affected record count and total count, and a few sample records.

## Impact

What could be wrong downstream if this is not handled?

## Proposed handling

Flag, quarantine, fail, or fix with a documented rule. Which one, and why?

## AI help

Rules: [Using AI](https://github.com/reached-hq/edu-access-intelligence/blob/main/CONTRIBUTING.md#using-ai). Tick one.

- [ ] No AI help
- [ ] AI helped, and it passed all four gates:
  - [ ] **Data:** only public or made-up data was shared; no keys, tokens, passwords, credentials, or personal information
  - [ ] **AI claims:** every fact from the AI was checked against a source I can link
  - [ ] **Output:** I checked the result myself; where there is something to run, it works, is safe to rerun, and can be traced
  - [ ] **Accountability:** I can explain every part without the AI and I answer for it

**What the AI did** (leave blank if no AI help):
