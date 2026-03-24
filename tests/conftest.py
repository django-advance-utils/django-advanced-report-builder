import os
import subprocess

import pytest


BASE_URL = 'http://localhost:8010'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
BASELINE_DUMP = os.path.join(FIXTURES_DIR, 'baseline.dump')


def _get_compose_cmd():
    """Return the docker compose command prefix, run from the repo root."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    return ['docker', 'compose', '-f', os.path.join(repo_root, 'docker-compose.yaml')]


def restore_baseline():
    """Restore the database from the baseline snapshot."""
    compose = _get_compose_cmd()

    # Drop and recreate the database
    subprocess.run(
        [*compose, 'exec', '-T', 'db', 'psql', '-U', 'django_report_builder', '-c',
         'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'django_report_builder\' AND pid <> pg_backend_pid()'],
        capture_output=True,
    )
    subprocess.run(
        [*compose, 'exec', '-T', 'db', 'dropdb', '-U', 'django_report_builder', '--if-exists', 'django_report_builder'],
        capture_output=True,
    )
    subprocess.run(
        [*compose, 'exec', '-T', 'db', 'createdb', '-U', 'django_report_builder', 'django_report_builder'],
        check=True, capture_output=True,
    )

    # Restore from dump
    with open(BASELINE_DUMP, 'rb') as f:
        subprocess.run(
            [*compose, 'exec', '-T', 'db', 'pg_restore', '-U', 'django_report_builder', '-d', 'django_report_builder', '--no-owner'],
            stdin=f, capture_output=True,
        )


@pytest.fixture(scope='session', autouse=True)
def reset_database():
    """Reset the database to the baseline state once per test session."""
    if os.path.exists(BASELINE_DUMP):
        restore_baseline()


@pytest.fixture
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        'viewport': {'width': 1920, 'height': 1080},
    }


@pytest.fixture
def authenticated_page(page):
    """Login and return an authenticated page."""
    page.set_default_timeout(10000)
    page.goto(f'{BASE_URL}/admin/login/')
    page.fill('#id_username', ADMIN_USERNAME)
    page.fill('#id_password', ADMIN_PASSWORD)
    page.get_by_role('button', name='Log in').click()
    page.wait_for_url(f'{BASE_URL}/admin/')
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    return page


def wait_for_modal(page, modal_id='modal-1'):
    """Wait for a django-modals modal to appear and have content loaded via AJAX."""
    modal = page.locator(f'#{modal_id}')
    modal.locator('#id_name').wait_for(state='visible', timeout=10000)
    page.wait_for_load_state('networkidle')
    return modal


def click_submit_button(page, modal_id='modal-1'):
    """Click the submit button in a modal."""
    modal = page.locator(f'#{modal_id}')
    modal.locator('.modal-submit').click()


def open_dropdown_item(page, item_text):
    """Click Add Report dropdown and select an item."""
    page.get_by_role('link', name='Add Report').click()
    page.wait_for_timeout(300)
    page.locator('.dropdown-item', has_text=item_text).first.click()


def select2_select(page, field_id, option_text):
    """Select an option in a select2 dropdown.

    Handles both regular and AJAX-loaded select2 fields by opening the
    dropdown and typing to search.
    """
    # Click the select2 container to open the dropdown
    container = page.locator(f'#select2-{field_id}-container')
    container.click()
    page.wait_for_timeout(300)

    # Type into the search box to trigger AJAX loading
    search = page.locator('.select2-search__field')
    if search.count() > 0 and search.first.is_visible():
        search.first.fill(option_text)
        page.wait_for_timeout(500)

    # Click the matching option
    page.locator('.select2-results__option', has_text=option_text).first.click()
    page.wait_for_timeout(300)
