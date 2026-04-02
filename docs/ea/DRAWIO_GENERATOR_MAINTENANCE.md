# Draw.io Generator Maintenance Notes

## Purpose

This note captures the current working agreement for maintaining the draw.io generator.
It is intentionally pragmatic. The goal is to preserve the existing behavior and accumulated
diagram-tuning knowledge while making the codebase safer to evolve.

## Current Assessment

The draw.io generator has become large and fairly tangled, especially in the `hub_spoke`
path used by landscape diagrams.

This does **not** mean the underlying diagramming rules are inherently complex.
Most of the requested behaviors are generic and sensible:

- edges should leave and enter shapes perpendicularly
- routed lines should stay outside boxes
- containers should reserve space for dominant or spanning nodes
- alignment and spacing should be predictable
- labels and annotations should not fight with core shapes

These are normal diagramming principles. If implementing them feels convoluted, that is
primarily a generator design issue rather than a problem with the principles themselves.

## Important Conclusion

We do **not** want a rewrite or a new simplified layout approach at this stage.

Reasons:

- the current generator already encodes a lot of learned behavior
- a rewrite would likely lose visual tuning that has been achieved through iteration
- the cost of re-validating all diagrams would be high
- regression risk would be unacceptable for a mostly working internal tool

So the correct stance is:

- preserve the current layout approach
- preserve current outputs wherever possible
- improve maintainability incrementally

## Working Strategy

### What we will do

- keep the current generator as the baseline engine
- continue fixing regenerable issues at the source
- add small, explicit YAML-driven controls when a view truly needs them
- extract helpers and modules only when output behavior can be preserved
- refactor one slice at a time

### What we will not do

- no rewrite of the draw.io layout engine
- no new replacement layout model
- no “clean slate” simplification that forces all existing diagrams through a new interpretation

## Refactor Principle

Refactoring is allowed only under this constraint:

> behavior preservation comes first; code cleanliness is secondary

That means:

1. establish the current output as the baseline
2. move logic into helpers without intending visual change
3. only then add narrowly-scoped new capabilities

## Preferred Refactor Order

If refactoring is undertaken, use this order:

1. extract edge routing helpers
2. extract annotation and text-box embedding helpers
3. extract hub-spoke subgroup placement helpers
4. extract external-group placement helpers
5. introduce small declarative placement controls

This order is deliberate. Edge routing and annotation handling are easier to isolate than a
full layout rewrite and offer immediate clarity benefits.

## Why the Code Feels Convoluted

The main problem is not line count by itself. The main problem is mixed responsibilities in
one module and, in some paths, one method.

Today the generator effectively mixes:

- element enrichment
- color selection
- layout policy
- coordinate calculation
- routing policy
- draw.io XML assembly
- annotation placement
- post-layout normalization

That is why simple visual intentions can require invasive edits.

## Recommended Design Direction

This is **not** a rewrite plan. It is a maintenance direction for the existing engine.

Over time, the code should move toward clearer separation between:

- layout-specific engines: `hub_spoke`, `matrix`, `flow_left_right`
- shared routing helpers
- shared annotation helpers
- shared draw.io export concerns
- small declarative YAML controls such as:
  - `Span To Group`
  - row reservation
  - side-by-side placement intent

The point is to make the current engine easier to reason about, not to replace it.

## Practical Guidance for Future Changes

When a new diagram request arrives:

1. first ask whether the issue is a source YAML issue, a generator issue, or a portal-rendering issue
2. prefer the narrowest source-level fix that will generalize safely
3. if the behavior is genuinely a diagram-specific exception, encode it in YAML rather than hard-coding it globally
4. if the behavior reflects a generic diagramming principle, implement it in the generator
5. avoid patching generated draw.io, SVG, or portal outputs unless a one-off fix is explicitly intended

## Commit Strategy

Do not combine visual behavior changes and structural refactors in the same commit.

Preferred sequence:

1. commit working diagram behavior changes first
2. then make a separate behavior-preserving refactor commit

This keeps regressions attributable and makes rollback realistic.

## Final Position

The draw.io generator is tangled, but still viable.

The right move is:

- no rewrite
- no new simplified engine
- yes to incremental detangling
- yes to preserving existing behavior as the controlling constraint

That is the least risky path and the one most consistent with how this repository treats
regenerable artifacts and source-of-truth fixes.
