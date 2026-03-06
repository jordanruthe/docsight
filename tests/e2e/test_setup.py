"""E2E tests for the setup wizard (/setup)."""

import pytest
from playwright.sync_api import expect


def _start_fresh(page):
    """Click 'New Setup' and wait for the wizard form to be visible."""
    page.locator(".choice-card").first.click()
    expect(page.locator("#setup-form")).to_be_visible()


def _click_next(page):
    """Click the visible 'Next' button within the active step."""
    page.locator(".step-content.active button.btn-primary", has_text="Next").click()


def _click_back(page):
    """Click the visible 'Back' button within the active step."""
    page.locator(".step-content.active button.btn-ghost", has_text="Back").click()


class TestSetupPageLoad:
    """Setup page renders with Tribu Design System elements."""

    def test_redirects_to_setup(self, setup_page):
        assert "/setup" in setup_page.url

    def test_has_mesh_background(self, setup_page):
        mesh = setup_page.locator(".mesh-bg")
        assert mesh.count() == 1

    def test_has_glass_cards(self, setup_page):
        glass = setup_page.locator(".glass")
        assert glass.count() >= 2  # at least 2 choice cards

    def test_lucide_icons_render(self, setup_page):
        svgs = setup_page.locator(".choice-card svg")
        assert svgs.count() >= 2

    def test_setup_title_visible(self, setup_page):
        title = setup_page.locator(".setup-title")
        assert title.is_visible()


class TestSetupStartChoice:
    """Start choice: New Setup vs Restore."""

    def test_two_choice_cards(self, setup_page):
        cards = setup_page.locator(".choice-card")
        assert cards.count() == 2

    def test_click_new_setup_shows_stepper(self, setup_page):
        setup_page.locator(".choice-card").first.click()
        stepper = setup_page.locator(".setup-stepper")
        expect(stepper).to_be_visible()

    def test_click_restore_shows_restore_section(self, setup_page):
        setup_page.locator(".choice-card").nth(1).click()
        restore = setup_page.locator("#restore-section")
        expect(restore).to_be_visible()


class TestSetupWizardFlow:
    """Step-by-step wizard navigation."""

    def test_step1_to_step2(self, setup_page):
        _start_fresh(setup_page)
        step1 = setup_page.locator(".step-content[data-step='1']")
        expect(step1).to_be_visible()
        _click_next(setup_page)
        step2 = setup_page.locator(".step-content[data-step='2']")
        expect(step2).to_be_visible()

    def test_step2_back_to_step1(self, setup_page):
        _start_fresh(setup_page)
        _click_next(setup_page)
        expect(setup_page.locator(".step-content[data-step='2']")).to_be_visible()
        _click_back(setup_page)
        step1 = setup_page.locator(".step-content[data-step='1']")
        expect(step1).to_be_visible()

    def test_step3_review_populates(self, setup_page):
        _start_fresh(setup_page)
        _click_next(setup_page)
        expect(setup_page.locator(".step-content[data-step='2']")).to_be_visible()
        _click_next(setup_page)
        expect(setup_page.locator(".step-content[data-step='3']")).to_be_visible()
        review_tz = setup_page.locator("#review-tz")
        assert review_tz.text_content() != ""


class TestSetupRestore:
    """Restore flow."""

    def test_restore_file_input_visible(self, setup_page):
        setup_page.locator(".choice-card").nth(1).click()
        file_input = setup_page.locator("#restore-file")
        expect(file_input).to_be_visible()

    def test_restore_back_to_start(self, setup_page):
        setup_page.locator(".choice-card").nth(1).click()
        expect(setup_page.locator("#restore-section")).to_be_visible()
        setup_page.locator("#restore-section button.btn-ghost", has_text="Back").click()
        start = setup_page.locator("#setup-start")
        expect(start).to_be_visible()


class TestSetupThemeToggle:
    """Theme toggle on setup page."""

    def test_default_theme_dark(self, setup_page):
        theme = setup_page.locator("html").get_attribute("data-theme")
        assert theme == "dark"

    def test_toggle_to_light(self, setup_page):
        setup_page.locator("button", has_text="Theme").click()
        theme = setup_page.locator("html").get_attribute("data-theme")
        assert theme == "light"

    def test_toggle_back_to_dark(self, setup_page):
        setup_page.locator("button", has_text="Theme").click()  # -> light
        setup_page.locator("button", has_text="Theme").click()  # -> dark
        theme = setup_page.locator("html").get_attribute("data-theme")
        assert theme == "dark"


class TestSetupResponsive:
    """Mobile responsive layout."""

    def test_choice_cards_stack_on_mobile(self, page, setup_server):
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(setup_server)
        page.wait_for_load_state("networkidle")
        cards = page.locator(".choice-card")
        assert cards.count() == 2
        box1 = cards.first.bounding_box()
        box2 = cards.nth(1).bounding_box()
        assert box1 is not None and box2 is not None
        # Stacked = second card below first, same left offset
        assert abs(box1["x"] - box2["x"]) < 5
        assert box2["y"] > box1["y"]
