"""Tests for the reports index page — listing, adding, and dropdown menu."""
from playwright.sync_api import expect

from conftest import BASE_URL, open_dropdown_item, wait_for_modal


def test_reports_index_loads(authenticated_page):
    """The reports index page loads and shows the reports datatable."""
    page = authenticated_page
    page.goto(BASE_URL)
    expect(page.locator('.dataTables_wrapper')).to_be_visible()


def test_reports_index_has_add_report_menu(authenticated_page):
    """The Add Report dropdown contains all report types."""
    page = authenticated_page
    page.goto(BASE_URL)
    page.get_by_role('link', name='Add Report').click()
    page.wait_for_timeout(300)

    for report_type in ['Table', 'Single Value', 'Bar Chart', 'Line Chart', 'Pie Chart',
                         'Funnel Chart', 'Kanban', 'Calendar', 'Multiple Values']:
        expect(page.locator('.dropdown-item', has_text=report_type).first).to_be_visible()


def test_add_table_report_modal_has_form_fields(authenticated_page):
    """Table report modal has name, report type, and configuration options."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Table')
    modal = wait_for_modal(page)

    expect(modal.locator('#id_name')).to_be_visible()
    expect(modal.locator('#id_report_type')).to_be_visible()
    expect(modal.locator('label', has_text='Has clickable rows')).to_be_visible()
    expect(modal.locator('label', has_text='Page length')).to_be_visible()


def test_add_single_value_modal_has_type_options(authenticated_page):
    """Single value modal has the single_value_type dropdown with all types."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Single Value')
    modal = wait_for_modal(page)

    expect(modal.locator('#id_single_value_type')).to_be_visible()

    # Check all type options are available
    options = modal.locator('#id_single_value_type option')
    option_texts = [options.nth(i).inner_text() for i in range(options.count())]
    for expected in ['Count', 'Sum', 'Percent', 'Percent from Count']:
        assert expected in option_texts, f'Expected "{expected}" in options, got: {option_texts}'


def test_add_multiple_values_modal_opens(authenticated_page):
    """Multiple Values modal opens with name and report type."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Multiple Values')
    modal = wait_for_modal(page)

    expect(modal.locator('#id_name')).to_be_visible()
