import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
HISTORICO = Path("data/viral_history.json")

def _load() -> set:
    try:
        if HISTORICO.exists():
            return set(json.loads(HISTORICO.read_text("utf-8")).get("repostados",[]))
    except: pass
    return set()

def _save(urls:set):
    HISTORICO.parent.mkdir(parents=True,exist_ok=True)
    existing=_load()
    HISTORICO.write_text(json.dumps({"repostados":list(existing|urls),"total":len(existing|urls),"atualizado":datetime.now().isoformat()},ensure_ascii=False,indent=2),"utf-8")

def selecionar_top_virais(videos,top_n=5,min_score=15.0,min_views=300):
    ja=_load()
    candidatos=[v for v in videos if v.viral_score>=min_score and v.views>=min_views and (v.video_url or v.page_url) and v.page_url not in ja and v.video_url not in ja]
    logger.info(f"{len(videos)} coletados -> {len(candidatos)} candidatos -> top {min(top_n,len(candidatos))}")
    for i,v in enumerate(candidatos[:top_n],1):
        logger.info(f"  #{i} Score={v.viral_score:.1f} | Views={v.views:,} | {v.produto[:40]}")
    return candidatos[:top_n]

def marcar_repostados(videos):
    urls={v.page_url for v in videos if v.page_url}|{v.video_url for v in videos if v.video_url}
    _save(urls)
    for v in videos: v.status="repostado"
    logger.info(f"{len(videos)} marcados no historico")

def load_historico_completo():
    try:
        if HISTORICO.exists(): return json.loads(HISTORICO.read_text("utf-8"))
    except: pass
    return {"repostados":[],"total":0}
