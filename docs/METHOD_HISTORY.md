# Method history

This document preserves the development history behind the current study. The public README introduces the accepted research design directly.

## Source and design changes

The resolved-loans extract was replaced by official FOIA status coverage because selection on final loan outcome cannot be repaired with an age filter. The analysis defines complete calendar-month charge-off windows, uses separate temporal roles, excludes reported Term from primary specifications and distinguishes prediction from future-path conditioning. Failed ordinary logit fits led to an explicitly post-results protocol amendment and Firth estimation. These are joint changes in source, estimand and design; legacy and current metrics are not like-for-like performance comparisons. The original Git history, `v1-original` tag, superseded reports and full local research archive are retained outside this public snapshot. Dated G2 and G2-bis aggregate results and protocol versions are included here.

## Timing of specification decisions

The Firth protocol amendment was frozen after failed ordinary-logit fits and calibration results had been inspected, and before the amended fits were estimated. This remains a post-results design change. Cohort reuse, calibration-calendar overlap and realized future macro conditioning limit confirmatory and real-time interpretations. These qualifications remain in the README, notebook and technical report.

Detailed dated records: [initial protocol](PROTOCOL.md), [amended protocol](PROTOCOL_v2_2026-10-08.md), [decisions](../DECISIONS.md), and [execution chronology](G2_BIS_EXECUTION_2026-10-08.md).
