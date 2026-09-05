# Day046 Landing Page Production Pipeline Design

## Goal

Extend the existing client-project workflow into a seven-agent landing-page
production chain that returns a reviewable delivery package in the Web UI.

## Pipeline

1. Research Agent gathers cited facts and identifies gaps.
2. Strategy Agent turns those facts into positioning, audience, offer, channels,
   and measurable goals.
3. Copywriting Agent writes landing-page copy using only confirmed inputs.
4. Web Design Agent defines page structure, hierarchy, responsive behavior, and
   acceptance criteria.
5. Coding Agent produces an implementation-ready code bundle in its response.
6. QA Agent reviews the proposed copy, design, and code and reports pass/fail,
   defects, and required changes.
7. Client Project Manager Agent summarizes scope, deliverables, risks, QA status,
   and next actions.

## Data Flow

Each step receives the original project context plus only the upstream outputs
needed for its task. The existing `TaskBrief`, router, executor, handler registry,
workflow result, history persistence, API, and Web UI remain unchanged.

## Failure Behavior

The workflow stops at the first failed Agent. The returned `WorkflowResult`
contains every completed step plus the failed step and identifies the failing
Agent in `error`.

## Delivery Boundary

Day046 stores and displays Agent outputs as a reviewable delivery package. It
does not write generated website files to disk and does not execute generated
code.

## Verification

- Update the successful workflow test for all seven Agents and data flow.
- Extend failure coverage to prove downstream Agents are skipped.
- Run the complete project verification and create a checkpoint.

