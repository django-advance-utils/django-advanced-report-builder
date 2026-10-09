"""Tests for a query version's own period on bar and line charts.

A chart with a period (bar, line) groups by its axis scale. Each query version may set its own
(``ReportQuery.axis_scale``), which applies while that version is selected; a version without one
uses the chart's. Reports with no period don't offer the field at all.
"""

import os
import subprocess

from conftest import BASE_URL, click_submit_button, open_dropdown_item, select2_select, wait_for_modal
from playwright.sync_api import expect

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


def _create_payment_bar_chart(page, name):
    """Create a weekly bar chart of payments by date, with Amount as its field."""
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Bar Chart')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill(name)
    modal.locator('#id_report_type').select_option(label='Payment')
    page.wait_for_timeout(500)
    select2_select(page, 'id_date_field', 'Date')
    modal.locator('#id_axis_scale').select_option(label='Week')

    selection = modal.locator('[id$="_selection"]').first
    available = modal.locator('[id$="_available_fields"]').first
    available.locator('li', has_text='Amount').first.drag_to(selection)
    page.wait_for_timeout(200)

    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)


def _add_versions(name, versions):
    """Give the named report these (name, axis_scale) query versions, in order, replacing any it has."""
    stdout, stderr = _run_django_shell(f"""
from advanced_report_builder.models import Report, ReportQuery
report = Report.objects.get(name='{name}')
report.reportquery_set.all().delete()
for version_name, axis_scale in {versions!r}:
    ReportQuery.objects.create(report=report, name=version_name, axis_scale=axis_scale)
print('OK')
""")
    assert 'OK' in stdout, f'Failed to add versions: {stderr}'


def _open_report(page, name):
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)


def _chart_unit(page):
    """The time unit the chart's x axis was drawn with."""
    return page.evaluate(
        """() => {
            for (const chart of Object.values(Chart.instances)) {
                const unit = chart.options.scales?.x?.time?.unit;
                if (unit) return unit;
            }
            return null;
        }"""
    )


def _open_add_query_modal(page):
    """Click Edit then Add Query Version, as in test_query_builder."""
    page.locator('a', has_text='Edit').first.click()
    page.locator('#modal-1 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)
    page.locator('#modal-1 a', has_text='Add Query').first.click()
    page.locator('#modal-2 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)


def _choose_version(page, version_name):
    page.locator('a', has_text='Version').first.click()
    page.wait_for_timeout(300)
    page.locator('.dropdown-item', has_text=version_name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)


def test_a_version_groups_by_its_own_period(authenticated_page):
    """Selecting a version with a period groups the chart by that period."""
    page = authenticated_page
    _create_payment_bar_chart(page, 'Period Versions')
    # 3 = Month (ANNOTATION_VALUE_MONTH)
    _add_versions('Period Versions', [('Weekly', None), ('Monthly', 3)])
    _open_report(page, 'Period Versions')

    assert _chart_unit(page) == 'week'
    _choose_version(page, 'Monthly')
    assert _chart_unit(page) == 'month'
    expect(page.locator('body')).to_contain_text('Monthly')


def test_a_version_without_a_period_uses_the_charts(authenticated_page):
    """A version that leaves the period blank groups by the chart's own."""
    page = authenticated_page
    _create_payment_bar_chart(page, 'Period Fallback')
    # 2 = Quarter (ANNOTATION_VALUE_QUARTER)
    _add_versions('Period Fallback', [('Quarterly', 2), ('As the chart', None)])
    _open_report(page, 'Period Fallback')

    assert _chart_unit(page) == 'quarter'
    _choose_version(page, 'As the chart')
    assert _chart_unit(page) == 'week'


def test_the_version_modal_offers_a_period_only_for_charts_with_one(authenticated_page):
    """A bar chart's version modal has the Period field; a table's does not."""
    page = authenticated_page
    _create_payment_bar_chart(page, 'Period Modal')
    _open_report(page, 'Period Modal')
    _open_add_query_modal(page)
    expect(page.locator('#modal-2 #id_axis_scale')).to_be_visible()

    page.goto(BASE_URL)
    open_dropdown_item(page, 'Table')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill('Period Table')
    modal.locator('#id_report_type').select_option(label='Company')
    page.locator('#id_table_fields_available_fields li', has_text='Name').first.drag_to(
        page.locator('#id_table_fields_selection')
    )
    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    _open_report(page, 'Period Table')
    _open_add_query_modal(page)
    expect(page.locator('#modal-2 #id_axis_scale')).to_have_count(0)
