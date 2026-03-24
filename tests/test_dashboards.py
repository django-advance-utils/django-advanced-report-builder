"""Tests for dashboard creation and report embedding."""

from conftest import BASE_URL
from playwright.sync_api import expect

DASHBOARDS_URL = f'{BASE_URL}/dashboards/'


def test_dashboards_index_loads(authenticated_page):
    """The dashboards index page loads with a datatable."""
    page = authenticated_page
    page.goto(DASHBOARDS_URL)
    page.wait_for_load_state('networkidle')
    expect(page.locator('.dataTables_wrapper')).to_be_visible()


def test_dashboards_nav_link(authenticated_page):
    """The Dashboard nav link navigates to the dashboards page."""
    page = authenticated_page
    page.goto(BASE_URL)
    page.get_by_role('link', name='Dashboard', exact=True).click()
    page.wait_for_load_state('networkidle')
    expect(page).to_have_url(DASHBOARDS_URL)


def test_dashboards_has_add_button(authenticated_page):
    """The dashboards page has an Add Dashboard button."""
    page = authenticated_page
    page.goto(DASHBOARDS_URL)
    page.wait_for_load_state('networkidle')
    expect(page.locator('a.btn, button.btn', has_text='Add').first).to_be_visible()
