"""
Shopee Affiliate Bot — Dashboard (Streamlit Community Cloud version)
Responsivo para mobile + PWA instalável.
"""

import io
import json
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
    initial_sidebar_state="collapsed",
)

# ── PWA + CSS Responsivo ───────────────────────────────────────────────────────
def inject_pwa_and_css():
    st.markdown("""
    <!-- PWA Meta Tags -->
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Shopee Bot">
    <meta name="theme-color" content="#FF6B35">

    <!-- PWA Manifest inline -->
    <link rel="manifest" href="data:application/json;base64,ewogICJuYW1lIjogIlNob3BlZSBBZmZpbGlhdGUgQm90IiwKICAic2hvcnRfbmFtZSI6ICJTaG9wZWUgQm90IiwKICAiZGVzY3JpcHRpb24iOiAiRGFzaGJvYXJkIGRlIGFmaWxpYWRvcyBTaG9wZWUiLAogICJzdGFydF91cmwiOiAiLyIsCiAgImRpc3BsYXkiOiAic3RhbmRhbG9uZSIsCiAgImJhY2tncm91bmRfY29sb3IiOiAiIzBFMTExNyIsCiAgInRoZW1lX2NvbG9yIjogIiNGRjZCMzUiLAogICJpY29ucyI6IFsKICAgIHsic3JjIjogImh0dHBzOi8vaW1nLmljb25zOC5jb20vY29sb3IvOTYvc2hvcGVlLnBuZyIsICJzaXplcyI6ICI5Nng5NiIsICJ0eXBlIjogImltYWdlL3BuZyJ9LAogICAgeyJzcmMiOiAiaHR0cHM6Ly9pbWcuaWNvbnM4LmNvbS9jb2xvci8xOTIvc2hvcGVlLnBuZyIsICJzaXplcyI6ICIxOTJ4MTkyIiwgInR5cGUiOiAiaW1hZ2UvcG5nIn0KICBdCn0=">

    <style>
    /* ── Reset e Base ── */
    * { box-sizing: border-box; }

    /* ── Responsivo: oculta sidebar em mobile ── */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 100% !important;
            min-width: 100% !important;
        }
        /* KPIs em 2 colunas no mobile */
        div[data-testid="column"] {
            min-width: 45% !important;
            flex: 1 1 45% !important;
        }
        /* Tabela responsiva */
        div[data-testid="stDataFrame"] {
            overflow-x: auto !important;
        }
        /* Texto menor em mobile */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }
        /* Botões full width */
        .stButton > button {
            width: 100% !important;
        }
        /* Upload area */
        div[data-testid="stFileUploader"] {
            width: 100% !important;
        }
    }

    /* ── Cards de métricas ── */
    div[data-testid="metric-container"] {
        background: #1E2130;
        border: 1px solid #FF6B3533;
        border-radius: 12px;
        padding: 12px 8px !important;
        text-align: center;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.75rem !important;
        color: #FF6B35 !important;
    }

    /* ── Banner de instalação PWA ── */
    #pwa-banner {
        display: none;
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: #FF6B35;
        color: white;
        padding: 14px 20px;
        text-align: center;
        font-weight: bold;
        z-index: 9999;
        cursor: pointer;
        font-size: 1rem;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
    }
    </style>

    <!-- Banner de instalação PWA -->
    <div id="pwa-banner" onclick="installPWA()">
        📱 Instalar como App no celular — Toque aqui!
    </div>

    <script>
    let deferredPrompt;

    // Captura evento de instalação
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        document.getElementById('pwa-banner').style.display = 'block';
    });

    // Função de instalação
    function installPWA() {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((result) => {
                if (result.outcome === 'accepted') {
                    document.getElementById('pwa-banner').style.display = 'none';
                }
                deferredPrompt = null;
            });
        }
    }

    // Oculta banner se já instalado
    window.addEventListener('appinstalled', () => {
        document.getElementById('pwa-banner').style.display = 'none';
    });
    </script>
    """, unsafe_allow_html=True)


STATUS_COLORS = {
    "pendente": "#FFA500",
    "publicado_tiktok": "#00CC44",
    "publicado_shopee": "#00AAFF",
    "fila_manual": "#9B59B6",
    "falhou_tiktok": "#FF3333",
    "falhou_shopee": "#FF6666",
}

EXCEL_COLUMNS = [
    "produto", "link_original", "link_afiliado",
    "comissao_novo", "comissao_atual",
    "overlay", "legenda", "hashtags", "estrategia",
    "status_agendamento", "data_publicacao",
]


# ── Session state ─────────────────────────────────────────────────────────────

def _get_df() -> pd.DataFrame:
    return st.session_state.get("df", pd.DataFrame())


def _set_df(df: pd.DataFrame):
    st.session_state["df"] = df


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/shopee.png", width=60)
        st.title("Shopee Affiliate Bot")
        st.markdown("---")

        st.subheader("📂 Carregar Dados")
        uploaded = st.file_uploader(
            "Upload do output.xlsx",
            type=["xlsx"],
            help="Gere o arquivo rodando 'python main.py' no PC e faça upload aqui.",
        )
        if uploaded:
            try:
                df = pd.read_excel(uploaded, engine="openpyxl")
                _set_df(df)
                st.success(f"✅ {len(df)} produtos carregados!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

        st.markdown("---")

        df = _get_df()
        if not df.empty:
            buf = io.BytesIO()
            df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button(
                label="⬇ Baixar Excel",
                data=buf.getvalue(),
                file_name=f"shopee_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.markdown("---")
        st.subheader("📋 Como usar")
        st.markdown("""
1. Rode no PC:
   ```
   python main.py
   ```
2. Upload do arquivo:
   ```
   data/output.xlsx
   ```
3. Visualize aqui
4. Baixe o Excel
        """)
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")


# ── KPIs ──────────────────────────────────────────────────────────────────────

def render_kpis(df: pd.DataFrame):
    st.subheader("📊 Resumo")

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    total = len(df)
    ai_ok = len(df[df["overlay"].str.len() > 5]) if "overlay" in df.columns and total > 0 else 0
    published = len(df[df["status_agendamento"].str.startswith("publicado", na=False)]) if "status_agendamento" in df.columns else 0
    pending = len(df[df["status_agendamento"] == "pendente"]) if "status_agendamento" in df.columns else 0
    avg_new = df["comissao_novo"].mean() if "comissao_novo" in df.columns and total > 0 else 0
    avg_existing = df["comissao_atual"].mean() if "comissao_atual" in df.columns and total > 0 else 0

    c1.metric("🛍️ Total", total)
    c2.metric("🤖 Copy OK", ai_ok)
    c3.metric("✅ Publicados", published)
    c4.metric("⏳ Pendentes", pending)
    c5.metric("💰 Comissão Novo", f"{avg_new:.1f}%")
    c6.metric("💰 Comissão Atual", f"{avg_existing:.1f}%")


# ── Products Table ────────────────────────────────────────────────────────────

def render_products_table(df: pd.DataFrame):
    st.subheader("📦 Produtos")

    if df.empty:
        st.info("Nenhum dado. Faça upload do output.xlsx na barra lateral ☰")
        return

    col1, col2 = st.columns(2)
    with col1:
        status_options = ["Todos"] + sorted(df["status_agendamento"].dropna().unique().tolist()) if "status_agendamento" in df.columns else ["Todos"]
        selected_status = st.selectbox("Filtrar por status", status_options)
    with col2:
        search = st.text_input("🔍 Buscar produto", placeholder="Digite o nome...")

    filtered = df.copy()
    if selected_status != "Todos" and "status_agendamento" in filtered.columns:
        filtered = filtered[filtered["status_agendamento"] == selected_status]
    if search and "produto" in filtered.columns:
        filtered = filtered[filtered["produto"].str.contains(search, case=False, na=False)]

    display_cols = [c for c in ["produto", "comissao_novo", "comissao_atual", "overlay", "hashtags", "status_agendamento"] if c in filtered.columns]

    def _color_status(val):
        color = STATUS_COLORS.get(str(val), "#FFFFFF")
        return f"background-color: {color}22; color: {color}; font-weight: bold;"

    styled = filtered[display_cols].style.applymap(
        _color_status, subset=["status_agendamento"]
    ) if "status_agendamento" in display_cols else filtered[display_cols].style

    st.dataframe(styled, use_container_width=True, height=350)
    st.caption(f"Mostrando {len(filtered)} de {len(df)} produtos")


# ── Copy Viewer ───────────────────────────────────────────────────────────────

def render_copy_viewer(df: pd.DataFrame):
    if df.empty:
        return

    st.subheader("✍️ Copy para Postagem")
    st.info("Copie o conteúdo abaixo para usar nos seus vídeos.")

    pending = df[df["status_agendamento"] == "pendente"] if "status_agendamento" in df.columns else df
    if pending.empty:
        st.success("🎉 Todos os produtos já foram postados!")
        return

    for _, row in pending.head(10).iterrows():
        with st.expander(f"📦 {row.get('produto', 'Produto')} — {row.get('comissao_novo', 0):.1f}%"):
            st.markdown("**🎬 Overlay (tela do vídeo):**")
            st.code(row.get("overlay", ""), language=None)

            st.markdown("**📝 Legenda:**")
            st.text_area(
                "Copiar legenda",
                row.get("legenda", ""),
                height=150,
                key=f"leg_{row.get('link_original', '')}",
            )

            st.markdown("**#️⃣ Hashtags:**")
            st.code(row.get("hashtags", ""), language=None)

            st.markdown("**🔗 Link Afiliado:**")
            st.code(row.get("link_afiliado", ""), language=None)

            st.caption(f"*{row.get('estrategia', '')}*")


# ── Charts ────────────────────────────────────────────────────────────────────

def render_charts(df: pd.DataFrame):
    if df.empty:
        return

    st.subheader("📈 Análise")

    if "status_agendamento" in df.columns:
        counts = df["status_agendamento"].value_counts().reset_index()
        counts.columns = ["Status", "Quantidade"]
        fig = px.bar(
            counts, x="Status", y="Quantidade",
            title="Produtos por Status",
            color="Status",
            color_discrete_map={k: v for k, v in STATUS_COLORS.items()},
        )
        fig.update_layout(showlegend=False, height=280)
        st.plotly_chart(fig, use_container_width=True)

    if "comissao_novo" in df.columns:
        fig2 = px.histogram(
            df, x="comissao_novo", nbins=20,
            title="Distribuição de Comissão",
            labels={"comissao_novo": "Comissão (%)"},
            color_discrete_sequence=["#FF6B35"],
        )
        fig2.update_layout(height=280)
        st.plotly_chart(fig2, use_container_width=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    inject_pwa_and_css()
    render_sidebar()

    st.title("🛒 Shopee Affiliate Bot")
    st.markdown("Visualize produtos, copy IA e status de postagem.")
    st.markdown("---")

    df = _get_df()

    render_kpis(df)
    st.markdown("---")
    render_products_table(df)
    st.markdown("---")
    render_copy_viewer(df)
    st.markdown("---")
    render_charts(df)


if __name__ == "__main__":
    main()
