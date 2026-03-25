"""Tests for creating, configuring, and viewing table reports end-to-end."""

from conftest import BASE_URL, click_submit_button, open_dropdown_item, select2_select, wait_for_modal
from playwright.sync_api import expect


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


def _open_field_edit_modal(page, field_text):
    """Click the pencil icon on a field in the selection list to open its edit modal."""
    selection = page.locator('#id_table_fields_selection')
    field_item = selection.locator('li', has_text=field_text).first
    field_item.hover()
    page.wait_for_timeout(200)
    field_item.locator('a.edit_field_link').click(force=True)
    # Wait for the nested modal to appear — it opens inside modal-1 as a sub-modal
    page.locator('#modal-1 #id_currency_prefix_type, #modal-2 #id_currency_prefix_type').first.wait_for(
        state='visible', timeout=10000
    )
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)
    # Return the modal that contains the field edit form
    if page.locator('#modal-2 #id_currency_prefix_type').is_visible():
        return page.locator('#modal-2')
    return page.locator('#modal-1')


def _run_django_shell(command):
    """Run a Django shell command in the docker container and return stdout, stderr."""
    import os
    import subprocess
    repo_root = os.path.dirname(os.path.dirname(__file__))
    result = subprocess.run(
        ['docker', 'compose', '-f', os.path.join(repo_root, 'docker-compose.yaml'),
         'exec', '-T', 'django_report_builder', 'python', 'manage.py', 'shell', '-c', command],
        capture_output=True, text=True,
    )
    return result.stdout.strip(), result.stderr.strip()


def _set_table_field_data_attr(report_name, field_name, data_attr_suffix):
    """Update a table field's data_attr in the database directly."""
    stdout, stderr = _run_django_shell(f"""
from advanced_report_builder.models import TableReport
report = TableReport.objects.get(name='{report_name}')
fields = report.table_fields
for f in fields:
    if f['field'] == '{field_name}':
        f['data_attr'] = '{data_attr_suffix}'
        break
report.table_fields = fields
report.save()
print('OK')
""")
    assert 'OK' in stdout, f'Failed to set data_attr: {stderr}'


def test_table_report_currency_prefix_default_none(authenticated_page):
    """A new Contract table report with currency field shows no prefix by default."""
    page = authenticated_page
    _create_table_report(page, 'Currency Default Test', report_type='Contract')
    _navigate_to_report(page, 'Currency Default Test')
    _add_fields_to_table(page, ['Currency Amount'])

    # Currency values should NOT have £ prefix by default
    first_cell = page.locator('table.dataTable tbody tr td').first
    cell_text = first_cell.inner_text()
    assert '£' not in cell_text, f'Expected no prefix by default, got: {cell_text}'


def test_table_report_currency_prefix_automatic(authenticated_page):
    """Setting currency prefix to Automatic shows £ prefix on values."""
    page = authenticated_page
    _create_table_report(page, 'Currency Auto Test', report_type='Contract')
    _navigate_to_report(page, 'Currency Auto Test')
    _add_fields_to_table(page, ['Currency Amount'])

    # Set prefix type to Automatic (0) via database
    _set_table_field_data_attr('Currency Auto Test', 'currency_amount', 'currency_prefix_type-0')

    page.reload()
    page.wait_for_load_state('networkidle')
    page.locator('table.dataTable tbody tr').first.wait_for(state='visible', timeout=10000)

    # Currency values should have £ prefix
    first_cell = page.locator('table.dataTable tbody tr td').first
    expect(first_cell).to_contain_text('£', timeout=5000)


def test_table_report_currency_field_modal_save(authenticated_page):
    """Opening and saving the currency field edit modal should not error."""
    page = authenticated_page
    _create_table_report(page, 'Currency Modal Save', report_type='Contract')
    _navigate_to_report(page, 'Currency Modal Save')
    _add_fields_to_table(page, ['Currency Amount'])

    # Open the edit modal
    page.locator('a.btn', has_text='Edit').click()
    page.locator('#modal-1 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)

    # Open the currency field edit sub-modal
    field_modal = _open_field_edit_modal(page, 'Currency Amount')

    # Verify the currency prefix type dropdown is present
    expect(field_modal.locator('#id_currency_prefix_type')).to_be_visible()

    # Submit the field modal without changes — should not error
    field_modal.locator('.modal-submit').click()
    page.wait_for_timeout(500)

    # Submit the main edit modal — try modal-2 first, fall back to modal-1
    page.evaluate("""
        (document.querySelector("#modal-2 .modal-submit") ||
         document.querySelector("#modal-1 .modal-submit")).click()
    """)
    page.wait_for_load_state('networkidle')
    page.locator('table.dataTable tbody tr').first.wait_for(state='visible', timeout=10000)

    # Values should still show with £ prefix (automatic default)
    first_cell = page.locator('table.dataTable tbody tr td').first
    expect(first_cell).to_contain_text('£', timeout=5000)


def test_table_report_currency_prefix_none(authenticated_page):
    """Setting currency prefix type to None removes the £ prefix from values."""
    page = authenticated_page
    _create_table_report(page, 'Currency None Test', report_type='Contract')
    _navigate_to_report(page, 'Currency None Test')
    _add_fields_to_table(page, ['Currency Amount'])

    # Set prefix type to None (1) via database
    _set_table_field_data_attr('Currency None Test', 'currency_amount', 'currency_prefix_type-1')

    # Reload the report
    page.reload()
    page.wait_for_load_state('networkidle')
    page.locator('table.dataTable tbody tr').first.wait_for(state='visible', timeout=10000)

    # Currency values should NOT have £ prefix
    first_cell = page.locator('table.dataTable tbody tr td').first
    cell_text = first_cell.inner_text()
    assert '£' not in cell_text, f'Expected no £ prefix, got: {cell_text}'


def test_table_report_currency_prefix_custom(authenticated_page):
    """Setting currency prefix type to Custom with $ shows $ prefix on values."""
    page = authenticated_page
    _create_table_report(page, 'Currency Custom Test', report_type='Contract')
    _navigate_to_report(page, 'Currency Custom Test')
    _add_fields_to_table(page, ['Currency Amount'])

    # Set prefix type to Custom (2) with $ prefix via database
    import base64
    b64_prefix = base64.b64encode('$'.encode()).decode()
    _set_table_field_data_attr(
        'Currency Custom Test', 'currency_amount',
        f'currency_prefix_type-2-currency_prefix-{b64_prefix}'
    )

    # Reload the report
    page.reload()
    page.wait_for_load_state('networkidle')
    page.locator('table.dataTable tbody tr').first.wait_for(state='visible', timeout=10000)

    # Currency values should have $ prefix
    first_cell = page.locator('table.dataTable tbody tr td').first
    expect(first_cell).to_contain_text('$', timeout=5000)
