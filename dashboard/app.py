"""
Streamlit Dashboard — Shopee Affiliate Automation Bot

Run: streamlit run dashboard/app.py
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Shopee Affiliate Bot",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

EXCEL_PATH = "data/output.xlsx"
LOG_PATH = "logs/affiliate_bot.log"
MANUAL_QUEUE_PATH = "data/manual_queue.json"

STATUS_COLORS = {
    "pendente": "#FFA500",
    "publicado_tiktok": "#00CC44",
    "publicado_shopee": "#00AAFF",
    "fila_manual": "#9B59B6",
    "falhou_tiktok": "#FF3333",
    "falhou_shopee": "#FF6666",
}


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
        return df
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar Excel: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=15)
def load_log(lines: int = 50) -> str:
    try:
        all_lines = Path(LOG_PATH).read_text(encoding="utf-8").splitlines()
        return "\n".join(all_lines[-lines:])
    except FileNotFoundError:
        return "Log não encontrado. Execute o pipeline primeiro."
    except Exception as e:
        return f"Erro ao ler log: {e}"


@st.cache_data(ttl=30)
def load_manual_queue() -> list:
    try:
        return json.loads(Path(MANUAL_QUEUE_PATH).read_text(encoding="utf-8"))
    except Exception:
        return []


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _pipeline_is_running() -> bool:
    """Verifica se o pipeline já está rodando."""
    import psutil
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmd = " ".join(proc.info['cmdline'] or [])
            if "main.py" in cmd and "--dashboard" not in cmd:
                return True
        except Exception:
            pass
    return False


def render_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/shopee.png", width=60)
        st.title("Shopee Affiliate Bot")
        st.markdown("---")

        # Status do pipeline
        running = _pipeline_is_running()
        if running:
            st.warning("⏳ Pipeline em execução...")
        else:
            st.success("✅ Pronto para executar")

        st.markdown("---")
        st.subheader("🚀 Controles")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶ Executar\nPipeline", use_container_width=True, type="primary", disabled=running):
                subprocess.Popen(
                    [sys.executable, "main.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(Path(__file__).parent.parent),
                )
                st.success("✅ Iniciado!")
                st.info("Aguarde ~2min e clique em Atualizar.")

        with col2:
            if st.button("🔁 Atualizar", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        if st.button("🧪 Teste (Dry-Run)", use_container_width=True):
            subprocess.Popen(
                [sys.executable, "main.py", "--dry-run"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).parent.parent),
            )
            st.success("Dry-run iniciado! Clique Atualizar em 10s.")

        st.markdown("---")

        # Download do Excel
        try:
            excel_bytes = Path(EXCEL_PATH).read_bytes()
            st.download_button(
                label="⬇ Baixar Excel",
                data=excel_bytes,
                file_name=f"shopee_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            st.caption("Excel ainda não gerado.")

        st.markdown("---")
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        st.caption("♻️ Dados atualizam a cada 30s.")


# ── KPI Row ───────────────────────────────────────────────────────────────────

def render_schedule_info():
    """Mostra os próximos horários de postagem automática."""
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        times = os.getenv("POST_TIMES", "09:00,13:00,20:00").split(",")
        whatsapp = os.getenv("WHATSAPP_PHONE", "")

        st.subheader("🕐 Agendamento Automático")
        cols = st.columns(len(times) + 1)
        for i, t in enumerate(times):
            cols[i].metric(f"Postagem {i+1}", t.strip())

        if whatsapp and len(whatsapp) > 5:
            cols[-1].metric("📱 WhatsApp", f"****{whatsapp[-4:]}")
        else:
            cols[-1].warning("⚠️ WhatsApp não configurado")

        st.caption("Configure horários em POST_TIMES no arquivo .env | `python main.py --all` para ativar")
    except Exception:
        pass


def render_kpis(df: pd.DataFrame):
    st.subheader("Resumo")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    total = len(df)
    ai_ok = len(df[df.get("overlay", pd.Series(dtype=str)).str.len() > 5]) if "overlay" in df.columns else 0
    published = len(df[df["status_agendamento"].str.startswith("publicado", na=False)]) if "status_agendamento" in df.columns else 0
    pending = len(df[df["status_agendamento"] == "pendente"]) if "status_agendamento" in df.columns else 0
    avg_new = df["comissao_novo"].mean() if "comissao_novo" in df.columns and total > 0 else 0
    avg_existing = df["comissao_atual"].mean() if "comissao_atual" in df.columns and total > 0 else 0

    c1.metric("Total Produtos", total)
    c2.metric("Copy Gerado", ai_ok)
    c3.metric("Publicados", published)
    c4.metric("Pendentes", pending)
    c5.metric("Comissão Média (Novo)", f"{avg_new:.1f}%")
    c6.metric("Comissão Média (Atual)", f"{avg_existing:.1f}%")


# ── Products Table ────────────────────────────────────────────────────────────

def render_products_table(df: pd.DataFrame):
    st.subheader("Produtos")

    if df.empty:
        st.info("Nenhum produto ainda. Execute o pipeline para começar.")
        return

    # Filter
    col1, col2 = st.columns(2)
    with col1:
        status_options = ["Todos"] + sorted(df["status_agendamento"].dropna().unique().tolist()) if "status_agendamento" in df.columns else ["Todos"]
        selected_status = st.selectbox("Filtrar por status", status_options)
    with col2:
        search = st.text_input("Buscar produto", placeholder="Digite o nome...")

    filtered = df.copy()
    if selected_status != "Todos" and "status_agendamento" in filtered.columns:
        filtered = filtered[filtered["status_agendamento"] == selected_status]
    if search and "produto" in filtered.columns:
        filtered = filtered[filtered["produto"].str.contains(search, case=False, na=False)]

    # Display columns
    display_cols = [c for c in ["produto", "comissao_novo", "comissao_atual", "overlay", "hashtags", "status_agendamento", "data_publicacao"] if c in filtered.columns]

    def _color_status(val):
        color = STATUS_COLORS.get(str(val), "#FFFFFF")
        return f"background-color: {color}22; color: {color}; font-weight: bold;"

    styled = filtered[display_cols].style
    if "status_agendamento" in display_cols:
        styled = styled.applymap(_color_status, subset=["status_agendamento"])

    st.dataframe(styled, use_container_width=True, height=400)
    st.caption(f"Mostrando {len(filtered)} de {len(df)} produtos")


# ── Charts ────────────────────────────────────────────────────────────────────

def render_charts(df: pd.DataFrame):
    if df.empty:
        return

    st.subheader("Análise")
    col1, col2 = st.columns(2)

    with col1:
        if "status_agendamento" in df.columns:
            status_counts = df["status_agendamento"].value_counts().reset_index()
            status_counts.columns = ["Status", "Quantidade"]
            fig = px.bar(
                status_counts,
                x="Status",
                y="Quantidade",
                title="Produtos por Status de Agendamento",
                color="Status",
                color_discrete_map={k: v for k, v in STATUS_COLORS.items()},
            )
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "comissao_novo" in df.columns:
            fig2 = px.histogram(
                df,
                x="comissao_novo",
                nbins=20,
                title="Distribuição de Comissão (Novos Compradores)",
                labels={"comissao_novo": "Comissão (%)"},
                color_discrete_sequence=["#FF6B35"],
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)


# ── Manual Queue ──────────────────────────────────────────────────────────────

def render_manual_queue():
    queue = load_manual_queue()
    if not queue:
        return

    st.subheader(f"Fila Manual de Postagem ({len(queue)} itens)")
    st.warning("Estes produtos precisam de vídeo para ser publicados. Grave o vídeo e poste manualmente com o copy abaixo.")

    for item in queue[-5:]:  # Show last 5
        with st.expander(f"📦 {item.get('produto', 'Produto')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Overlay (tela):** `{item.get('overlay', '')}`")
                st.markdown(f"**Hashtags:** `{item.get('hashtags', '')}`")
                st.markdown(f"**Link:** {item.get('link_afiliado', '')}")
            with col2:
                st.text_area("Legenda (copiar)", item.get("legenda", ""), height=120, key=f"q_{item.get('adicionado_em', '')}")


# ── Log Viewer ────────────────────────────────────────────────────────────────

def render_log_viewer():
    with st.expander("Log do Sistema (últimas 50 linhas)"):
        log_content = load_log()
        st.code(log_content, language="text")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    render_sidebar()

    st.title("🛒 Shopee Affiliate Bot — Dashboard")
    st.markdown("Automação de produtos afiliados com geração de copy por IA e agendamento de posts.")
    st.markdown("---")

    df = load_data()

    render_schedule_info()
    st.markdown("---")
    render_kpis(df)
    st.markdown("---")
    render_products_table(df)
    st.markdown("---")
    render_charts(df)
    render_manual_queue()
    st.markdown("---")
    render_log_viewer()


if __name__ == "__main__":
    main()
