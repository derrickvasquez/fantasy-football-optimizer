# Fantasy Football Draft Optimizer

A Python-based fantasy football draft assistant designed to help users make better, data-driven decisions during live snake drafts.

The initial version is being built specifically around a **10-team ESPN Full PPR league**, with the architecture designed to support additional league formats in the future.

## The Problem

Fantasy draft rankings are useful, but they do not fully account for what is happening inside a specific draft.

A player who is ranked highest overall may not always be the best selection based on:

* Your draft position
* Your current roster
* Players already selected
* Positional scarcity
* ESPN ADP
* The number of picks before your next turn
* Player projections
* Bye-week conflicts
* Injury history and availability
* Player upside and risk
* Changing player roles and preseason news

The goal of this project is to move beyond a static rankings list and answer a more useful question:

> **Given everything that has happened in this draft so far, what is my best next move?**

## What the App Will Do

During a draft, users will be able to:

* Enter their draft position
* Choose the number of draft rounds
* Automatically calculate every pick in a snake draft
* Browse available NFL players
* View player headshots and key fantasy information
* Mark players as drafted by other teams
* Add selected players to **My Team**
* Track the round and overall pick where each player was selected
* Receive updated recommendations after every draft selection
* Compare player projections, ADP, positional value, and roster fit
* Account for bye weeks and injury history
* Estimate whether a player is likely to remain available at the next pick
* Finish the draft and receive a draft report card

## Optimization Goals

The optimizer will eventually consider factors such as:

* Projected fantasy production
* Value over replacement
* Positional scarcity
* Starting-lineup improvement
* ESPN ADP value
* Probability of surviving until the next pick
* Floor and ceiling projections
* Injury and availability risk
* Bye-week roster impact
* Bench value
* Roster balance
* Player upside

The goal is not simply to draft the highest-ranked player.

The goal is to construct the strongest overall fantasy roster based on the state of the draft.

## Future Intelligence

Later versions are planned to include:

* Historical draft simulations
* Machine-learning player projections
* Injury-availability modeling
* Player trend detection
* NFL news and social-media signals
* Historical league-manager tendencies
* Different draft strategies such as Balanced, Safe, and Championship Upside
* Simulated playoff and championship probability

Social-media attention will be treated separately from player performance so that hype does not automatically increase a player's fantasy projection.

## Initial League Configuration

The current development league is:

* Platform: ESPN
* Teams: 10
* Scoring: Full PPR
* Draft Type: Snake
* Keepers: None
* QB: 1
* RB: 2
* WR: 2
* TE: 1
* FLEX: 1
* D/ST: 1
* K: 1
* Bench: 7
* Maximum Draft Rounds: 16

## Technology

The project is being built primarily with:

* Python
* Streamlit
* Polars
* NumPy
* PostgreSQL / Supabase
* nflverse / nflreadpy
* scikit-learn

Additional tools will only be introduced when they provide measurable value to the optimizer.

## Project Philosophy

This project is being built iteratively.

Each feature must work and be tested before development moves to the next phase.

The priorities are:

1. Correctness
2. Explainable recommendations
3. Lightweight architecture
4. Low operating cost
5. Ease of use
6. Visual polish

The application will initially remain simple and functional before additional design and advanced modeling are introduced.
