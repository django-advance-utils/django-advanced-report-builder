"""Tests for the denominator_query feature on percentage reports.

The Percent single value type calculates:
    Sum(numerator_field, filter=extra_query) / Sum(denominator_field, filter=denominator_query) * 100

- query: filters the overall queryset (both numerator and denominator operate on this)
- extra_query: additional filter applied ONLY to the numerator Sum
- denominator_query: additional filter applied ONLY to the denominator Sum (NEW)

Since extra_query and denominator_query have no UI yet, these tests set them
via the database and verify the rendered percentage changes accordingly.
"""

import os
import re
import subprocess

from conftest import BASE_URL, click_submit_button, open_dropdown_item, select2_select, wait_for_modal

# Repo root (parent of the tests/ dir) — where docker-compose.yaml lives.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_django_shell(command):
    """Run a Django shell command inside the Docker container."""
    result = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'django_report_builder', 'python', 'manage.py', 'shell', '-c', command],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return result.stdout.strip(), result.stderr.strip()


def _create_percent_report_with_query(page, name):
    """Create a Percent report on Payment Amount and add a blank query version."""
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Single Value')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill(name)
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_single_value_type').select_option(label='Percent')
    page.wait_for_timeout(500)
    select2_select(page, 'id_field', 'Amount')
    page.wait_for_timeout(300)
    select2_select(page, 'id_numerator', 'Amount')
    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)

    # Navigate to the report and add a query version
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)

    # For Percent reports, Edit opens the main modal which may auto-open
    # a numerator field sub-modal. We add the query version via database instead.
    stdout, stderr = _run_django_shell(f"""
from advanced_report_builder.models import ReportQuery, SingleValueReport
report = SingleValueReport.objects.get(name='{name}')
ReportQuery.objects.create(report=report, name='Standard')
print('OK')
""")
    assert 'OK' in stdout, f'Failed to create query version: {stderr}'


def _get_report_percentage(page, report_name):
    """Navigate to a report and extract the displayed percentage value."""
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=report_name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1500)
    body = page.locator('body').inner_text()
    # Find percentage-like numbers (could be "100%", "75%", "42")
    match = re.search(r'(\d+(?:\.\d+)?)\s*%?', body.split('Duplicate')[-1])
    if match:
        return float(match.group(1))
    return None


def test_percent_no_filters_shows_100(authenticated_page):
    """Percent report with same field, no extra/denominator queries shows 100%."""
    page = authenticated_page
    _create_percent_report_with_query(page, 'Denom Baseline')
    pct = _get_report_percentage(page, 'Denom Baseline')
    assert pct == 100, f'Expected 100%, got {pct}%'


def test_numerator_filter_reduces_percentage(authenticated_page):
    """Setting extra_query (numerator filter) reduces the percentage below 100%."""
    page = authenticated_page
    _create_percent_report_with_query(page, 'Denom Numer Test')

    # Set extra_query via database: numerator only counts payments with amount > 5000
    stdout, stderr = _run_django_shell("""
from advanced_report_builder.models import ReportQuery, SingleValueReport
report = SingleValueReport.objects.get(name='Denom Numer Test')
rq = ReportQuery.objects.filter(report=report).first()
rq.extra_query = {
    'rules': [{'id': 'amount', 'type': 'integer', 'field': 'amount',
               'input': 'number', 'value': 5000, 'operator': 'greater'}],
    'valid': True, 'condition': 'AND'
}
rq.save()
print(f'OK: extra_query set on query {rq.id}')
""")
    assert 'OK' in stdout, f'Failed: {stderr}'

    pct = _get_report_percentage(page, 'Denom Numer Test')
    assert pct is not None and pct < 100, f'Expected < 100% with numerator filter, got {pct}%'


def test_denominator_filter_increases_percentage(authenticated_page):
    """Setting denominator_query to a narrower filter increases the percentage.

    With numerator filter: amount > 5000
    Without denominator filter: denominator = Sum(all amounts) → some %
    With denominator filter: amount > 3000 → smaller denominator → higher %
    """
    page = authenticated_page
    _create_percent_report_with_query(page, 'Denom Increase Test')

    # Set extra_query (numerator: amount > 5000) — no denominator filter yet
    stdout, _ = _run_django_shell("""
from advanced_report_builder.models import ReportQuery, SingleValueReport
report = SingleValueReport.objects.get(name='Denom Increase Test')
rq = ReportQuery.objects.filter(report=report).first()
rq.extra_query = {
    'rules': [{'id': 'amount', 'type': 'integer', 'field': 'amount',
               'input': 'number', 'value': 5000, 'operator': 'greater'}],
    'valid': True, 'condition': 'AND'
}
rq.save()
print(f'OK')
""")
    assert 'OK' in stdout

    pct_before = _get_report_percentage(page, 'Denom Increase Test')
    assert pct_before is not None and pct_before < 100

    # Now add denominator_query: amount > 3000 (narrows denominator)
    stdout, _ = _run_django_shell("""
from advanced_report_builder.models import ReportQuery, SingleValueReport
report = SingleValueReport.objects.get(name='Denom Increase Test')
rq = ReportQuery.objects.filter(report=report).first()
rq.denominator_query = {
    'rules': [{'id': 'amount', 'type': 'integer', 'field': 'amount',
               'input': 'number', 'value': 3000, 'operator': 'greater'}],
    'valid': True, 'condition': 'AND'
}
rq.save()
print(f'OK')
""")
    assert 'OK' in stdout

    pct_after = _get_report_percentage(page, 'Denom Increase Test')
    assert pct_after is not None
    assert pct_after > pct_before, f'Denominator filter should increase %: before={pct_before}%, after={pct_after}%'


def test_independent_numerator_and_denominator_filters(authenticated_page):
    """Numerator and denominator filters operate independently on the same queryset.

    - extra_query (numerator): amount > 7000
    - denominator_query: quantity > 5
    These filter different columns, proving they're independent.
    """
    page = authenticated_page
    _create_percent_report_with_query(page, 'Denom Independent Test')

    stdout, _ = _run_django_shell("""
from advanced_report_builder.models import ReportQuery, SingleValueReport
report = SingleValueReport.objects.get(name='Denom Independent Test')
rq = ReportQuery.objects.filter(report=report).first()
rq.extra_query = {
    'rules': [{'id': 'amount', 'type': 'integer', 'field': 'amount',
               'input': 'number', 'value': 7000, 'operator': 'greater'}],
    'valid': True, 'condition': 'AND'
}
rq.denominator_query = {
    'rules': [{'id': 'quantity', 'type': 'integer', 'field': 'quantity',
               'input': 'number', 'value': 5, 'operator': 'greater'}],
    'valid': True, 'condition': 'AND'
}
rq.save()
print(f'OK')
""")
    assert 'OK' in stdout

    pct = _get_report_percentage(page, 'Denom Independent Test')
    assert pct is not None and pct > 0, f'Expected a positive percentage, got {pct}%'
    # With independent filters the result won't be 100% or 0%
    assert pct != 100, 'With different filters on numerator and denominator, should not be 100%'
