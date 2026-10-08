"""G1 coverage/status QA only: no model fitting or policy-outcome comparisons."""
import collections
import json
import pathlib
import time
import pandas as pd

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
REPO = args.repo
MANIFEST = json.loads((REPO / 'docs/g1_foia_manifest_2026-06-30.json').read_text())
DATE_FIELDS = ['AsOfDate', 'ApprovalDate', 'FirstDisbursementDate', 'ChargeOffDate', 'PaidInFullDate']
FIELDS = DATE_FIELDS + ['Program', 'LoanStatus', 'GrossApproval', 'SBAGuaranteedApproval', 'GrossChargeOffAmount', 'RevolverStatus', 'BusinessAge', 'ProjectState', 'TermInMonths']
results = []
started = time.monotonic()
for resource in MANIFEST['files']:
    path = REPO / resource['relative_raw_path']
    counts = collections.Counter()
    statuses = collections.Counter()
    programs = collections.Counter()
    business_ages = collections.Counter()
    rev = collections.Counter()
    date_range = {}
    missing_dates_by_status = collections.defaultdict(collections.Counter)
    approval_years = collections.Counter()
    disbursement_years = collections.Counter()
    window_excluded_years = collections.Counter()
    for frame in pd.read_csv(path, usecols=FIELDS, dtype=str, encoding='utf-8-sig', keep_default_na=False, chunksize=100000):
        counts['rows'] += len(frame)
        status = frame.LoanStatus.str.replace(r'\s+', '', regex=True).str.upper()
        statuses.update(status)
        programs.update(frame.Program.str.strip())
        business_ages.update(frame.BusinessAge.str.strip())
        rev.update(frame.RevolverStatus.str.strip())
        dates = {}
        for field in DATE_FIELDS:
            raw = frame[field].str.strip()
            value = pd.to_datetime(raw, format='%Y-%m-%d', errors='coerce')
            dates[field] = value
            counts['invalid_nonblank_' + field] += int(((raw != '') & value.isna()).sum())
            for s in status.unique():
                missing_dates_by_status[str(s)][field] += int((value.isna() & (status == s)).sum())
            if value.notna().any():
                minimum, maximum = str(value.min().date()), str(value.max().date())
                old = date_range.get(field, [minimum, maximum])
                date_range[field] = [min(old[0], minimum), max(old[1], maximum)]
        approval_years.update(str(int(x)) for x in dates['ApprovalDate'].dt.year.dropna())
        disbursement_years.update(str(int(x)) for x in dates['FirstDisbursementDate'].dt.year.dropna())
        recent = dates['FirstDisbursementDate'] > pd.Timestamp('2023-06-30')
        window_excluded_years.update(str(int(x)) for x in dates['FirstDisbursementDate'][recent].dt.year.dropna())
        counts['incomplete_36_month_window'] += int(recent.sum())
        counts['cancelled_or_undisbursed'] += int(status.isin(['CANCLD', 'COMMIT']).sum())
        counts['noncancelled_with_missing_first_disbursement'] += int((~status.isin(['CANCLD', 'COMMIT']) & dates['FirstDisbursementDate'].isna()).sum())
        counts['chargeoff_status_missing_date'] += int(((status == 'CHGOFF') & dates['ChargeOffDate'].isna()).sum())
        counts['chargeoff_date_before_first_disbursement'] += int((dates['ChargeOffDate'] < dates['FirstDisbursementDate']).sum())
        counts['first_disbursement_before_approval'] += int((dates['FirstDisbursementDate'] < dates['ApprovalDate']).sum())
        counts['dates_after_snapshot'] += sum(int((dates[x] > pd.Timestamp('2026-06-30')).sum()) for x in DATE_FIELDS)
        counts['nonchargeoff_status_with_chargeoff_date'] += int(((status != 'CHGOFF') & dates['ChargeOffDate'].notna()).sum())
        counts['non_pif_status_with_payoff_date'] += int(((status != 'PIF') & dates['PaidInFullDate'].notna()).sum())
        counts['payoff_date_before_first_disbursement'] += int((dates['PaidInFullDate'] < dates['FirstDisbursementDate']).sum())
        counts['unknown_status'] += int((~status.isin(['CANCLD', 'COMMIT', 'CHGOFF', 'EXEMPT', 'PIF'])).sum())
        gross = pd.to_numeric(frame.GrossApproval, errors='coerce')
        guaranteed = pd.to_numeric(frame.SBAGuaranteedApproval, errors='coerce')
        chargeoff = pd.to_numeric(frame.GrossChargeOffAmount, errors='coerce')
        counts['invalid_or_nonpositive_gross_approval'] += int((gross.isna() | (gross <= 0)).sum())
        counts['guarantee_exceeds_gross_approval'] += int((guaranteed > gross).sum())
        counts['chargeoff_amount_exceeds_gross_approval'] += int((chargeoff > gross).sum())
    item = {'filename': path.name, 'rows': counts.pop('rows'), 'canonical_status_counts': dict(statuses), 'program_values': dict(programs), 'business_age_values': dict(business_ages), 'revolver_values': dict(rev), 'date_ranges': date_range, 'missing_dates_by_status': {k: dict(v) for k,v in missing_dates_by_status.items()}, 'source_quality_counts': dict(counts), 'approval_year_counts': dict(sorted(approval_years.items())), 'first_disbursement_year_counts': dict(sorted(disbursement_years.items())), 'incomplete_window_counts_by_first_disbursement_year': dict(sorted(window_excluded_years.items()))}
    results.append(item)
    print(json.dumps({k:item[k] for k in ('filename','rows','canonical_status_counts','date_ranges','source_quality_counts')}), flush=True)
output = {'review_date': '2026-10-08', 'snapshot_date': '2026-06-30', 'scope': 'Source coverage/status/date completeness only; no models, default rates by policy date, or fitted results', 'elapsed_seconds': round(time.monotonic()-started,3), 'files': results}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(output, indent=2)+'\n')
print('Source QA complete.', flush=True)
