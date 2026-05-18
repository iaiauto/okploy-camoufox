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
        mobile_ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )

        with Camoufox(headless=True) as browser:
            ctx_args = {
                "viewport": viewport,
                "extra_http_headers": req.headers or {},
            }
            if req.mobile:
                ctx_args["user_agent"] = mobile_ua

            context = browser.new_context(**ctx_args)
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
