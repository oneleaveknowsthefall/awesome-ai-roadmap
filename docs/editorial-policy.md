---
title: Editorial, citation, and correction policy
description: Source priorities, technical verification, bilingual editing, version labels, corrections, and citation rules for Awesome AI Roadmap.
---

# Editorial, Citation, and Correction Policy

## Reading and editing the handbook

English is the primary manuscript, accompanied by a complete Simplified Chinese edition. Each section develops a question a reader might actually ask: answer it first, then explain the mechanism, examples, and conditions. Do not rewrite good prose simply to impose a uniform template; do correct technical errors.

The website supports topic-based browsing, while the book provides a continuous reading sequence. Readers should not need repeated detours to understand the current question. Cross-references provide further detail. Figures, formulas, code, and tables should also remain usable offline and on narrow screens.

## Source priorities

During the bilingual migration, the Chinese manuscript preserves the intended scope and examples, while original English-language papers, specifications, and official documentation establish technical meaning. Neither should be replaced with a model's recollection. If they conflict, check the relevant source version, make justified corrections in both languages, and record the evidence and limitations.

Prefer specifications and standards, official documentation, original papers, engineering reports with clear experimental conditions, and practitioner accounts that can be cross-checked. A vendor case can illustrate a method, but vendor-reported performance, cost, or customer benefit is not an independently verified result.

Put citations close to the claims they support. A references section provides further reading; it does not mean that any one link establishes every claim in the chapter.

## Versions and dates

Model capabilities, framework APIs, protocols, and hosted services change quickly. State the checked version, date, and applicable conditions. Page creation and update dates come from the Git history of the current file path. Moving or localizing a page can change those dates, and a large editorial revision can update the timestamp without rechecking every API. Use the version notes and primary links to assess technical currency. Retain useful classical methods, but do not present a historical interface as the current recommendation without qualification.

## Analysis, evidence, and examples

Architecture layers, selection tables, and engineering recommendations are often a synthesis of public sources. Verifiable figures, product capabilities, and other people's findings need attribution. A judgment derived from several sources should state its conditions rather than become a universal claim.

Identify hypothetical scenarios and illustrative data. An acceptance target is a criterion agreed in advance; an illustrative result explains a method; a claim about production performance needs measurements. These are not interchangeable. Use a fictional case to explain how you would design a system, not to claim that you delivered it.

## Keeping the language editions aligned

Start substantive changes in English and review the corresponding Chinese update in the same PR. The editions share chapter identities, examples, and technical claims. Headings, explanations, and figure labels are localized; identifiers, protocol fields, units, data, and mathematical meaning must not drift.

Synchronization records identify the English and Chinese revisions reviewed together. They detect missing or stale pairs, not the quality of a translation. Do not refresh a record without reviewing the text. An English wording-only edit may leave the Chinese wording unchanged if its meaning still matches.

## Reporting and correcting problems

When reporting a problem through a [GitHub issue](https://github.com/zongyangbigpolo/awesome-ai-roadmap/issues/new), include:

1. The page and specific passage.
2. What appears incorrect, ambiguous, or outdated.
3. A primary source that can be checked.
4. A suggested correction.

Corrections remain visible in the commit history. For a disputed judgment, prefer clarifying the conditions and evidence over deleting an alternative view without explanation.

## Citing the project

For the project as a whole:

> Polo Li. *Awesome AI Roadmap: AI Engineering Interview Handbook*. https://zongyangbigpolo.github.io/awesome-ai-roadmap/

For an individual chapter, use its title and the canonical URL for the language cited. An adaptation under CC BY 4.0 must also indicate changes and retain the project link.

## License scope

The repository's original text and diagrams are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Referenced third-party trademarks, screenshots, papers, code, and other material remain subject to their own rights and licenses.

Author attribution and general license information belong in the project information and book closing matter, not between technical sections. Centralizing those notices does not change existing licenses or remove required third-party notices.
