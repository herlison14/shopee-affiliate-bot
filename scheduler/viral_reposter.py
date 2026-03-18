import json, logging, re
from pathlib import Path
import anthropic
logger = logging.getLogger(__name__)

def _gerar_copy(video,settings):
    client=anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt=f"""Voce e um Growth Hacker viral para o publico brasileiro.
Um video viralizou no Shopee com {video.views:,} views.
Reposte com copy mais impactante e SEU link afiliado.
PRODUTO: {video.produto or "Produto Shopee"}
VIEWS: {video.views:,} | LIKES: {video.likes:,}
LINK: {video.link_produto or ""}
Responda APENAS em JSON:
{{"overlay":"max 5 palavras IMPACTANTES","legenda":"legenda completa com link e emojis","hashtags":"#shopee #viral (max 10 tags)"}}"""
    resp=client.messages.create(model=settings.anthropic_model,max_tokens=400,messages=[{"role":"user","content":prompt}])
    raw=resp.content[0].text
    m=re.search(r"\{.*\}",raw,re.DOTALL)
    if m: return json.loads(m.group())
    return {"overlay":"NAO PERCA ISSO","legenda":f"Produto viral! {video.link_produto} ","hashtags":"#shopee #viral #oferta"}

async def repostar_video(video,video_path,settings):
    if not Path(video_path).exists():
        return {"status":"failed","error":"arquivo_nao_encontrado"}
    logger.info(f"Repostando: {video.produto[:50]} [score={video.viral_score:.1f}]")
    copy=_gerar_copy(video,settings)
    produto_post={"produto":video.produto or "Produto Viral Shopee","link_afiliado":video.link_produto or "","preco":video.preco,"overlay":copy.get("overlay",""),"legenda":copy.get("legenda",""),"hashtags":copy.get("hashtags","")}
    from scheduler.shopee_video_poster import post_shopee_video
    resultado=post_shopee_video(produto_post,video_path,settings)
    if resultado["status"]=="success": video.status="repostado"; logger.info(f"Repostado: {video.produto[:50]}")
    else: video.status="falhou"; logger.error(f"Falhou: {resultado.get('error')}")
    return resultado
