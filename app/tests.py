import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from app.vision import validate_ui_state


BASE_DIR = Path(__file__).resolve().parent.parent

HTML_FILE = BASE_DIR / "web" / "index.html"

SCREENSHOT_DIR = BASE_DIR / "screenshots"


TEST_CASES = [
    {
        "name": "Valid Login",
        "username": "alpish",
        "password": "secret123",
        "expected": "Login successful!",
        "expected_state": "success",
    },
    {
        "name": "Empty Username",
        "username": "",
        "password": "secret123",
        "expected": "Username is required",
        "expected_state": "validation error",
    },
    {
        "name": "Empty Password",
        "username": "alpish",
        "password": "",
        "expected": "Password is required",
        "expected_state": "validation error",
    },
    {
        "name": "Invalid Credentials",
        "username": "alpish",
        "password": "wrongpassword",
        "expected": "Invalid username or password",
        "expected_state": "authentication error",
    },
]


async def run_test(page, test_case):

    print(
        f"\n{'=' * 50}"
    )

    print(
        f"Running: {test_case['name']}"
    )

    # --------------------------------
    # Fill username
    # --------------------------------

    await page.locator(
        "#username"
    ).fill(
        test_case["username"]
    )

    # --------------------------------
    # Fill password
    # --------------------------------

    await page.locator(
        "#password"
    ).fill(
        test_case["password"]
    )

    # --------------------------------
    # Click Login
    # --------------------------------

    await page.locator(
        "#login-button"
    ).click()

    # --------------------------------
    # DOM validation
    # --------------------------------

    actual = await page.locator(
        "#result"
    ).inner_text()

    expected = test_case["expected"]

    dom_passed = actual == expected

    if dom_passed:

        print(
            f"✅ DOM PASS: {test_case['name']}"
        )

    else:

        print(
            f"❌ DOM FAIL: {test_case['name']}"
        )

        print(
            f"Expected: {expected}"
        )

        print(
            f"Actual: {actual}"
        )

    # --------------------------------
    # Screenshot
    # --------------------------------

    screenshot_path = (
        SCREENSHOT_DIR
        / f"{test_case['name'].lower().replace(' ', '_')}.png"
    )

    await page.screenshot(
        path=str(screenshot_path)
    )

    print(
        f"📸 Screenshot: {screenshot_path}"
    )

    # --------------------------------
    # Vision validation
    # --------------------------------

    vision_result = validate_ui_state(
        str(screenshot_path),
        test_case["expected_state"]
    )

    vision_passed = vision_result["passed"]

    if vision_passed:

        print(
            "👁️ Vision PASS"
        )

    else:

        print(
            "👁️ Vision FAIL"
        )

    # --------------------------------
    # Final result
    # --------------------------------

    passed = (
        dom_passed
        and vision_passed
    )

    if passed:

        print(
            f"\n🎉 TEST PASSED: "
            f"{test_case['name']}"
        )

    else:

        print(
            f"\n❌ TEST FAILED: "
            f"{test_case['name']}"
        )

    return passed


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        page = await browser.new_page(
            viewport={
                "width": 1280,
                "height": 720
            }
        )

        passed = 0
        failed = 0

        # --------------------------------
        # Run test cases
        # --------------------------------

        for test_case in TEST_CASES:

            await page.goto(
                HTML_FILE.as_uri()
            )

            result = await run_test(
                page,
                test_case
            )

            if result:

                passed += 1

            else:

                failed += 1

        # --------------------------------
        # Summary
        # --------------------------------

        total = passed + failed

        print(
            f"\n{'=' * 50}"
        )

        print(
            "TEST SUMMARY"
        )

        print(
            f"{'=' * 50}"
        )

        print(
            f"Total : {total}"
        )

        print(
            f"Passed: {passed}"
        )

        print(
            f"Failed: {failed}"
        )

        print(
            f"{'=' * 50}"
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
            "\nPress ENTER to close browser."
        )

        input()

        await browser.close()


if __name__ == "__main__":

    asyncio.run(main())