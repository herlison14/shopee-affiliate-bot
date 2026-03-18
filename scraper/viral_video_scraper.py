import asyncio, logging, math, re
from dataclasses import dataclass
logger = logging.getLogger(__name__)

FEED_URLS=["https://affiliate.shopee.com.br/creative/feed","https://affiliate.shopee.com.br/creative/video","https://shopee.com.br/m/shopee-video"]

@dataclass
class ViralVideo:
    video_url:str=""
    page_url:str=""
    thumbnail_url:str=""
    produto:str=""
    link_produto:str=""
    criador:str=""
    views:int=0
    likes:int=0
    shares:int=0
    comentarios:int=0
    duracao_seg:int=0
    viral_score:float=0.0
    preco:float=0.0
    comissao:float=0.0
    status:str="pendente"
    def to_dict(self): return self.__dict__.copy()

def _parse_num(t) -> int:
    t=str(t).upper().strip().replace(",",".")
    try:
        if "M" in t: return int(float(t.replace("M",""))*1_000_000)
        if "K" in t: return int(float(t.replace("K",""))*1_000)
        return int(float(re.sub(r"[^\d.]","",t))) if t else 0
    except: return 0

def calcular_viral_score(v) -> float:
    if v.views==0: return 0.0
    eng=(v.likes+v.shares*3+v.comentarios*2)/max(v.views,1)
    se=min(eng*100,40)
    sv=min(math.log10(max(v.views,1))*8,30)
    sd=15 if 15<=v.duracao_seg<=60 else (5 if v.duracao_seg<15 else 8)
    sc=min(v.comissao*0.3,15)
    return round(min(se+sv+sd+sc,100),2)

_JS="""() => {
    const videos=[];
    const cards=document.querySelectorAll('[class*="video-card"],[class*="VideoCard"],[class*="creative-video"],[data-testid*="video"],[class*="feed-item"],[class*="content-card"]');
    cards.forEach(card=>{
        const v={};
        const ve=card.querySelector("video source,video");
        v.video_url=ve?.src||ve?.getAttribute("data-src")||"";
        const img=card.querySelector("img");
        v.thumbnail_url=img?.src||"";
        const lk=card.querySelector("a[href*=shopee]");
        v.page_url=lk?.href||"";
        const t=card.querySelector("[class*=title],[class*=name],h3,h4");
        v.produto=t?.textContent?.trim()||"";
        const nums=Array.from(card.querySelectorAll("*")).map(el=>el.childNodes).flatMap(n=>Array.from(n)).filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).filter(t=>/^[\\d.,]+[KkMm]?$/.test(t));
        v.views=nums[0]||"0"; v.likes=nums[1]||"0"; v.shares=nums[2]||"0";
        if(v.page_url||v.video_url||v.produto) videos.push(v);
    });
    return videos;
}"""

async def scrape_viral_videos(settings,max_videos:int=30,min_views:int=300):
    from playwright.async_api import async_playwright
    videos=[]
    async with async_playwright() as p:
        try:
            browser=await p.chromium.connect_over_cdp("http://localhost:9222")
            ctx=browser.contexts[0]
            page=await ctx.new_page()
            logger.info("CDP conectado")
        except Exception as e:
            logger.error(f"Chrome CDP indisponivel: {e}")
            return []
        for url in FEED_URLS:
            if len(videos)>=max_videos: break
            try:
                await page.goto(url,wait_until="networkidle",timeout=30000)
                await page.wait_for_timeout(3000)
                for _ in range(6):
                    await page.evaluate("window.scrollBy(0,window.innerHeight)")
                    await page.wait_for_timeout(1200)
                raw=await page.evaluate(_JS)
                for r in raw:
                    vv=ViralVideo(video_url=r.get("video_url",""),page_url=r.get("page_url",""),thumbnail_url=r.get("thumbnail_url",""),produto=r.get("produto",""),views=_parse_num(r.get("views",0)),likes=_parse_num(r.get("likes",0)),shares=_parse_num(r.get("shares",0)))
                    vv.viral_score=calcular_viral_score(vv)
                    if vv.views>=min_views or vv.video_url: videos.append(vv)
                logger.info(f"{len(raw)} cards em {url}")
            except Exception as e:
                logger.warning(f"Erro em {url}: {e}")
        await page.close()
    videos.sort(key=lambda x:x.viral_score,reverse=True)
    return videos[:max_videos]
