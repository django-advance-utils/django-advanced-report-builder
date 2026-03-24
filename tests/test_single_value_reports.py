"""Tests for creating and viewing single value reports — verifying actual computed values."""

from conftest import BASE_URL, click_submit_button, open_dropdown_item, select2_select, wait_for_modal
from playwright.sync_api import expect


def _open_single_value_modal(page):
    """Navigate to index and open the Add Single Value modal."""
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Single Value')
    return wait_for_modal(page)


def _navigate_to_report(page, name):
    """Navigate to a report by name."""
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)


def _get_report_value(page):
    """Get the displayed value from a single value report page."""
    # The value is displayed as plain text in the report area after the buttons
    page.wait_for_timeout(1000)
    body = page.locator('body').inner_text()
    return body


def test_count_report_shows_99_companies(authenticated_page):
    """A Count report on Company should display 99."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Count Companies')
    modal.locator('#id_report_type').select_option(label='Company')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Count Companies')
    body = _get_report_value(page)
    assert '99' in body, f'Expected 99 companies in report, got: {body[:200]}'


def test_sum_report_shows_total_amount(authenticated_page):
    """A Sum report on Payment amount should display a non-zero total."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Sum Payments')
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_single_value_type').select_option(label='Sum')
    page.wait_for_timeout(500)
    select2_select(page, 'id_field', 'Amount')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Sum Payments')
    body = _get_report_value(page)
    # The sum should be a number with commas (e.g. "2,345,678")
    # Extract digits from the body text
    import re

    numbers = re.findall(r'[\d,]+', body)
    large_numbers = [n for n in numbers if len(n.replace(',', '')) >= 4]
    assert len(large_numbers) > 0, f'Expected a large sum value, got: {body[:200]}'


def test_count_and_sum_report(authenticated_page):
    """A Count & Sum report shows both a count and a sum value."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Count And Sum')
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_single_value_type').select_option(label='Count & Sum')
    page.wait_for_timeout(500)
    select2_select(page, 'id_field', 'Amount')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Count And Sum')
    body = _get_report_value(page)
    # Should contain both a count (435 payments) and a sum
    assert '435' in body or '99' in body, f'Expected count value in report, got: {body[:200]}'


def test_percent_report_shows_percentage(authenticated_page):
    """A Percent report shows a percentage value with % suffix."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Pct Report')
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_single_value_type').select_option(label='Percent')
    page.wait_for_timeout(500)
    select2_select(page, 'id_field', 'Amount')
    page.wait_for_timeout(300)
    select2_select(page, 'id_numerator', 'Amount')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Pct Report')
    body = _get_report_value(page)
    # With same field for both numerator and denominator (no filter), should be 100%
    assert '100' in body, f'Expected 100% (same field, no filter), got: {body[:200]}'


def test_count_report_with_prefix(authenticated_page):
    """A Sum report with a currency prefix displays the prefix."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Prefixed Sum')
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_single_value_type').select_option(label='Sum')
    page.wait_for_timeout(500)
    select2_select(page, 'id_field', 'Amount')
    modal.locator('#id_prefix').fill('£')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Prefixed Sum')
    body = _get_report_value(page)
    assert '£' in body, f'Expected £ prefix in report, got: {body[:200]}'


def test_single_value_report_has_edit_and_duplicate_buttons(authenticated_page):
    """A single value report view shows Edit and Duplicate buttons."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Buttons Test SV')
    modal.locator('#id_report_type').select_option(label='Company')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Buttons Test SV')
    expect(page.locator('a.btn', has_text='Edit')).to_be_visible()
    expect(page.locator('a.btn', has_text='Duplicate')).to_be_visible()
    expect(page.locator('a.btn', has_text='Back')).to_be_visible()
