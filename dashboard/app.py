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
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Shopee Affiliate Bot",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Tema Shopee */
    :root {
        --shopee-orange: #EE4D2D;
        --shopee-light: #FFF3F0;
        --shopee-dark: #CC3000;
    }

    /* Fundo geral */
    .stApp { background-color: #F7F8FA; }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #EE4D2D 0%, #FF7337 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(238,77,45,0.3);
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p  { color: rgba(255,255,255,0.85); margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        border-left: 4px solid #EE4D2D;
        margin-bottom: 0.5rem;
    }
    .kpi-label { font-size: 0.78rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .kpi-value { font-size: 1.9rem; font-weight: 700; color: #1A1A2E; line-height: 1.2; }
    .kpi-sub   { font-size: 0.78rem; color: #666; margin-top: 0.15rem; }
    .kpi-green { border-left-color: #00C851; }
    .kpi-blue  { border-left-color: #007BFF; }
    .kpi-purple{ border-left-color: #9B59B6; }
    .kpi-gold  { border-left-color: #F39C12; }
    .kpi-teal  { border-left-color: #1ABC9C; }

    /* Seção */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1A1A2E;
        margin: 1.5rem 0 0.8rem 0;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Produto card na fila manual */
    .product-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 0.8rem;
        border: 1px solid #F0F0F0;
    }

    /* Sidebar */
    .sidebar-btn { border-radius: 8px !important; }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-orange  { background: #FFF3EE; color: #EE4D2D; }
    .badge-green   { background: #E8F8F0; color: #00C851; }
    .badge-blue    { background: #EEF5FF; color: #007BFF; }
    .badge-purple  { background: #F5EEFF; color: #9B59B6; }
    .badge-red     { background: #FFEAEA; color: #FF3333; }

    /* Ganho potencial destaque */
    .ganho-destaque {
        background: linear-gradient(135deg, #F39C12 0%, #F7C948 100%);
        border-radius: 12px;
        padding: 1rem 1.4rem;
        color: white;
        margin-bottom: 1rem;
    }
    .ganho-destaque h2 { color: white; margin: 0; font-size: 2.2rem; }
    .ganho-destaque p  { color: rgba(255,255,255,0.9); margin: 0.2rem 0 0 0; font-size: 0.9rem; }

    /* Tabela */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* Input search */
    .stTextInput input { border-radius: 8px !important; }
    .stSelectbox select { border-radius: 8px !important; }

    /* Slider */
    .stSlider { padding: 0 0.5rem; }
</style>
""", unsafe_allow_html=True)

EXCEL_PATH = "data/output.xlsx"
LOG_PATH = "logs/affiliate_bot.log"
MANUAL_QUEUE_PATH = "data/manual_queue.json"

STATUS_COLORS = {
    "pendente": "#EE4D2D",
    "publicado_tiktok": "#00C851",
    "publicado_shopee": "#007BFF",
    "fila_manual": "#9B59B6",
    "falhou_tiktok": "#FF3333",
    "falhou_shopee": "#FF6666",
}

STATUS_EMOJI = {
    "pendente": "🟠",
    "publicado_tiktok": "✅",
    "publicado_shopee": "🔵",
    "fila_manual": "📋",
    "falhou_tiktok": "❌",
    "falhou_shopee": "❌",
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
def load_log(lines: int = 60) -> str:
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


def _load_env() -> dict:
    try:
        from dotenv import dotenv_values
        return dotenv_values(".env")
    except Exception:
        return {}


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _pipeline_is_running() -> bool:
    try:
        import psutil
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmd = " ".join(proc.info['cmdline'] or [])
                if "main.py" in cmd and "--dashboard" not in cmd:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
            <div style="font-size:2.5rem">🛒</div>
            <div style="font-size:1.1rem; font-weight:700; color:#EE4D2D;">Shopee Affiliate Bot</div>
            <div style="font-size:0.75rem; color:#888;">Automação com IA</div>
        </div>
        """, unsafe_allow_html=True)

        # Status do pipeline
        running = _pipeline_is_running()
        if running:
            st.warning("⏳ Pipeline em execução...")
            st.progress(0.6, text="Processando produtos...")
        else:
            st.success("✅ Pronto para executar")

        st.markdown("---")
        st.markdown("**🚀 Controles**")

        if st.button("▶ Executar Pipeline", use_container_width=True, type="primary", disabled=running):
            subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).parent.parent),
            )
            st.success("✅ Pipeline iniciado!")
            st.info("Aguarde ~15min e clique em Atualizar.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 Atualizar", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("🧪 Dry-Run", use_container_width=True):
                subprocess.Popen(
                    [sys.executable, "main.py", "--dry-run"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(Path(__file__).parent.parent),
                )
                st.success("Iniciado! Atualizar em 10s.")

        st.markdown("---")
        st.markdown("**📥 Exportar**")

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

        # Config info
        env = _load_env()
        times = env.get("POST_TIMES", "09:00,13:00,20:00").split(",")
        st.markdown("**⏰ Postagens agendadas**")
        for t in times:
            st.markdown(f"&nbsp;&nbsp;&nbsp;🕐 `{t.strip()}`")

        whatsapp = env.get("WHATSAPP_PHONE", "")
        if whatsapp:
            st.markdown(f"**📱 WhatsApp:** `****{whatsapp[-4:]}`")

        st.markdown("---")
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        st.caption("♻️ Dados atualizam a cada 30s")


# ── Header ─────────────────────────────────────────────────────────────────────

def render_header():
    now = datetime.now()
    st.markdown(f"""
    <div class="main-header">
        <h1>🛒 Shopee Affiliate Bot</h1>
        <p>Automação de produtos afiliados com IA · {now.strftime('%A, %d de %B de %Y')}</p>
    </div>
    """, unsafe_allow_html=True)


# ── KPIs principais ────────────────────────────────────────────────────────────

def render_kpis(df: pd.DataFrame):
    total = len(df)
    if total == 0:
        st.info("🚀 Nenhum dado ainda. Clique em **Executar Pipeline** na barra lateral para começar!")
        return

    published = len(df[df["status_agendamento"].str.startswith("publicado", na=False)]) if "status_agendamento" in df.columns else 0
    pending   = len(df[df["status_agendamento"] == "pendente"]) if "status_agendamento" in df.columns else 0
    failed    = len(df[df["status_agendamento"].str.startswith("falhou", na=False)]) if "status_agendamento" in df.columns else 0
    ai_ok     = len(df[df["overlay"].str.len() > 5]) if "overlay" in df.columns else 0

    avg_comm  = df["comissao_novo"].mean() if "comissao_novo" in df.columns else 0
    max_comm  = df["comissao_novo"].max()  if "comissao_novo" in df.columns else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-label">Total Produtos</div>
            <div class="kpi-value">{total}</div>
            <div class="kpi-sub">encontrados hoje</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card kpi-green">
            <div class="kpi-label">Copy com IA</div>
            <div class="kpi-value">{ai_ok}</div>
            <div class="kpi-sub">prontos para postar</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card kpi-blue">
            <div class="kpi-label">Publicados</div>
            <div class="kpi-value">{published}</div>
            <div class="kpi-sub">posts no ar</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="kpi-card kpi-purple">
            <div class="kpi-label">Pendentes</div>
            <div class="kpi-value">{pending}</div>
            <div class="kpi-sub">aguardando postagem</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class="kpi-card kpi-gold">
            <div class="kpi-label">Comissão Média</div>
            <div class="kpi-value">{avg_comm:.1f}%</div>
            <div class="kpi-sub">por produto</div>
        </div>""", unsafe_allow_html=True)
    with col6:
        st.markdown(f"""<div class="kpi-card kpi-teal">
            <div class="kpi-label">Maior Comissão</div>
            <div class="kpi-value">{max_comm:.1f}%</div>
            <div class="kpi-sub">produto destaque</div>
        </div>""", unsafe_allow_html=True)


# ── Métricas de Ganho Estimado ─────────────────────────────────────────────────

def render_ganho_estimado(df: pd.DataFrame):
    if df.empty:
        return

    st.markdown('<div class="section-title">💰 Potencial de Ganho Estimado</div>', unsafe_allow_html=True)

    # Slider para configurar estimativa de vendas/dia
    col_slider, col_info = st.columns([2, 1])
    with col_slider:
        vendas_dia = st.slider(
            "📊 Estimativa de vendas por produto / dia",
            min_value=1, max_value=50, value=5,
            help="Quantas vendas você espera por produto por dia. Ajuste conforme seu histórico."
        )
    with col_info:
        st.info(f"Baseado em **{vendas_dia} venda(s)/produto/dia** com seus produtos atuais")

    # Calcula ganhos
    has_preco  = "preco" in df.columns and df["preco"].sum() > 0
    has_ganho  = "ganho_estimado" in df.columns and df["ganho_estimado"].sum() > 0
    has_comm   = "comissao_novo" in df.columns

    if has_ganho:
        ganho_por_venda = df["ganho_estimado"].sum()
    elif has_preco and has_comm:
        ganho_por_venda = (df["preco"] * df["comissao_novo"] / 100).sum()
    elif has_comm:
        # Sem preço: assume ticket médio R$80
        ticket_medio = 80.0
        ganho_por_venda = (df["comissao_novo"] / 100 * ticket_medio).sum()
        st.caption(f"💡 Preço não capturado ainda — usando ticket médio de R$80,00")
    else:
        return

    total_produtos = len(df)
    ganho_dia     = ganho_por_venda * vendas_dia
    ganho_semana  = ganho_dia * 7
    ganho_mes     = ganho_dia * 30

    # Cards de ganho
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="ganho-destaque">
            <p>💰 Ganho / Dia</p>
            <h2>R$ {ganho_dia:,.2f}</h2>
            <p>{total_produtos} produtos × {vendas_dia} vendas</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kpi-card kpi-gold">
            <div class="kpi-label">Ganho / Semana</div>
            <div class="kpi-value">R$ {ganho_semana:,.0f}</div>
            <div class="kpi-sub">em 7 dias</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kpi-card kpi-gold">
            <div class="kpi-label">Ganho / Mês</div>
            <div class="kpi-value">R$ {ganho_mes:,.0f}</div>
            <div class="kpi-sub">em 30 dias</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        comissao_media = df["comissao_novo"].mean() if has_comm else 0
        st.markdown(f"""<div class="kpi-card kpi-teal">
            <div class="kpi-label">Comissão Média</div>
            <div class="kpi-value">{comissao_media:.1f}%</div>
            <div class="kpi-sub">por produto vendido</div>
        </div>""", unsafe_allow_html=True)

    # Top 10 produtos com maior ganho potencial
    st.markdown('<div class="section-title">🏆 Top 10 — Maior Potencial de Ganho</div>', unsafe_allow_html=True)

    df_top = df.copy()
    if has_ganho:
        df_top["_ganho_calc"] = df_top["ganho_estimado"] * vendas_dia
    elif has_preco and has_comm:
        df_top["_ganho_calc"] = df_top["preco"] * df_top["comissao_novo"] / 100 * vendas_dia
    else:
        df_top["_ganho_calc"] = df_top["comissao_novo"] / 100 * 80 * vendas_dia

    df_top = df_top.nlargest(10, "_ganho_calc")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_top["produto"].str[:40],
        x=df_top["_ganho_calc"],
        orientation="h",
        marker=dict(
            color=df_top["_ganho_calc"],
            colorscale=[[0, "#FFD0C5"], [0.5, "#FF7337"], [1, "#EE4D2D"]],
            showscale=False,
        ),
        text=[f"R$ {v:,.2f}/dia" for v in df_top["_ganho_calc"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Ganho estimado: R$ %{x:,.2f}/dia<extra></extra>",
    ))
    fig.update_layout(
        height=400,
        margin=dict(l=0, r=80, t=10, b=0),
        xaxis_title="Ganho estimado (R$/dia)",
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="sans-serif", size=12),
    )
    fig.update_xaxes(gridcolor="#F0F0F0", showgrid=True)
    st.plotly_chart(fig, use_container_width=True)

    # Cenários de ganho
    st.markdown('<div class="section-title">📈 Simulação de Cenários</div>', unsafe_allow_html=True)
    cenarios = [1, 3, 5, 10, 20, 50]
    data_cenarios = []
    for v in cenarios:
        g_dia = ganho_por_venda * v
        data_cenarios.append({
            "Vendas/produto/dia": v,
            "Ganho Diário": f"R$ {g_dia:,.2f}",
            "Ganho Semanal": f"R$ {g_dia*7:,.2f}",
            "Ganho Mensal": f"R$ {g_dia*30:,.2f}",
            "Ganho Anual": f"R$ {g_dia*365:,.2f}",
        })
    df_cen = pd.DataFrame(data_cenarios)
    st.dataframe(df_cen, use_container_width=True, hide_index=True)


# ── Products Table ────────────────────────────────────────────────────────────

def render_products_table(df: pd.DataFrame):
    st.markdown('<div class="section-title">📦 Produtos</div>', unsafe_allow_html=True)

    if df.empty:
        return

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        status_options = ["Todos"] + sorted(df["status_agendamento"].dropna().unique().tolist()) if "status_agendamento" in df.columns else ["Todos"]
        selected_status = st.selectbox("Filtrar por status", status_options, label_visibility="collapsed")
    with col2:
        search = st.text_input("Buscar produto", placeholder="🔍 Buscar por nome...", label_visibility="collapsed")
    with col3:
        st.caption(f"**{len(df)}** produtos")

    filtered = df.copy()
    if selected_status != "Todos" and "status_agendamento" in filtered.columns:
        filtered = filtered[filtered["status_agendamento"] == selected_status]
    if search and "produto" in filtered.columns:
        filtered = filtered[filtered["produto"].str.contains(search, case=False, na=False)]

    display_cols = [c for c in [
        "produto", "preco", "comissao_novo", "ganho_estimado",
        "overlay", "hashtags", "status_agendamento", "data_publicacao"
    ] if c in filtered.columns]

    def _color_status(val):
        color = STATUS_COLORS.get(str(val), "#888888")
        return f"background-color: {color}18; color: {color}; font-weight: 600; border-radius: 4px;"

    styled = filtered[display_cols].style
    if "status_agendamento" in display_cols:
        styled = styled.applymap(_color_status, subset=["status_agendamento"])
    if "ganho_estimado" in display_cols:
        styled = styled.format({"ganho_estimado": "R$ {:.2f}", "preco": "R$ {:.2f}", "comissao_novo": "{:.1f}%"}, na_rep="-")

    st.dataframe(styled, use_container_width=True, height=380)
    st.caption(f"Mostrando {len(filtered)} de {len(df)} produtos")


# ── Charts ────────────────────────────────────────────────────────────────────

def render_charts(df: pd.DataFrame):
    if df.empty:
        return

    st.markdown('<div class="section-title">📊 Análise</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        if "status_agendamento" in df.columns:
            status_counts = df["status_agendamento"].value_counts().reset_index()
            status_counts.columns = ["Status", "Quantidade"]
            emojis = [STATUS_EMOJI.get(s, "⚪") for s in status_counts["Status"]]
            status_counts["Label"] = [f"{e} {s}" for e, s in zip(emojis, status_counts["Status"])]

            fig = px.pie(
                status_counts,
                names="Label",
                values="Quantidade",
                title="Status dos Produtos",
                color="Status",
                color_discrete_map={k: v for k, v in STATUS_COLORS.items()},
                hole=0.4,
            )
            fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0),
                              legend=dict(orientation="h", yanchor="bottom", y=-0.3))
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "comissao_novo" in df.columns:
            fig2 = px.histogram(
                df,
                x="comissao_novo",
                nbins=15,
                title="Distribuição de Comissão",
                labels={"comissao_novo": "Comissão (%)"},
                color_discrete_sequence=["#EE4D2D"],
            )
            fig2.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0),
                               plot_bgcolor="white", paper_bgcolor="white")
            fig2.update_xaxes(gridcolor="#F0F0F0")
            fig2.update_yaxes(gridcolor="#F0F0F0")
            st.plotly_chart(fig2, use_container_width=True)

    with col3:
        if "data_publicacao" in df.columns:
            df_pub = df[df["data_publicacao"].notna() & (df["data_publicacao"] != "")].copy()
            if not df_pub.empty:
                try:
                    df_pub["data"] = pd.to_datetime(df_pub["data_publicacao"]).dt.date
                    pub_por_dia = df_pub.groupby("data").size().reset_index(name="Posts")
                    fig3 = px.bar(
                        pub_por_dia, x="data", y="Posts",
                        title="Posts por Dia",
                        color_discrete_sequence=["#EE4D2D"],
                    )
                    fig3.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0),
                                       plot_bgcolor="white", paper_bgcolor="white")
                    st.plotly_chart(fig3, use_container_width=True)
                except Exception:
                    st.caption("Ainda sem histórico de publicações.")
            else:
                st.caption("📅 Histórico de publicações aparecerá aqui após os primeiros posts.")


# ── Manual Queue ──────────────────────────────────────────────────────────────

def render_manual_queue():
    queue = load_manual_queue()
    if not queue:
        return

    st.markdown(f'<div class="section-title">📋 Fila Manual ({len(queue)} itens)</div>', unsafe_allow_html=True)
    st.warning("📹 Estes produtos precisam de vídeo para publicar. Grave o vídeo e use o copy abaixo!")

    for i, item in enumerate(reversed(queue[-8:])):
        with st.expander(f"📦 {item.get('produto', 'Produto')[:70]}", expanded=(i == 0)):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**🎬 Texto para overlay do vídeo:**")
                overlay_val = item.get('overlay', '')
                st.code(overlay_val, language=None)

                st.markdown("**#️⃣ Hashtags:**")
                st.code(item.get('hashtags', ''), language=None)

                st.markdown("**🔗 Link afiliado:**")
                st.code(item.get('link_afiliado', ''), language=None)

            with c2:
                st.markdown("**📝 Legenda completa (copiar e colar):**")
                legenda = item.get('legenda', '')
                link = item.get('link_afiliado', '')
                hashtags = item.get('hashtags', '')
                copy_completo = f"{legenda}\n\n{hashtags}\n\n🔗 {link}"
                st.text_area(
                    "copy",
                    copy_completo,
                    height=160,
                    key=f"q_{i}_{item.get('adicionado_em', i)}",
                    label_visibility="collapsed"
                )
                adicionado = item.get('adicionado_em', '')[:16].replace('T', ' ')
                st.caption(f"⏱ Adicionado: {adicionado}")


# ── Log Viewer ────────────────────────────────────────────────────────────────

def render_log_viewer():
    with st.expander("🖥️ Log do Sistema (últimas 60 linhas)"):
        log_content = load_log()
        # Colorir linhas de erro
        log_html = ""
        for line in log_content.split("\n"):
            if "ERROR" in line or "Erro" in line:
                log_html += f'<span style="color:#FF4444">{line}</span>\n'
            elif "WARNING" in line or "warning" in line:
                log_html += f'<span style="color:#FFA500">{line}</span>\n'
            elif "success" in line.lower() or "publicado" in line.lower() or "✅" in line:
                log_html += f'<span style="color:#00C851">{line}</span>\n'
            else:
                log_html += f'{line}\n'
        st.markdown(f'<pre style="font-size:0.78rem; line-height:1.5; overflow-x:auto">{log_html}</pre>',
                    unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    render_sidebar()
    render_header()

    df = load_data()

    render_kpis(df)
    st.markdown("---")
    render_ganho_estimado(df)
    st.markdown("---")
    render_products_table(df)
    st.markdown("---")
    render_charts(df)
    st.markdown("---")
    render_manual_queue()
    st.markdown("---")
    render_log_viewer()

    # Auto-refresh a cada 30s
    st.markdown("""
    <script>
        setTimeout(function() { window.location.reload(); }, 30000);
    </script>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
