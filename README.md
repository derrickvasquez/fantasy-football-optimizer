# Fantasy Football Draft Optimizer — Draft Night v0.1

A lightweight Streamlit draft assistant for a 10-team ESPN Full PPR snake draft.

## Draft-night features

- Draft position 1–10 and up to 16 rounds
- Correct snake draft ownership/pick tracking
- Current PPR consensus player pool and bye weeks
- Best-effort ESPN PPR ADP enrichment with safe ECR fallback
- Player headshots when an ESPN player ID is available
- ✅ add to My Team / ❌ drafted by opponent
- Automatic live recalculation
- Roster-aware optimizer score
- Next-pick urgency estimate
- Search, position filters, and sorting
- Undo last pick
- My Team with round/overall pick history
- Finish Draft report card

## Run

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

## Important

Draft Night v0.1 intentionally favors reliability over complexity. It does not yet include a trained injury-history model, social-media monitoring, ESPN live-draft synchronization, or Monte Carlo championship simulations.
