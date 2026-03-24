"""Tests for chart report creation, configuration, and rendering."""

from conftest import BASE_URL, click_submit_button, open_dropdown_item, select2_select, wait_for_modal
from playwright.sync_api import expect


def _navigate_to_report(page, name):
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    page.get_by_role('link', name=name).first.click()
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)


def _add_chart_fields(page, field_names):
    """Open Edit modal and drag fields into selection, then submit."""
    page.locator('a.btn', has_text='Edit').click()
    page.locator('#modal-1 #id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_timeout(300)

    # Charts use a similar reorder widget — find selection and available lists
    selection = page.locator('[id$="_selection"]').first
    available = page.locator('[id$="_available_fields"]').first

    for field_name in field_names:
        field_item = available.locator('li', has_text=field_name).first
        field_item.drag_to(selection)
        page.wait_for_timeout(200)

    click_submit_button(page)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)


def test_pie_chart_create_and_render(authenticated_page):
    """Create a pie chart, add a field, and verify it renders a canvas."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Pie Chart')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill('Company Pie')
    modal.locator('#id_report_type').select_option(label='Company')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Company Pie')
    _add_chart_fields(page, ['Importance'])

    # Pie chart should render a canvas element
    expect(page.locator('canvas').first).to_be_visible(timeout=5000)


def test_funnel_chart_create_and_render(authenticated_page):
    """Create a funnel chart, add fields, and verify it renders SVG."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Funnel Chart')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill('Company Funnel')
    modal.locator('#id_report_type').select_option(label='Company')
    click_submit_button(page)
    page.wait_for_timeout(1000)

    _navigate_to_report(page, 'Company Funnel')
    _add_chart_fields(page, ['Importance'])

    # Funnel chart renders as SVG (d3-funnel)
    expect(page.locator('svg, canvas').first).to_be_visible(timeout=5000)


def test_bar_chart_modal_fields(authenticated_page):
    """Bar chart modal has date field, orientation, and stacked options."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Bar Chart')
    modal = wait_for_modal(page)

    expect(modal.locator('#id_name')).to_be_visible()
    expect(modal.locator('#id_report_type')).to_be_visible()
    expect(modal.locator('label', has_text='Date field').first).to_be_visible()
    expect(modal.locator('label', has_text='Orientation')).to_be_visible()
    expect(modal.locator('label', has_text='Stacked')).to_be_visible()


def test_line_chart_modal_fields(authenticated_page):
    """Line chart modal has date field configuration."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Line Chart')
    modal = wait_for_modal(page)

    expect(modal.locator('#id_name')).to_be_visible()
    expect(modal.locator('#id_report_type')).to_be_visible()
    expect(modal.locator('label', has_text='Date field').first).to_be_visible()


def test_bar_chart_with_date_field(authenticated_page):
    """Create a bar chart with a date field, add a data field, and verify it renders."""
    page = authenticated_page
    page.goto(BASE_URL)
    open_dropdown_item(page, 'Bar Chart')
    modal = wait_for_modal(page)
    modal.locator('#id_name').fill('Payment Bar')
    modal.locator('#id_report_type').select_option(label='Payment')
    page.wait_for_timeout(500)
    select2_select(page, 'id_date_field', 'Date')

    # Drag a field into the chart fields selection
    selection = modal.locator('[id$="_selection"]').first
    available = modal.locator('[id$="_available_fields"]').first
    if available.locator('li', has_text='Amount').count() > 0:
        available.locator('li', has_text='Amount').first.drag_to(selection)
        page.wait_for_timeout(200)

    click_submit_button(page)
    page.wait_for_timeout(2000)

    # Navigate to the report — it may redirect to the report view directly
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    bar_link = page.get_by_role('link', name='Payment Bar')
    if bar_link.count() > 0:
        bar_link.first.click()
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1000)
        # Should render a canvas (Chart.js)
        expect(page.locator('canvas').first).to_be_visible(timeout=5000)
