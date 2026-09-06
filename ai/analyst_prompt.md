# AI analyst — prompt spec

The analyst model receives structured weekly data and produces ranked,
sourced recommendations. It never places trades — output is advisory only.

## Inputs
- Current holdings (from `sheets/holdings.csv`) with entry price, thesis, targets, stop-loss
- Watchlist candidates (from `sheets/watchlist.csv`)
- This week's market data pull (price, volume)
- FII/DII flow trend (quarterly shareholding % change direction)
- News/policy digest (thesis-relevant items only)
- Broker consensus targets, where available

## Required output format
For each holding and each watchlist candidate:
1. **One-line status**: on-thesis / near target / near stop-loss / off-thesis
2. **What changed this week** (or "no material change")
3. **Composite score** (0–100) with the weighting shown:
   - Valuation vs. sector (30%)
   - FII/DII flow direction (25%)
   - News/policy relevance (25%)
   - Broker consensus alignment (20%)
4. **Every numeric claim must cite its source and date** — no unsourced figures.

## Guardrails
- Never recommend an action without a defined price level or trigger.
- Never treat social-media sentiment as a data input for scoring — flag it as narrative context only, if mentioned at all.
- Flag disagreement with broker consensus explicitly rather than averaging it away.
