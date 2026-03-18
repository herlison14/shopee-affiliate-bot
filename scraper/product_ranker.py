import logging, math, re
logger = logging.getLogger(__name__)

def _parse_sold(s) -> int:
    t = str(s).upper().replace(",",".")
    t = re.sub(r"[^\d.KM]","",t)
    try:
        if "M" in t: return int(float(t.replace("M",""))*1_000_000)
        if "K" in t: return int(float(t.replace("K",""))*1_000)
        return int(float(t)) if t else 0
    except: return 0

def rank_products(products:list, top_n:int=10) -> list:
    def score(p):
        rating  = min(float(p.get("rating",0)),5.0)
        sold    = min(_parse_sold(p.get("sold",0)),50_000)
        comissao= float(p.get("comissao_atual",0))/100
        preco   = float(p.get("preco",999))
        ps      = 1.0 if 20<=preco<=300 else 0.4
        sn      = math.log10(max(sold,1))/math.log10(50_000)
# Cria estrutura de pastas
New-Item -ItemType Directory -Force -Path "scraper","data\videos\viral","logs" | Out-Null

# ── product_ranker.py ─────────────────────────────────────────
@'
import logging, math, re
logger = logging.getLogger(__name__)

def _parse_sold(s) -> int:
    t = str(s).upper().replace(",",".")
    t = re.sub(r"[^\d.KM]","",t)
    try:
        if "M" in t: return int(float(t.replace("M",""))*1_000_000)
        if "K" in t: return int(float(t.replace("K",""))*1_000)
        return int(float(t)) if t else 0
    except: return 0

def rank_products(products:list, top_n:int=10) -> list:
    def score(p):
        rating  = min(float(p.get("rating",0)),5.0)
        sold    = min(_parse_sold(p.get("sold",0)),50_000)
        comissao= float(p.get("comissao_atual",0))/100
        preco   = float(p.get("preco",999))
        ps      = 1.0 if 20<=preco<=300 else 0.4
        sn      = math.log10(max(sold,1))/math.log10(50_000)
        return (rating/5.0)*0.4+comissao*0.3+sn*0.2+ps*0.1
    ranked = sorted(products,key=score,reverse=True)
    filtered = [p for p in ranked if float(p.get("rating",0))>=4.0 and float(p.get("comissao_atual",0))>=5.0]
    logger.info(f"Ranking: {len(products)} -> {len(filtered)} qualificados -> top {min(top_n,len(filtered))}")
    return filtered[:top_n]
