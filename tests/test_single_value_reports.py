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


def test_sum_report_via_fk_include_shows_value(authenticated_page):
    """A Sum report where the field is reached via a FK include must aggregate
    using the full traversal path, not just the leaf field name. Regression test
    for N/A on the single-value tile when col_type_override has a model_path
    (e.g. `Delivery Schedule -> Invoice -> Net Amount`).
    """
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Sum Via Include')
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_single_value_type').select_option(label='Sum')
    page.wait_for_timeout(500)
    # 'Company -> Importance' traverses Payment.company FK to Company.importance.
    # This mirrors the customer bug pattern (forward FK to an included model's
    # numeric column); without the fix, Sum() gets the stripped leaf name and
    # Django raises FieldError, which renders as 'N/A'.
    select2_select(page, 'id_field', 'Company -> Importance')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Sum Via Include')
    body = _get_report_value(page)
    # Without the fix the Sum() call raises FieldError (wrong field path) and
    # charts_base.py substitutes 'N/A' into the tile. The core regression is
    # that 'N/A' should never appear for a valid FK-include Sum.
    assert 'N/A' not in body, f'Single value showed N/A — FK-include Sum broken: {body[:300]}'


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
    modal.locator('#id_prefix_type').select_option(label='Custom')
    page.wait_for_timeout(300)
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


def _breakdown_quantities(page, report_name):
    """Open the report's breakdown and return the Quantity column of its first page."""
    _navigate_to_report(page, report_name)
    page.locator('a.single_value_link').first.click()
    table = page.locator('#modal-1 table.dataTable')
    table.locator('tbody tr').first.wait_for(state='visible', timeout=10000)
    headers = [h.strip() for h in table.locator('thead th').all_inner_texts()]
    column = headers.index('Quantity')
    cells = table.locator(f'tbody tr td:nth-child({column + 1})').all_inner_texts()
    return [int(c.replace(',', '')) for c in cells]


def test_breakdown_sorts_on_the_chosen_field(authenticated_page):
    """The breakdown opens sorted on its order-by field, descending when ascending is off.

    Without an order the table would sort on its first column ascending, so a descending
    Quantity column shows the setting was applied.
    """
    page = authenticated_page
    modal = _open_single_value_modal(page)
    modal.locator('#id_name').fill('Payments by Quantity')
    modal.locator('#id_report_type').select_option(label='Payment')
    modal.locator('#id_show_breakdown').locator('xpath=..').click()
    modal.locator('#div_id_breakdown_order_by_field').wait_for(state='visible')
    quantity = modal.locator('#id_breakdown_fields_available_fields li', has_text='Quantity').first
    quantity.drag_to(modal.locator('#id_breakdown_fields_selection'))
    select2_select(page, 'id_breakdown_order_by_field', 'Quantity')
    modal.locator('#id_breakdown_order_by_ascending').locator('xpath=..').click()
    click_submit_button(page)
    page.wait_for_timeout(1000)

    quantities = _breakdown_quantities(page, 'Payments by Quantity')
    assert len(quantities) > 1, quantities
    assert quantities == sorted(quantities, reverse=True), quantities
    assert quantities[0] > quantities[-1], quantities


def test_breakdown_order_by_hidden_until_breakdown_shown(authenticated_page):
    """The breakdown order fields only show once Show breakdown is on."""
    page = authenticated_page
    modal = _open_single_value_modal(page)
    expect(modal.locator('#div_id_breakdown_order_by_field')).to_be_hidden()
    expect(modal.locator('#div_id_breakdown_order_by_ascending')).to_be_hidden()
    modal.locator('#id_show_breakdown').locator('xpath=..').click()
    expect(modal.locator('#div_id_breakdown_order_by_field')).to_be_visible()
    expect(modal.locator('#div_id_breakdown_order_by_ascending')).to_be_visible()
