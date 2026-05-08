from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.pbi.uq.edu.au/clientservices/SECaT/embedChart.aspx")


    page.on("response", lambda r: print(r.url, r.status))

    def get_course_data(letter, course, course_code, course_code_semester_descr):
        page.click(f"text={letter}")
        page.click(f"text={course}")
        page.click(f"text={course_code}")
        page.click(f"text={course_code_semester_descr}")
        return page.content()

    content = get_course_data("C", "CSSE", "CSSE1001", "CSSE1001: Semester 2, 2024")

    data = (content[content.find("courseSECATData"): content.find("var title = '")])
    with open("out_csse1001.txt", "w") as f:
        f.write(data)
    browser.close()