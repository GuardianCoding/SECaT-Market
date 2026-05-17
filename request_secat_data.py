from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def getCourseData(courseCode: str, sem: int | None = None, year: int | None = None):
    courseCode = courseCode.upper()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()
        page.set_default_timeout(15000)

        try:
            page.goto(
                "https://www.pbi.uq.edu.au/clientservices/SECaT/embedChart.aspx",
                wait_until="domcontentloaded",
                timeout=20000,
            )

            # Click first letter
            page.locator(f"text={courseCode[:1]}").first.click()

            # Wait for course prefix to appear, then click it
            page.locator(f"text={courseCode[:4]}").first.wait_for(state="visible", timeout=10000)
            page.locator(f"text={courseCode[:4]}").first.click()

            # Wait for exact course code to appear, then click it
            page.locator(f"text={courseCode}").first.wait_for(state="visible", timeout=10000)
            page.locator(f"text={courseCode}").first.click()

            offerings_locator = page.locator(f"text={courseCode}: Semester")

            try:
                offerings_locator.first.wait_for(state="visible", timeout=10000)
            except PlaywrightTimeoutError:
                return {
                    "course": courseCode,
                    "available_offerings": [],
                    "selected_offering": None,
                    "data": None,
                    "error": f"No offerings found for {courseCode}",
                }

            offering_count = offerings_locator.count()

            available_offerings = []
            for i in range(offering_count):
                available_offerings.append(
                    offerings_locator.nth(i).inner_text().strip()
                )

            if sem is None or year is None:
                return {
                    "course": courseCode,
                    "available_offerings": available_offerings,
                    "selected_offering": None,
                    "data": None,
                    "error": None,
                }

            target_offering = f"{courseCode}: Semester {sem}, {year}"
            matching_offering = page.locator(f"text={target_offering}")

            if matching_offering.count() == 0:
                return {
                    "course": courseCode,
                    "available_offerings": available_offerings,
                    "selected_offering": None,
                    "data": None,
                    "error": f"{target_offering} is not available",
                }

            matching_offering.first.click()

            # Wait until the SECaT JS data appears, but don't wait longer than needed
            try:
                page.wait_for_function(
                    "() => document.documentElement.innerHTML.includes('courseSECATData')",
                    timeout=10000,
                )
            except PlaywrightTimeoutError:
                pass

            content = page.content()
            start = content.find("courseSECATData")
            end = content.find("var title = '")

            if start == -1 or end == -1:
                return {
                    "course": courseCode,
                    "available_offerings": available_offerings,
                    "selected_offering": target_offering,
                    "data": None,
                    "error": f"Could not find courseSECATData for {target_offering}",
                }

            return {
                "course": courseCode,
                "available_offerings": available_offerings,
                "selected_offering": target_offering,
                "data": content[start:end],
                "error": None,
            }

        except PlaywrightTimeoutError:
            return {
                "course": courseCode,
                "available_offerings": [],
                "selected_offering": None,
                "data": None,
                "error": f"Timeout while loading {courseCode}",
            }

        except Exception as e:
            return {
                "course": courseCode,
                "available_offerings": [],
                "selected_offering": None,
                "data": None,
                "error": str(e),
            }

        finally:
            browser.close()