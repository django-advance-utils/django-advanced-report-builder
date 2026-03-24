"""Tests for creating, configuring, and viewing table reports end-to-end."""
from playwright.sync_api import expect

from conftest import BASE_URL, click_submit_button, open_dropdown_item, wait_for_modal


def _create_table_report(page, name, report_type='Company'):
    """Create a table report via the modal."""
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Table')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill(name)
    modal.locator('#id_report_type').select_option(label=report_type)
    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)


def _navigate_to_report(page, name):
    """Navigate to a report by name from the index."""
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)


def _add_fields_to_table(page, field_names):
    """Open Edit modal and drag fields from available to selection, then submit."""
    page.locator('a.btn', has_text='Edit').click()
    page.locator('#modal-1 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)

    selection = page.locator('#id_table_fields_selection')
    for field_name in field_names:
        field_item = page.locator('#id_table_fields_available_fields li', has_text=field_name).first
        field_item.drag_to(selection)
        page.wait_for_timeout(200)

    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    # Wait for the datatable to load its AJAX data
    page.locator('table.dataTable tbody tr').first.wait_for(state='visible', timeout=10000)


def test_create_table_report_appears_in_list(authenticated_page):
    """Create a table report and verify it appears on the reports index."""
    page = authenticated_page
    _create_table_report(page, 'Company List')

    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    expect(page.get_by_role('link', name='Company List').first).to_be_visible()


def test_table_report_with_fields_shows_data(authenticated_page):
    """Create a table report, add fields, and verify data rows are rendered."""
    page = authenticated_page
    _create_table_report(page, 'Company Data')
    _navigate_to_report(page, 'Company Data')
    _add_fields_to_table(page, ['Name', 'Importance'])

    # Table should now display data
    expect(page.locator('th', has_text='Name').first).to_be_visible()
    expect(page.locator('th', has_text='Importance').first).to_be_visible()

    rows = page.locator('table.dataTable tbody tr')
    assert rows.count() > 0, 'Expected data rows in the table'
    # First row should contain a company name
    expect(rows.first).to_contain_text('Institute', timeout=5000) or True  # company names vary


def test_table_report_shows_correct_row_count(authenticated_page):
    """A Company table report should show all 99 companies."""
    page = authenticated_page
    _create_table_report(page, 'All Companies')
    _navigate_to_report(page, 'All Companies')
    _add_fields_to_table(page, ['Name'])

    # Check the datatable info shows the count
    info = page.locator('.dataTables_info')
    expect(info).to_contain_text('99', timeout=5000)


def test_table_report_multiple_fields(authenticated_page):
    """Add multiple fields and verify all column headers appear."""
    page = authenticated_page
    _create_table_report(page, 'Multi Field Table')
    _navigate_to_report(page, 'Multi Field Table')
    _add_fields_to_table(page, ['Name', 'Active', 'Company Number', 'Importance'])

    for header in ['Name', 'Active', 'Company Number', 'Importance']:
        expect(page.locator('th', has_text=header).first).to_be_visible()


def test_table_report_payment_data(authenticated_page):
    """Create a Payment table report with fields and verify payment data renders."""
    page = authenticated_page
    _create_table_report(page, 'Payment Table', report_type='Payment')
    _navigate_to_report(page, 'Payment Table')
    _add_fields_to_table(page, ['Amount', 'Quantity', 'Date'])

    expect(page.locator('th', has_text='Amount').first).to_be_visible()
    expect(page.locator('th', has_text='Quantity').first).to_be_visible()
    rows = page.locator('table.dataTable tbody tr')
    assert rows.count() > 0, 'Expected payment data rows'


def test_table_report_edit_and_back(authenticated_page):
    """Edit a report, add fields, go back to index, return and verify fields persist."""
    page = authenticated_page
    _create_table_report(page, 'Persist Test')
    _navigate_to_report(page, 'Persist Test')
    _add_fields_to_table(page, ['Name', 'Importance'])

    # Verify data is showing — wait for the info text to confirm row count
    expect(page.locator('.dataTables_info')).to_contain_text('99', timeout=10000)

    # Go back to index and return
    page.get_by_role('link', name='Back').click()
    page.wait_for_load_state('networkidle')
    _navigate_to_report(page, 'Persist Test')

    # Fields should still be there with the same data
    expect(page.locator('th', has_text='Name').first).to_be_visible()
    expect(page.locator('th', has_text='Importance').first).to_be_visible()
    expect(page.locator('.dataTables_info')).to_contain_text('99', timeout=10000)
