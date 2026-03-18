import asyncio, logging, re, subprocess
from pathlib import Path
import httpx
logger = logging.getLogger(__name__)
VIRAL_DIR=Path("data/videos/viral")
MAX_MB=50

def _slug(text,n=40):
    import unicodedata
    text=unicodedata.normalize("NFKD",str(text)).encode("ascii","ignore").decode()
    text=re.sub(r"[^a-z0-9]","_",text.lower())
    return re.sub(r"_+","_",text).strip("_")[:n]

def _dl_direto(url,path):
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        with httpx.stream("GET",url,follow_redirects=True,timeout=60,headers={"User-Agent":"Mozilla/5.0"}) as r:
            if r.status_code!=200: return False
            with open(path,"wb") as f:
                for chunk in r.iter_bytes(8192): f.write(chunk)
        mb=path.stat().st_size/1_048_576
        if mb>MAX_MB: path.unlink(); return False
        logger.info(f"Download direto: {path.name} ({mb:.1f}MB)")
        return True
    except Exception as e:
        logger.debug(f"Download direto falhou: {e}"); return False

async def _interceptar_url(page_url):
    from playwright.async_api import async_playwright
    found=None
    async with async_playwright() as p:
        try:
            browser=await p.chromium.connect_over_cdp("http://localhost:9222")
            ctx=browser.contexts[0]; page=await ctx.new_page()
            def on_req(req):
                nonlocal found
                u=req.url
                if any(x in u for x in [".mp4",".m3u8","video","stream"]) and not found:
                    if "shopee" in u or "cdn" in u.lower(): found=u
            page.on("request",on_req)
            await page.goto(page_url,wait_until="networkidle",timeout=20000)
            await page.wait_for_timeout(4000)
            try: await page.click("video,[class*='video']",timeout=2000); await page.wait_for_timeout(2000)
            except: pass
            await page.close()
        except Exception as e: logger.debug(f"Interceptacao falhou: {e}")
    return found

def _dl_ytdlp(url,path):
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        r=subprocess.run(["yt-dlp","--format","mp4/best[ext=mp4]","--output",str(path),"--max-filesize",f"{MAX_MB}M","--quiet","--no-playlist",url],timeout=90,capture_output=True)
        return path.exists() and r.returncode==0
    except Exception as e:
        logger.debug(f"yt-dlp falhou: {e}"); return False

async def baixar_video_viral(video,idx=0):
    slug=f"viral_{idx:03d}_{_slug(video.produto or 'video')}"
    path=VIRAL_DIR/f"{slug}.mp4"
    if path.exists(): return str(path)
    logger.info(f"Baixando #{idx}: {slug}")
    if video.video_url and ".mp4" in video.video_url:
        if _dl_direto(video.video_url,path): return str(path)
    if video.page_url:
        real_url=await _interceptar_url(video.page_url)
        if real_url:
            video.video_url=real_url
            if _dl_direto(real_url,path): return str(path)
    url=video.page_url or video.video_url
    if url and _dl_ytdlp(url,path): return str(path)
    logger.warning(f"Download falhou: {slug}"); return None

async def baixar_lote(videos,max_concurrent=2):
    resultados={}; sem=asyncio.Semaphore(max_concurrent)
    async def task(v,i):
        async with sem:
            path=await baixar_video_viral(v,i)
            resultados[v.page_url or v.video_url]=path
            await asyncio.sleep(2)
    await asyncio.gather(*[task(v,i) for i,v in enumerate(videos,1)])
    ok=sum(1 for x in resultados.values() if x)
    logger.info(f"Downloads: {ok}/{len(videos)}")
    return resultados
