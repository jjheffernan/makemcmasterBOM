# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once a release tag exists.

## [Unreleased]

### Added

- After-hours engineer-density plan (`docs/plans/engineer-density-v1.md`) targeting `dev`
- Agent skills install (`heff-skills` after-hours loop) under `.agents/skills/`
- OpenMANET-style description BOM parsing and plural fastener routing (on `dev`)

### Planned (see plan / TODO)

- Matching preferences (exact vs lazy guess)
- Export pack (TSV/XLSX) without new deps; Google/PDF deferred pending dependency review
- Golden BOM fixture harness and multi-site ingestion scaffold
- Engineer UI density pass

## [0.1.0] — 2026-07 — MVP

Phases 1–9 complete: MakerWorld import → McMaster browse match → edit → CSV export.
Matcher covers 41 Fastening & Joining categories with monthly taxonomy refresh.
