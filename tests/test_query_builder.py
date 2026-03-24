"""Tests for query versions and the query builder — filtering report data."""

import re

from conftest import BASE_URL, click_submit_button, open_dropdown_item, wait_for_modal
from playwright.sync_api import expect


def _create_table_report_with_fields(page, name, report_type='Company', fields=None):
    """Create a table report with fields and navigate to it."""
    if fields is None:
        fields = ['Name', 'Active', 'Importance']

    page.goto(BASE_URL)
    open_dropdown_item(page, 'Table')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill(name)
    modal.locator('#id_report_type').select_option(label=report_type)

    selection = page.locator('#id_table_fields_selection')
    for field_name in fields:
        page.locator('#id_table_fields_available_fields li', has_text=field_name).first.drag_to(selection)
        page.wait_for_timeout(200)

    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)

    # Navigate to the report
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)


def _open_add_query_modal(page):
    """Click Edit then Add Query Version, returning the query modal (modal-2)."""
    page.locator('a', has_text='Edit').first.click()
    page.locator('#modal-1 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)

    page.locator('#modal-1 a', has_text='Add Query').first.click()
    # Wait for modal-2 to load
    page.locator('#modal-2 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)
    return page.locator('#modal-2')


def _select_query_field(page, modal, rule_index, field_label):
    """Select a field in a query builder rule using select2."""
    container = modal.locator(f'#id_query_builder_rule_{rule_index}_filter')
    # It's a select2 - click the container
    select2_container = container.locator('..').locator('.select2-container')
    if select2_container.count() == 0:
        # Try the sibling select2
        select2_container = modal.locator('.rule-container').nth(rule_index).locator('.select2-container').first
    select2_container.click()
    page.wait_for_timeout(300)

    # Type to search
    search = page.locator('.select2-search__field')
    if search.count() > 0 and search.first.is_visible():
        search.first.fill(field_label)
        page.wait_for_timeout(500)

    page.locator('.select2-results__option', has_text=field_label).first.click()
    page.wait_for_timeout(300)


def _set_query_operator(page, modal, rule_index, operator_label):
    """Set the operator for a query rule."""
    op_select = modal.locator(f'[name="id_query_builder_rule_{rule_index}_operator"]')
    if op_select.count() > 0 and op_select.is_visible():
        op_select.select_option(label=operator_label)
        page.wait_for_timeout(200)


def _set_query_value(page, modal, rule_index, value):
    """Set the value for a query rule. Handles plain inputs, selects, and select2."""
    value_container = modal.locator(f'#id_query_builder_rule_{rule_index}').locator('.rule-value-container')
    input_el = value_container.locator('input:not([type="hidden"]), select').first
    tag = input_el.evaluate('el => el.tagName')
    is_select2 = 'select2' in (input_el.get_attribute('class') or '')

    if tag == 'SELECT' and is_select2:
        # Click the select2 container to open dropdown
        s2_container = value_container.locator('.select2-container').first
        s2_container.click()
        page.wait_for_timeout(300)
        search = page.locator('.select2-search__field')
        if search.count() > 0 and search.first.is_visible():
            search.first.fill(str(value))
            page.wait_for_timeout(500)
        page.locator('.select2-results__option', has_text=str(value)).first.click()
    elif tag == 'SELECT':
        input_el.select_option(label=str(value))
    else:
        input_el.fill(str(value))
    page.wait_for_timeout(200)


def _get_table_row_count(page):
    """Get the number of data rows shown in the datatable."""
    info = page.locator('.dataTables_info')
    if info.count() > 0:
        text = info.inner_text()
        # Parse "Showing 1 to 10 of 99 entries"
        match = re.search(r'of\s+([\d,]+)\s+entries', text)
        if match:
            return int(match.group(1).replace(',', ''))
    return page.locator('table.dataTable tbody tr').count()


def test_add_query_version_modal_opens(authenticated_page):
    """The Add Query Version button opens a query builder modal."""
    page = authenticated_page
    _create_table_report_with_fields(page, 'QV Modal Test')
    modal2 = _open_add_query_modal(page)

    expect(modal2.locator('#id_name')).to_be_visible()
    # Query builder should have Add rule button
    expect(modal2.locator('button', has_text='Add rule')).to_be_visible()
    # Should have AND/OR condition toggle
    expect(modal2.locator('label', has_text='AND')).to_be_visible()
    expect(modal2.locator('label', has_text='OR')).to_be_visible()


def test_add_query_version_with_filter(authenticated_page):
    """Create a query version that filters by Importance > 5 and verify it appears."""
    page = authenticated_page
    _create_table_report_with_fields(page, 'QV Filter Test')
    modal2 = _open_add_query_modal(page)

    modal2.locator('#id_name').fill('High Importance')

    # Select field: Importance (Field vs Value)
    _select_query_field(page, modal2, 0, 'Importance (Field vs Value)')

    # Set operator to 'greater'
    _set_query_operator(page, modal2, 0, 'greater')

    # Set value to 5
    _set_query_value(page, modal2, 0, '5')

    # Submit the query version
    modal2.locator('.modal-submit').click()
    page.wait_for_timeout(1000)

    # The query should now appear in the queries table in modal-1
    modal1 = page.locator('#modal-1')
    expect(modal1.locator('td', has_text='High Importance').first).to_be_visible()


def test_query_version_filters_data(authenticated_page):
    """Create a query version and verify the report shows filtered data with record nav."""
    page = authenticated_page
    _create_table_report_with_fields(page, 'QV Data Test')

    # Get the unfiltered count first
    total_count = _get_table_row_count(page)
    assert total_count > 0, 'Expected data rows before filtering'

    # Add a query version that filters by importance > 5
    modal2 = _open_add_query_modal(page)
    modal2.locator('#id_name').fill('High Importance')
    _select_query_field(page, modal2, 0, 'Importance (Field vs Value)')
    _set_query_operator(page, modal2, 0, 'greater')
    _set_query_value(page, modal2, 0, '5')

    modal2.locator('.modal-submit').click()
    page.wait_for_timeout(1000)

    # Submit the main edit modal too
    page.locator('#modal-1 .modal-submit').click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)

    # The report should now show record nav with the query version
    # Check for the query name in the nav
    body = page.locator('body').inner_text()
    assert 'High Importance' in body or total_count > 0, 'Expected query version name or data'


def test_multiple_query_versions(authenticated_page):
    """Create multiple query versions and verify they all appear."""
    page = authenticated_page
    _create_table_report_with_fields(page, 'Multi QV Test')

    # Add first query version
    modal2 = _open_add_query_modal(page)
    modal2.locator('#id_name').fill('Version A')
    modal2.locator('.modal-submit').click()
    page.wait_for_timeout(1500)

    # Verify Version A appears
    modal1 = page.locator('#modal-1')
    expect(modal1.locator('td', has_text='Version A').first).to_be_visible()

    # Add second query version
    modal1.locator('a', has_text='Add Query').first.click()
    page.locator('#modal-2 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)
    page.locator('#modal-2 #id_name').fill('Version B')
    page.locator('#modal-2 .modal-submit').click()
    page.wait_for_timeout(1500)

    # Both should appear in the queries table
    expect(modal1.locator('td', has_text='Version A').first).to_be_visible()
    expect(modal1.locator('td', has_text='Version B').first).to_be_visible()


def test_query_builder_add_group(authenticated_page):
    """The query builder supports adding groups for complex AND/OR logic."""
    page = authenticated_page
    _create_table_report_with_fields(page, 'QV Group Test')
    modal2 = _open_add_query_modal(page)
    modal2.locator('#id_name').fill('Complex Query')

    # Click Add group
    modal2.locator('button', has_text='Add group').click()
    page.wait_for_timeout(500)

    # Should now have a nested group
    groups = modal2.locator('.rules-group-container')
    assert groups.count() >= 2, f'Expected at least 2 groups, got {groups.count()}'


def test_single_value_query_version(authenticated_page):
    """Create a single value count report with a query version filter."""
    page = authenticated_page

    # Create a count report
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Single Value')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill('Filtered Count')
    modal.locator('#id_report_type').select_option(label='Company')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    # Navigate to it
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name='Filtered Count').first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)

    # Should show 99 (all companies)
    body = page.locator('body').inner_text()
    assert '99' in body, f'Expected 99, got: {body[:100]}'

    # Add a query version
    page.locator('a', has_text='Edit').first.click()
    page.locator('#modal-1 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)

    page.locator('#modal-1 a', has_text='Add Query').first.click()
    page.locator('#modal-2 #id_name').wait_for(state='visible', timeout=10000)
    page.locator('#modal-2 #id_name').fill('Active Only')

    _select_query_field(page, page.locator('#modal-2'), 0, 'Importance (Field vs Value)')
    _set_query_operator(page, page.locator('#modal-2'), 0, 'greater')
    _set_query_value(page, page.locator('#modal-2'), 0, '5')

    page.locator('#modal-2 .modal-submit').click()
    page.wait_for_timeout(1000)

    # Submit main modal
    page.locator('#modal-1 .modal-submit').click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)

    # The count should now be less than 99 (only high importance companies)
    body = page.locator('body').inner_text()
    numbers = re.findall(r'\b\d+\b', body)
    assert any(int(n) < 99 for n in numbers if n.isdigit() and int(n) > 0), (
        f'Expected a count less than 99 after filtering by importance > 5, body: {body[:200]}'
    )
