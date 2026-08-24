import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

from app.vision import (
    generate_action_plan,
    validate_ui_state,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

HTML_FILE = BASE_DIR / "web" / "index.html"

SCREENSHOT_DIR = BASE_DIR / "screenshots"


# ============================================================
# TEST CASES
# ============================================================

TEST_CASES = [
    {
        "name": "Valid Login",
        "username": "alpish",
        "password": "secret123",
        "expected_state": (
            "The login operation was successful. "
            "The page should visibly show the message "
            "\"Login successful!\"."
        ),
    },
    {
        "name": "Invalid Password",
        "username": "alpish",
        "password": "wrong123",
        "expected_state": (
            "The login should fail because the password "
            "is incorrect. The page should visibly show "
            "an invalid credentials or login failed message."
        ),
    },
    {
        "name": "Empty Username",
        "username": "",
        "password": "secret123",
        "expected_state": (
            "The login should fail because the username "
            "is empty. The page should visibly show a "
            "username required or validation error."
        ),
    },
    {
        "name": "Empty Password",
        "username": "alpish",
        "password": "",
        "expected_state": (
            "The login should fail because the password "
            "is empty. The page should visibly show a "
            "password required or validation error."
        ),
    },
]


# ============================================================
# GET INTERACTIVE DOM ELEMENTS
# ============================================================

async def get_interactive_elements(page):

    return await page.locator(
        "button, input, a, select, textarea"
    ).evaluate_all(
        """
        elements => elements.map(element => ({
            selector: element.id
                ? `#${element.id}`
                : null,

            tag: element.tagName.toLowerCase(),

            text: (
                element.innerText ||
                element.value ||
                ""
            ).trim(),

            placeholder:
                element.getAttribute("placeholder") || "",

            type:
                element.getAttribute("type") || "",

            ariaLabel:
                element.getAttribute("aria-label") || ""
        }))
        """
    )


# ============================================================
# RESOLVE AI TARGET
# ============================================================

async def resolve_element(
    page,
    action,
):

    selector = action.get(
        "selector"
    )

    target = action.get(
        "target",
        "",
    ).strip()

    # --------------------------------------------------------
    # 1. Try AI selector
    # --------------------------------------------------------

    if selector:

        try:

            locator = page.locator(
                selector
            )

            if await locator.count() > 0:

                print(
                    f"  🔎 Resolved using selector: "
                    f"{selector}"
                )

                return locator.first

        except Exception:

            pass

    # --------------------------------------------------------
    # 2. Clean target
    # --------------------------------------------------------

    clean_target = target

    suffixes = [
        " button",
        " input",
        " field",
        " textbox",
        " link",
        " element",
    ]

    for suffix in suffixes:

        if clean_target.lower().endswith(
            suffix
        ):

            clean_target = clean_target[
                : -len(suffix)
            ].strip()

            break

    print(
        f"  🔎 Trying semantic target: "
        f"'{clean_target}'"
    )

    # --------------------------------------------------------
    # 3. Button
    # --------------------------------------------------------

    locator = page.get_by_role(
        "button",
        name=clean_target,
        exact=True,
    )

    if await locator.count() > 0:

        print(
            "  ✅ Resolved using button text"
        )

        return locator.first

    # --------------------------------------------------------
    # 4. Placeholder
    # --------------------------------------------------------

    locator = page.get_by_placeholder(
        clean_target,
        exact=True,
    )

    if await locator.count() > 0:

        print(
            "  ✅ Resolved using placeholder"
        )

        return locator.first

    # --------------------------------------------------------
    # 5. Exact text
    # --------------------------------------------------------

    locator = page.get_by_text(
        clean_target,
        exact=True,
    )

    if await locator.count() > 0:

        print(
            "  ✅ Resolved using visible text"
        )

        return locator.first

    # --------------------------------------------------------
    # 6. Case-insensitive text
    # --------------------------------------------------------

    locator = page.get_by_text(
        re.compile(
            re.escape(clean_target),
            re.IGNORECASE,
        )
    )

    if await locator.count() > 0:

        print(
            "  ✅ Resolved using "
            "case-insensitive text"
        )

        return locator.first

    # --------------------------------------------------------
    # 7. DOM metadata fallback
    # --------------------------------------------------------

    elements = await get_interactive_elements(
        page
    )

    target_lower = clean_target.lower()

    for element in elements:

        text = (
            element.get("text") or ""
        ).lower()

        placeholder = (
            element.get("placeholder") or ""
        ).lower()

        aria_label = (
            element.get("ariaLabel") or ""
        ).lower()

        if (
            target_lower in text
            or target_lower in placeholder
            or target_lower in aria_label
        ):

            candidate_selector = (
                element.get("selector")
            )

            if candidate_selector:

                locator = page.locator(
                    candidate_selector
                )

                if await locator.count() > 0:

                    print(
                        "  ✅ Resolved using "
                        "DOM metadata"
                    )

                    return locator.first

    # --------------------------------------------------------
    # Failed
    # --------------------------------------------------------

    raise ValueError(
        "\nCould not resolve AI target.\n"
        f"Target: {target}\n"
        f"Selector: {selector}\n"
        f"Clean target: {clean_target}"
    )


# ============================================================
# EXECUTE AI ACTIONS
# ============================================================

async def execute_actions(
    page,
    actions,
    credentials,
):

    for index, action in enumerate(
        actions,
        start=1,
    ):

        target = action.get(
            "target",
            "",
        )

        action_type = action.get(
            "action"
        )

        print(
            f"\n▶ Action {index}"
        )

        print(
            f"  Target: {target}"
        )

        print(
            f"  Action: {action_type}"
        )

        locator = await resolve_element(
            page,
            action,
        )

        # ----------------------------------------------------
        # Fill
        # ----------------------------------------------------

        if action_type == "fill":

            value = action.get(
                "value",
                "",
            )

            if value == "{{USERNAME}}":

                value = credentials[
                    "username"
                ]

            elif value == "{{PASSWORD}}":

                value = credentials[
                    "password"
                ]

            print(
                "  🔐 Filling field"
            )

            await locator.fill(
                value
            )

            print(
                "  ✅ Filled"
            )

        # ----------------------------------------------------
        # Click
        # ----------------------------------------------------

        elif action_type == "click":

            print(
                "  🖱️ Clicking"
            )

            await locator.click()

            print(
                "  ✅ Clicked"
            )

        else:

            raise ValueError(
                f"Unsupported action: "
                f"{action_type}"
            )


# ============================================================
# RUN ONE TEST
# ============================================================

async def run_test(
    browser,
    test_case,
    test_number,
):

    name = test_case["name"]

    username = test_case["username"]

    password = test_case["password"]

    expected_state = (
        test_case["expected_state"]
    )

    print(
        "\n\n"
        + "=" * 70
    )

    print(
        f"🧪 TEST {test_number}: {name}"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # Create fresh page
    # --------------------------------------------------------

    page = await browser.new_page(
        viewport={
            "width": 1280,
            "height": 720,
        }
    )

    try:

        # ----------------------------------------------------
        # Open page
        # ----------------------------------------------------

        print(
            "\n🌐 Opening application..."
        )

        await page.goto(
            HTML_FILE.as_uri()
        )

        await page.wait_for_load_state(
            "networkidle"
        )

        print(
            "✅ Page loaded"
        )

        # ----------------------------------------------------
        # Initial screenshot
        # ----------------------------------------------------

        initial_screenshot = (
            SCREENSHOT_DIR
            / f"test_{test_number}_before.png"
        )

        await page.screenshot(
            path=str(
                initial_screenshot
            )
        )

        print(
            f"📸 Initial screenshot: "
            f"{initial_screenshot}"
        )

        # ----------------------------------------------------
        # DOM
        # ----------------------------------------------------

        elements = (
            await get_interactive_elements(
                page
            )
        )

        # ----------------------------------------------------
        # Goal
        # ----------------------------------------------------

        goal = f"""
Test the login form.

Username:
{username if username else "(empty)"}

Password:
{"(provided)" if password else "(empty)"}

Perform the login operation using the
available UI elements.

The goal of this test is:

{name}
"""

        # ----------------------------------------------------
        # Credentials
        # ----------------------------------------------------

        credentials = {
            "username": username,
            "password": password,
        }

        # ----------------------------------------------------
        # Vision AI action plan
        # ----------------------------------------------------

        print(
            "\n👁️ Asking Vision AI "
            "to understand the UI..."
        )

        plan = generate_action_plan(
            str(
                initial_screenshot
            ),
            elements,
            goal,
        )

        actions = plan.get(
            "actions",
            []
        )

        if not actions:

            raise ValueError(
                "Vision AI returned "
                "no actions."
            )

        print(
            "\n🤖 Vision AI Action Plan:"
        )

        print(
            "-" * 60
        )

        for index, action in enumerate(
            actions,
            start=1,
        ):

            safe_action = dict(
                action
            )

            if safe_action.get(
                "value"
            ) in [
                "{{USERNAME}}",
                "{{PASSWORD}}",
            ]:

                safe_action[
                    "value"
                ] = "***"

            print(
                f"Action {index}: "
                f"{safe_action}"
            )

        print(
            "-" * 60
        )

        # ----------------------------------------------------
        # Execute
        # ----------------------------------------------------

        print(
            "\n⚙️ Executing AI action plan..."
        )

        await execute_actions(
            page,
            actions,
            credentials,
        )

        # ----------------------------------------------------
        # Wait
        # ----------------------------------------------------

        await page.wait_for_timeout(
            500
        )

        # ----------------------------------------------------
        # DOM result
        # ----------------------------------------------------

        result_locator = page.locator(
            "#result"
        )

        result = ""

        if await result_locator.count() > 0:

            result = await result_locator.inner_text()

        print(
            "\n📋 Browser result:"
        )

        print(
            result
        )

        # ----------------------------------------------------
        # Result screenshot
        # ----------------------------------------------------

        result_screenshot = (
            SCREENSHOT_DIR
            / f"test_{test_number}_after.png"
        )

        await page.screenshot(
            path=str(
                result_screenshot
            )
        )

        print(
            f"\n📸 Result screenshot: "
            f"{result_screenshot}"
        )

        # ----------------------------------------------------
        # Vision validation
        # ----------------------------------------------------

        print(
            "\n👁️ Asking Vision AI "
            "to validate the result..."
        )

        vision_result = validate_ui_state(
            str(
                result_screenshot
            ),
            expected_state,
        )

        vision_passed = (
            vision_result["passed"]
        )

        print(
            "\n👁️ Vision validation:"
        )

        print(
            f"  Passed : "
            f"{vision_result['passed']}"
        )

        print(
            f"  State  : "
            f"{vision_result['state']}"
        )

        print(
            f"  Message: "
            f"{vision_result.get('message', '')}"
        )

        # ----------------------------------------------------
        # Test result
        # ----------------------------------------------------

        print(
            "\n" + "-" * 60
        )

        if vision_passed:

            print(
                f"✅ TEST PASSED: {name}"
            )

            return {
                "name": name,
                "passed": True,
            }

        print(
            f"❌ TEST FAILED: {name}"
        )

        return {
            "name": name,
            "passed": False,
        }

    except Exception as exc:

        print(
            f"\n❌ TEST ERROR: {name}"
        )

        print(
            f"   {type(exc).__name__}: "
            f"{exc}"
        )

        return {
            "name": name,
            "passed": False,
        }

    finally:

        await page.close()


# ============================================================
# MAIN
# ============================================================

async def main():

    SCREENSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not HTML_FILE.exists():

        raise FileNotFoundError(
            f"HTML file not found:\n"
            f"{HTML_FILE}"
        )

    print(
        "\n🚀 Vision AI + Playwright "
        "Test Suite"
    )

    print(
        f"\nTests to execute: "
        f"{len(TEST_CASES)}"
    )

    # --------------------------------------------------------
    # Start Playwright
    # --------------------------------------------------------

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
        )

        results = []

        # ----------------------------------------------------
        # Run tests
        # ----------------------------------------------------

        for index, test_case in enumerate(
            TEST_CASES,
            start=1,
        ):

            result = await run_test(
                browser,
                test_case,
                index,
            )

            results.append(
                result
            )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        passed = sum(
            1
            for result in results
            if result["passed"]
        )

        failed = len(results) - passed

        print(
            "\n\n"
            + "=" * 70
        )

        print(
            "🏁 TEST SUITE SUMMARY"
        )

        print(
            "=" * 70
        )

        for result in results:

            status = (
                "PASS"
                if result["passed"]
                else "FAIL"
            )

            print(
                f"{status:6} | "
                f"{result['name']}"
            )

        print(
            "-" * 70
        )

        print(
            f"Total : {len(results)}"
        )

        print(
            f"Passed: {passed}"
        )

        print(
            f"Failed: {failed}"
        )

        print(
            "=" * 70
        )

        if failed == 0:

            print(
                "\n🎉 ALL TESTS PASSED"
            )

        else:

            print(
                "\n❌ SOME TESTS FAILED"
            )

        print(
            "\n🟢 Test suite finished."
        )

        await browser.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )