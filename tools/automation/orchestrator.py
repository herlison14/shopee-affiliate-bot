"""
Orquestrador local do pipeline completo de afiliado Shopee.

Fluxo por produto: descobre -> gera link de afiliado -> cria campanha com IA
(via MCP) -> busca video relevante -> (opcional) tenta postar no Shopee Videos
-> atualiza status REAL da campanha (nunca finge sucesso).

Roda na MAQUINA DO USUARIO, nao no Render -- depende do Chrome local com CDP
(porta 9222) logado em affiliate.shopee.com.br.

Uso:
    set SHOPEEVIRAL_MCP_URL=https://shopee-viral-api.onrender.com/agent/SEU_TOKEN/mcp
    python tools/automation/orchestrator.py --uma-vez
    python tools/automation/orchestrator.py --ciclo-horas 6 --auto-postar
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tools/
from gerar_link_e_campanha import chamar_mcp_tool  # noqa: E402

from automation.discovery import descobrir_produtos, rankear_produtos  # noqa: E402
from automation.shopee_poster import postar_video_async  # noqa: E402
from automation.video_match import buscar_e_baixar_video_relevante  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("orquestrador")


def _mcp_url() -> str:
    url = os.environ.get("SHOPEEVIRAL_MCP_URL")
    if not url:
        raise SystemExit("Defina a variavel de ambiente SHOPEEVIRAL_MCP_URL com sua URL pessoal de MCP.")
    return url


def _resultado_tool(resposta: dict) -> dict:
    return json.loads(resposta["content"][0]["text"])


async def processar_produto(mcp_url: str, produto: dict, auto_postar: bool) -> None:
    nome = produto["produto"]
    url_produto = produto["link_original"]
    link_afiliado = produto.get("link_afiliado")
    link_falhou = link_afiliado == produto.get("link_original")

    dedup = _resultado_tool(
        chamar_mcp_tool(mcp_url, "existe_campanha_para_produto", {"url_produto": url_produto})
    )
    if dedup["existe"]:
        logger.info("Pulando '%s': campanha ja existe para esse produto.", nome[:60])
        return

    campanha = _resultado_tool(
        chamar_mcp_tool(
            mcp_url,
            "criar_campanha",
            {"nome_produto": nome, "url_produto": url_produto, "link_afiliado": link_afiliado},
        )
    )
    campaign_id = campanha["id"]
    logger.info("Campanha criada: '%s' (%s)", nome[:60], campaign_id)

    if link_falhou:
        chamar_mcp_tool(
            mcp_url,
            "atualizar_status_campanha",
            {
                "campaign_id": campaign_id,
                "status": "needs_review",
                "detalhe": "geracao do link de afiliado falhou -- o link salvo e o link original, "
                "sem rastreio de comissao. Gere o link manualmente.",
            },
        )
        return

    video_result = await asyncio.to_thread(buscar_e_baixar_video_relevante, nome)
    if not video_result.get("video_path"):
        chamar_mcp_tool(
            mcp_url,
            "atualizar_status_campanha",
            {"campaign_id": campaign_id, "status": "needs_review", "detalhe": f"sem video: {video_result['motivo']}"},
        )
        logger.info("Sem video relevante para '%s': %s", nome[:60], video_result["motivo"])
        return

    if not auto_postar:
        chamar_mcp_tool(
            mcp_url,
            "atualizar_status_campanha",
            {
                "campaign_id": campaign_id,
                "status": "scheduled",
                "detalhe": f"video pronto em {video_result['video_path']} ({video_result['motivo']}); "
                "auto-postagem desligada, poste manualmente ou rode com --auto-postar.",
            },
        )
        logger.info("Campanha '%s' pronta (video baixado), aguardando postagem manual.", nome[:60])
        return

    post_result = await postar_video_async(
        nome_produto=nome,
        video_path=video_result["video_path"],
        legenda=campanha.get("legenda", ""),
        hashtags=campanha.get("hashtags", ""),
        link_afiliado=link_afiliado or url_produto,
    )

    if post_result["confirmed"]:
        chamar_mcp_tool(
            mcp_url,
            "atualizar_status_campanha",
            {
                "campaign_id": campaign_id,
                "status": "posted",
                "detalhe": post_result["detalhe"],
                "url_postagem": post_result["post_url"],
            },
        )
        logger.info("Postado com sucesso confirmado: '%s'", nome[:60])
    else:
        chamar_mcp_tool(
            mcp_url,
            "atualizar_status_campanha",
            {"campaign_id": campaign_id, "status": "needs_review", "detalhe": post_result["detalhe"]},
        )
        logger.warning("Postagem nao confirmada para '%s': %s", nome[:60], post_result["detalhe"])


async def executar_ciclo(max_produtos: int, min_comissao: float, top_n: int, auto_postar: bool) -> None:
    mcp_url = _mcp_url()
    logger.info("Descobrindo produtos (max=%d, comissao_min=%.1f%%)...", max_produtos, min_comissao)
    produtos = await descobrir_produtos(max_produtos=max_produtos, min_comissao_pct=min_comissao)
    ranqueados = rankear_produtos(produtos, top_n=top_n)
    logger.info("%d produtos descobertos, processando top %d.", len(produtos), len(ranqueados))

    for produto in ranqueados:
        try:
            await processar_produto(mcp_url, produto, auto_postar)
        except Exception:
            logger.exception("Erro processando produto '%s'", produto.get("produto", "?")[:60])


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline automatico de afiliado Shopee.")
    parser.add_argument("--uma-vez", action="store_true", help="Roda um ciclo e sai (nao fica em loop).")
    parser.add_argument("--ciclo-horas", type=float, default=6, help="Intervalo entre ciclos, em horas.")
    parser.add_argument("--max-produtos", type=int, default=20)
    parser.add_argument("--min-comissao", type=float, default=8.0)
    parser.add_argument("--top-n", type=int, default=5, help="Quantos produtos processar por ciclo.")
    parser.add_argument(
        "--auto-postar",
        action="store_true",
        help="Posta de fato no Shopee Videos. Sem essa flag, so prepara (link+campanha+video) "
        "e deixa a postagem para voce fazer manualmente -- modo seguro, recomendado para os primeiros testes.",
    )
    args = parser.parse_args()

    if args.uma_vez:
        asyncio.run(executar_ciclo(args.max_produtos, args.min_comissao, args.top_n, args.auto_postar))
        return

    logger.info("Loop continuo iniciado: 1 ciclo a cada %.1fh. Ctrl+C para parar.", args.ciclo_horas)
    while True:
        asyncio.run(executar_ciclo(args.max_produtos, args.min_comissao, args.top_n, args.auto_postar))
        logger.info("Ciclo concluido, dormindo %.1fh...", args.ciclo_horas)
        time.sleep(args.ciclo_horas * 3600)


if __name__ == "__main__":
    main()
