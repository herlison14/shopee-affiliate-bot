"""
🤖 ROBO MESTRE — Shopee Affiliate Bot
Loop autonomo: produtos afiliados + videos virais
Rodar: python robot_master.py
"""
import asyncio, json, logging, subprocess, sys, threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
CYCLE_HOURS=6; TOP_PRODUTOS=5; TOP_VIRAIS=5
MIN_VIRAL_SCORE=15.0; MIN_VIRAL_VIEWS=300; DELAY_POSTS=45
STATE_PATH=Path("data/robot_state.json")

def _salvar_estado(e):
    STATE_PATH.parent.mkdir(parents=True,exist_ok=True)
    e["atualizado"]=datetime.now().isoformat()
    STATE_PATH.write_text(json.dumps(e,ensure_ascii=False,indent=2),"utf-8")

def _estado_inicial():
    return {"status":"iniciando","ciclo_atual":0,"ultimo_ciclo":None,"proximo_ciclo":None,
            "produtos_postados_total":0,"virais_repostados_total":0,"erros_total":0,
            "ultimo_log":"","virais_coletados":[],"produtos_coletados":[]}

async def _buscar_video_youtube(produto):
    import re,subprocess
    nome=produto.get("produto","")
    slug=re.sub(r"[^a-z0-9_]","",nome.lower().replace(" ","_"))[:40]
    path=Path(f"data/videos/{slug}.mp4")
    if path.exists(): return str(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        r=subprocess.run(["yt-dlp",f"ytsearch3:{nome} review shopee produto","--match-filter","duration < 60","--format","mp4/best[ext=mp4]","--output",str(path),"--max-filesize","50M","--quiet","--no-playlist"],timeout=90,capture_output=True)
        return str(path) if path.exists() else None
    except: return None

async def ciclo_produtos(settings,estado):
    logger.info("="*50+"\n📦 MODO A — PRODUTOS AFILIADOS\n"+"="*50)
    estado["ultimo_log"]="Scraping produtos afiliados..."; _salvar_estado(estado)
    from scraper.shopee_affiliate import scrape_all_products
    produtos=await scrape_all_products(settings)
    if not produtos: logger.warning("Nenhum produto coletado"); return 0
    from scraper.product_ranker import rank_products
    top=rank_products(produtos,top_n=TOP_PRODUTOS)
    estado["produtos_coletados"]=[{"produto":p.get("produto","")[:50],"rating":p.get("rating",0),"comissao":p.get("comissao_atual",0),"preco":p.get("preco",0)} for p in top]
    _salvar_estado(estado)
    from ai.copy_generator import generate_batch
    top=generate_batch(top,settings.anthropic_api_key,settings.anthropic_model,settings.campaign_name,settings.social_network)
    postados=0
    for produto in top:
        estado["ultimo_log"]=f"Processando: {produto.get('produto','')[:40]}"; _salvar_estado(estado)
        video_path=await _buscar_video_youtube(produto)
        if not video_path: continue
        from scheduler.shopee_video_poster import post_shopee_video
        resultado=post_shopee_video(produto,video_path,settings)
        if resultado["status"]=="success":
            postados+=1; logger.info(f"✅ [{postados}] {produto.get('produto','')[:50]}")
        else: logger.error(f"❌ {produto.get('produto','')[:40]}: {resultado.get('error')}")
        await asyncio.sleep(DELAY_POSTS)
    logger.info(f"📦 Produtos: {postados}/{len(top)} postados")
    return postados

async def ciclo_viral(settings,estado):
    logger.info("="*50+"\n🔥 MODO B — VIDEOS VIRAIS\n"+"="*50)
    estado["ultimo_log"]="Buscando videos virais..."; _salvar_estado(estado)
    from scraper.viral_video_scraper import scrape_viral_videos
    videos=await scrape_viral_videos(settings,max_videos=30,min_views=MIN_VIRAL_VIEWS)
    if not videos: logger.warning("Nenhum video viral encontrado"); return 0
    from scraper.viral_video_ranker import selecionar_top_virais,marcar_repostados
    top_virais=selecionar_top_virais(videos,TOP_VIRAIS,MIN_VIRAL_SCORE,MIN_VIRAL_VIEWS)
    if not top_virais: logger.info("Nenhum video novo passou nos criterios"); return 0
    estado["virais_coletados"]=[v.to_dict() for v in top_virais]; _salvar_estado(estado)
    from scheduler.viral_video_downloader import baixar_lote
    estado["ultimo_log"]=f"Baixando {len(top_virais)} videos virais..."; _salvar_estado(estado)
    downloads=await baixar_lote(top_virais,max_concurrent=2)
    from scheduler.viral_reposter import repostar_video
    repostados=[]
    for video in top_virais:
        video_path=downloads.get(video.page_url or video.video_url)
        if not video_path: video.status="falhou"; continue
        estado["ultimo_log"]=f"Repostando: {video.produto[:40]}"; _salvar_estado(estado)
        resultado=await repostar_video(video,video_path,settings)
        if resultado["status"]=="success": repostados.append(video)
        await asyncio.sleep(DELAY_POSTS)
    if repostados: marcar_repostados(repostados)
    logger.info(f"🔥 Virais: {len(repostados)}/{len(top_virais)} repostados")
    return len(repostados)

async def main():
    from config.settings import Settings
    settings=Settings()
    estado=_estado_inicial(); estado["status"]="rodando"; _salvar_estado(estado)
    logger.info("🤖 ROBO MESTRE INICIADO"); logger.info(f"Ciclos a cada {CYCLE_HOURS}h")
    logger.info(f"Top produtos/ciclo: {TOP_PRODUTOS} | Top virais/ciclo: {TOP_VIRAIS}")
    logger.info("Dashboard: http://localhost:8501\nCtrl+C para parar\n")
    ciclo_num=0
    while True:
        ciclo_num+=1; now=datetime.now()
        estado["ciclo_atual"]=ciclo_num; estado["ultimo_ciclo"]=now.isoformat(); estado["status"]="executando"; _salvar_estado(estado)
        logger.info(f"\n{'='*60}\n🔄 CICLO #{ciclo_num} — {now.strftime('%d/%m/%Y %H:%M')}\n{'='*60}")
        try:
            pp,vr=await asyncio.gather(ciclo_produtos(settings,estado),ciclo_viral(settings,estado),return_exceptions=True)
            if isinstance(pp,Exception): logger.error(f"Erro modo A: {pp}"); pp=0
            if isinstance(vr,Exception): logger.error(f"Erro modo B: {vr}"); vr=0
            estado["produtos_postados_total"]+=pp; estado["virais_repostados_total"]+=vr
        except KeyboardInterrupt:
            logger.info("Parado pelo usuario"); estado["status"]="parado"; _salvar_estado(estado); break
        except Exception as e:
            logger.error(f"Erro critico: {e}"); estado["erros_total"]+=1
        from datetime import timedelta
        proximo=datetime.fromtimestamp(now.timestamp()+CYCLE_HOURS*3600)
        estado["status"]="aguardando"; estado["proximo_ciclo"]=proximo.isoformat()
        estado["ultimo_log"]=f"Ciclo #{ciclo_num} concluido. Proximo: {proximo.strftime('%H:%M')}"
        _salvar_estado(estado)
        logger.info(f"✅ Ciclo #{ciclo_num} OK | Produtos total: {estado['produtos_postados_total']} | Virais total: {estado['virais_repostados_total']}")
        logger.info(f"Proximo ciclo: {proximo.strftime('%d/%m/%Y %H:%M')}\n")
        await asyncio.sleep(CYCLE_HOURS*3600)

if __name__=="__main__":
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(message)s",handlers=[logging.FileHandler("logs/robot_master.log",encoding="utf-8"),logging.StreamHandler()])
    asyncio.run(main())
