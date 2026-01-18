# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for csvnorm.

## What is an ADR?

An ADR documents a significant architectural decision, including:
- **Context**: What problem required a decision?
- **Decision**: What was chosen?
- **Alternatives**: What options were rejected and why?
- **Consequences**: Trade-offs and implications

## ADRs in this project

- [ADR 001: Use DuckDB for CSV validation](001-use-duckdb-for-csv-validation.md)
- [ADR 002: Fallback delimiter strategy](002-fallback-delimiter-strategy.md)
- [ADR 003: Stdout vs file output modes](003-stdout-vs-file-output-modes.md)
- [ADR 004: Temp file lifecycle](004-temp-file-lifecycle.md)

## Purpose

These records help:
- New contributors understand design rationale
- Avoid revisiting settled decisions
- Document trade-offs made during development
- Provide context for future refactoring

## Format

Each ADR follows this structure:
- **Title**: Decision being documented
- **Date**: When decision was made
- **Status**: Accepted, Deprecated, Superseded
- **Context**: Problem and constraints
- **Decision**: What was chosen
- **Alternatives**: Options considered and rejected
- **Consequences**: Positive, negative, neutral impacts
- **Implementation Notes**: Key details and code references
- **Related Decisions**: Links to other ADRs
