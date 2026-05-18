from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from camoufox.sync_api import Camoufox

app = FastAPI(title="Camoufox Scraper")


class ScrapeRequest(BaseModel):
    url: str
    headers: Optional[dict] = None
    mobile: Optional[bool] = False
    wait_for: Optional[str] = "networkidle"   # networkidle | load | domcontentloaded
    wait_for_selector: Optional[str] = None
    scroll_to_bottom: Optional[bool] = False
    timeout: Optional[int] = 30000            # ms


class ScrapeResponse(BaseModel):
    html: str
    final_url: str
    status: str = "ok"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
def scrape(req: ScrapeRequest):
    viewport = {"width": 390, "height": 844} if req.mobile else {"width": 1280, "height": 800}

    try:
        with Camoufox(headless=True) as browser:
            context = browser.new_context(
                viewport=viewport,
                extra_http_headers=req.headers or {},
                is_mobile=req.mobile or False,
            )
            page = context.new_page()
            page.set_default_timeout(req.timeout)

            response = page.goto(req.url, wait_until=req.wait_for, timeout=req.timeout)

            if req.wait_for_selector:
                page.wait_for_selector(req.wait_for_selector, timeout=req.timeout)

            if req.scroll_to_bottom:
                page.evaluate("""
                    () => new Promise(resolve => {
                        let total = 0;
                        const step = 300;
                        const timer = setInterval(() => {
                            window.scrollBy(0, step);
                            total += step;
                            if (total >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    })
                """)
                page.wait_for_load_state("networkidle")

            html = page.content()
            final_url = page.url
            context.close()

        return ScrapeResponse(html=html, final_url=final_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
