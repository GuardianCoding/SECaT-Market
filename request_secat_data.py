from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.pbi.uq.edu.au/clientservices/SECaT/embedChart.aspx")


    page.on("response", lambda r: print(r.url, r.status))


    page.click("text=C")
    page.click("text=CSSE")




    content = page.content()
    print(content)
    browser.close()