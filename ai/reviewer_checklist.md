# AI reviewer — checklist

The reviewer model checks the analyst's draft before it reaches the
newsletter or spreadsheet. It does not generate new recommendations —
it verifies the existing ones.

## Checklist

- [ ] Does every numeric claim (price, %, target) cite a source and date?
- [ ] Does every recommendation reference a specific price level or trigger
      (not just "looks strong" / "looks weak")?
- [ ] Does any recommendation contradict the stop-loss or target already
      set for that holding, without explanation?
- [ ] Is there internal inconsistency (e.g., "bullish" status paired with a
      falling composite score, with no explanation)?
- [ ] Where the analyst disagrees with broker consensus, is that disagreement
      stated explicitly rather than blended in silently?
- [ ] Is any claim based on social-media sentiment being treated as a
      scoring input rather than narrative context?
- [ ] Does the draft avoid reproducing broker research verbatim (signal
      extraction only — rating, target, direction — not copied text)?

## Output
Reviewer returns either:
- **Approved**, or
- **Flagged**, with the specific checklist item(s) that failed and why.

A flagged draft goes back to the analyst step before publication.
