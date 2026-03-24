"""Tests for main navigation, page structure, and admin access."""
from playwright.sync_api import expect

from conftest import BASE_URL


def test_main_nav_links(authenticated_page):
    """The main navigation has Reports, Dashboard, and Targets links."""
    page = authenticated_page
    page.goto(BASE_URL)

    expect(page.get_by_role('link', name='Reports')).to_be_visible()
    expect(page.get_by_role('link', name='Dashboard')).to_be_visible()
    expect(page.get_by_role('link', name='Targets')).to_be_visible()


def test_admin_link_visible_for_superuser(authenticated_page):
    """The Admin link is visible for superusers."""
    page = authenticated_page
    page.goto(BASE_URL)
    expect(page.get_by_role('link', name='Admin')).to_be_visible()


def test_reports_nav_navigates(authenticated_page):
    """Clicking Reports navigates to the reports index."""
    page = authenticated_page
    page.goto(f'{BASE_URL}/dashboards/')
    page.get_by_role('link', name='Reports').click()
    page.wait_for_load_state('networkidle')
    expect(page).to_have_url(f'{BASE_URL}/')


def test_targets_page_loads(authenticated_page):
    """The targets page loads and shows the targets datatable with Add Target button."""
    page = authenticated_page
    page.goto(f'{BASE_URL}/targets/')
    page.wait_for_load_state('networkidle')
    expect(page.locator('.dataTables_wrapper')).to_be_visible()
    expect(page.get_by_role('link', name='Add Target')).to_be_visible()


def test_reports_index_shows_datatable(authenticated_page):
    """The reports index displays a datatable with report type grouping."""
    page = authenticated_page
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')

    expect(page.locator('.dataTables_wrapper')).to_be_visible()
    # Should have column headers
    expect(page.locator('th', has_text='Name').first).to_be_visible()
    expect(page.locator('th', has_text='Instance Type').first).to_be_visible()
