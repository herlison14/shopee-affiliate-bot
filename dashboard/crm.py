"""
CRM — Sistema de Gestão de Clientes
Módulo CRM completo integrado ao dashboard Shopee Affiliate Bot.
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.crm_db import (
    init_db, get_pipelines, get_stages, create_stage, delete_stage,
    get_contacts, get_contact, create_contact, update_contact, delete_contact, count_contacts,
    get_companies, get_company, create_company, update_company, delete_company, count_companies,
    get_deals, get_deal, create_deal, update_deal, delete_deal, move_deal_stage,
    count_deals, sum_deals_value, get_deal_stage_history,
    get_activities, create_activity, update_activity_status, delete_activity, count_activities,
    get_notes, create_note, delete_note,
    get_crm_products, create_crm_product, delete_crm_product,
    get_pipeline_summary, get_deals_by_month, get_conversion_rate,
    get_activities_summary, get_top_owners, get_users, get_tags, get_automations,
    toggle_automation, create_automation,
)

# ── Constantes visuais ─────────────────────────────────────────────────────────

ACTIVITY_ICONS = {
    "ligacao":  "📞", "email":    "📧", "reuniao":  "🤝",
    "tarefa":   "✅", "whatsapp": "💬", "almoco":   "🍽️", "prazo": "⏰",
}
STATUS_BADGE = {
    "pendente":  ("🟡", "#FFD700"), "concluida": ("🟢", "#00C851"),
    "atrasada":  ("🔴", "#FF4444"), "aberto":    ("🔵", "#4D9FFF"),
    "ganho":     ("🟢", "#00C851"), "perdido":   ("🔴", "#FF4444"),
}
STAGE_COLORS = ["#888888", "#4D9FFF", "#FFD700", "#FF8C00", "#00C851"]

CRM_CSS = """
<style>
.crm-card {
    background: #1A1A1A;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    border-left: 4px solid #4D9FFF;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    transition: transform .15s;
}
.crm-card:hover { transform: translateY(-2px); }
.crm-card-title { font-weight: 700; font-size: 0.92rem; color: #F0F0F0; }
.crm-card-sub   { font-size: 0.78rem; color: #999; margin-top: 2px; }
.crm-badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 0.72rem; font-weight: 600; margin-right: 4px;
}
.crm-kpi {
    background: #1A1A1A; border-radius: 12px; padding: 18px 22px;
    text-align: center; border: 1px solid #2A2A2A;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}
.crm-kpi-value { font-size: 2rem; font-weight: 800; color: #F0F0F0; }
.crm-kpi-label { font-size: 0.78rem; color: #999; margin-top: 4px; }
.kanban-col {
    background: #151515; border-radius: 12px; padding: 12px 8px;
    min-height: 300px; border: 1px solid #2A2A2A;
}
.kanban-header {
    text-align: center; font-weight: 700; font-size: 0.88rem;
    padding: 6px; border-radius: 8px; margin-bottom: 10px;
    letter-spacing: .5px;
}
.section-title {
    font-size: 1.1rem; font-weight: 700; color: #F0F0F0;
    border-bottom: 2px solid #2A2A2A; padding-bottom: 8px; margin-bottom: 16px;
}
</style>
"""


def _fmt_brl(v: float) -> str:
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"R$ {v/1_000:.1f}k"
    return f"R$ {v:,.0f}"


def _days_until(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return 0


# ── KPI Cards ─────────────────────────────────────────────────────────────────

def render_crm_kpis():
    total_contacts  = count_contacts()
    total_companies = count_companies()
    open_deals      = count_deals("aberto")
    won_deals       = count_deals("ganho")
    pipeline_value  = sum_deals_value("aberto")
    won_revenue     = sum_deals_value("ganho")
    conv_rate       = get_conversion_rate()
    pending_act     = count_activities("pendente")

    cols = st.columns(4)
    kpis = [
        ("Contatos",         total_contacts,          "👤", "#4D9FFF"),
        ("Empresas",         total_companies,         "🏢", "#B07FFF"),
        ("Negócios Abertos", open_deals,              "💼", "#FF8C00"),
        ("Negócios Ganhos",  won_deals,               "🏆", "#00C851"),
    ]
    for col, (label, value, icon, color) in zip(cols, kpis):
        col.markdown(f"""
        <div class="crm-kpi">
            <div style="font-size:1.6rem">{icon}</div>
            <div class="crm-kpi-value" style="color:{color}">{value}</div>
            <div class="crm-kpi-label">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    cols2 = st.columns(4)
    kpis2 = [
        ("Valor no Funil",    _fmt_brl(pipeline_value), "💰", "#FFD700"),
        ("Receita Gerada",    _fmt_brl(won_revenue),    "💵", "#00C851"),
        ("Taxa de Conversão", f"{conv_rate}%",           "📈", "#4D9FFF"),
        ("Atividades Pend.",  pending_act,               "📅", "#FF4444"),
    ]
    for col, (label, value, icon, color) in zip(cols2, kpis2):
        col.markdown(f"""
        <div class="crm-kpi">
            <div style="font-size:1.6rem">{icon}</div>
            <div class="crm-kpi-value" style="color:{color}">{value}</div>
            <div class="crm-kpi-label">{label}</div>
        </div>""", unsafe_allow_html=True)


# ── Pipeline Kanban ────────────────────────────────────────────────────────────

def render_pipeline():
    st.markdown('<div class="section-title">📊 Pipeline de Vendas</div>', unsafe_allow_html=True)

    pipelines = get_pipelines()
    if not pipelines:
        st.warning("Nenhum pipeline encontrado.")
        return

    # Seletor de pipeline + filtros
    col_pip, col_search, col_owner, col_status = st.columns([2, 2, 2, 1])
    with col_pip:
        pip_names = {p["name"]: p["id"] for p in pipelines}
        sel_pip = st.selectbox("Pipeline", list(pip_names.keys()), key="pip_sel")
    pipeline_id = pip_names[sel_pip]

    with col_search:
        search = st.text_input("🔍 Buscar negócio", key="pip_search", placeholder="Nome, contato...")
    with col_owner:
        users = [u["name"] for u in get_users()]
        owner_filter = st.selectbox("Responsável", ["Todos"] + users, key="pip_owner")
    with col_status:
        show_status = st.selectbox("Status", ["aberto", "ganho", "perdido"], key="pip_status")

    owner = "" if owner_filter == "Todos" else owner_filter
    deals = get_deals(pipeline_id=pipeline_id, status=show_status, search=search, owner=owner)
    stages = get_stages(pipeline_id)

    if not stages:
        st.info("Adicione etapas ao pipeline abaixo.")
    else:
        # Resumo financeiro
        summary = get_pipeline_summary(pipeline_id)
        total_val = sum(s["total_value"] for s in summary)
        if total_val > 0:
            sum_cols = st.columns(len(summary))
            for col, s in zip(sum_cols, summary):
                col.markdown(f"""
                <div style="text-align:center; padding:6px; background:#1A1A1A; border-radius:8px;
                             border-top:3px solid {s['color']}; margin-bottom:8px">
                    <div style="font-size:0.7rem; color:#999">{s['name']}</div>
                    <div style="font-weight:700; color:#F0F0F0">{_fmt_brl(s['total_value'])}</div>
                    <div style="font-size:0.7rem; color:#888">{s['deal_count']} neg.</div>
                </div>""", unsafe_allow_html=True)

        # Kanban
        deals_by_stage = {}
        for d in deals:
            sid = d["stage_id"]
            deals_by_stage.setdefault(sid, []).append(d)

        kanban_cols = st.columns(len(stages))
        for col, stage in zip(kanban_cols, stages):
            stage_deals = deals_by_stage.get(stage["id"], [])
            with col:
                st.markdown(f"""
                <div class="kanban-header" style="background:{stage['color']}22; color:{stage['color']}">
                    {stage['name']} <span style="color:#888">({len(stage_deals)})</span>
                </div>""", unsafe_allow_html=True)

                for deal in stage_deals:
                    days = _days_until(deal.get("close_date") or "")
                    days_color = "#FF4444" if days < 0 else "#FFD700" if days <= 7 else "#00C851"
                    prob_color = "#00C851" if deal["probability"] >= 70 else "#FFD700" if deal["probability"] >= 40 else "#FF4444"

                    with st.container():
                        st.markdown(f"""
                        <div class="crm-card" style="border-left-color:{stage['color']}">
                            <div class="crm-card-title">💼 {deal['title']}</div>
                            <div class="crm-card-sub">💰 {_fmt_brl(deal['value'])}</div>
                            {"<div class='crm-card-sub'>👤 " + (deal['contact_name'] or '') + "</div>" if deal.get('contact_name') else ""}
                            {"<div class='crm-card-sub'>🏢 " + (deal['company_name'] or '') + "</div>" if deal.get('company_name') else ""}
                            <div class="crm-card-sub" style="margin-top:6px">
                                <span style="color:{prob_color}">▣ {deal['probability']}%</span>
                                {"&nbsp;&nbsp;<span style='color:" + days_color + "'>📅 " + str(abs(days)) + "d " + ("atraso" if days < 0 else "restante") + "</span>" if deal.get('close_date') else ""}
                                {"&nbsp;&nbsp;<span style='color:#999'>" + (deal['owner'] or '') + "</span>" if deal.get('owner') else ""}
                            </div>
                        </div>""", unsafe_allow_html=True)

                        btn_cols = st.columns(3)
                        stage_idx = next((i for i, s in enumerate(stages) if s["id"] == stage["id"]), -1)

                        with btn_cols[0]:
                            if stage_idx > 0 and st.button("◀", key=f"prev_{deal['id']}", help="Etapa anterior"):
                                move_deal_stage(deal["id"], stages[stage_idx - 1]["id"])
                                st.rerun()
                        with btn_cols[1]:
                            if st.button("✏️", key=f"edit_d_{deal['id']}", help="Editar"):
                                st.session_state["edit_deal_id"] = deal["id"]
                        with btn_cols[2]:
                            if stage_idx < len(stages) - 1 and st.button("▶", key=f"next_{deal['id']}", help="Próxima etapa"):
                                move_deal_stage(deal["id"], stages[stage_idx + 1]["id"])
                                st.rerun()

    # ── Formulário Novo Negócio ──
    st.markdown("---")
    with st.expander("➕ Novo Negócio", expanded=False):
        _form_new_deal(pipeline_id, stages)

    # ── Gerenciar Etapas ──
    with st.expander("⚙️ Gerenciar Etapas do Pipeline", expanded=False):
        _manage_stages(pipeline_id, stages)

    # ── Editar Negócio (modal) ──
    if "edit_deal_id" in st.session_state:
        _modal_edit_deal(st.session_state["edit_deal_id"], stages)


def _form_new_deal(pipeline_id: int, stages: list):
    contacts = get_contacts(limit=500)
    companies = get_companies(limit=500)
    users = get_users()

    with st.form("form_new_deal", clear_on_submit=True):
        c1, c2 = st.columns(2)
        title     = c1.text_input("Título do Negócio *", placeholder="Ex: Proposta para Empresa X")
        value     = c2.number_input("Valor (R$)", min_value=0.0, step=100.0)
        c3, c4, c5 = st.columns(3)
        stage_names = {s["name"]: s["id"] for s in stages}
        sel_stage   = c3.selectbox("Etapa *", list(stage_names.keys()))
        probability = c4.slider("Probabilidade (%)", 0, 100, 50)
        close_date  = c5.date_input("Data de Fechamento", value=date.today() + timedelta(days=30))
        c6, c7, c8 = st.columns(3)
        contact_opts = {f"{c['name']} ({c.get('company_name') or 'sem empresa'})": c["id"] for c in contacts}
        contact_opts = {"-- Nenhum --": None, **contact_opts}
        sel_contact = c6.selectbox("Contato", list(contact_opts.keys()))
        company_opts = {co["name"]: co["id"] for co in companies}
        company_opts = {"-- Nenhum --": None, **company_opts}
        sel_company = c7.selectbox("Empresa", list(company_opts.keys()))
        owner_opts  = [u["name"] for u in users]
        sel_owner   = c8.selectbox("Responsável", owner_opts if owner_opts else ["Sem usuário"])
        notes       = st.text_area("Observações", height=80)

        if st.form_submit_button("✅ Criar Negócio", type="primary"):
            if not title:
                st.error("Título obrigatório.")
            else:
                create_deal({
                    "title": title, "value": value, "currency": "BRL",
                    "stage_id": stage_names[sel_stage], "pipeline_id": pipeline_id,
                    "contact_id": contact_opts[sel_contact],
                    "company_id": company_opts[sel_company],
                    "owner": sel_owner, "close_date": str(close_date),
                    "probability": probability, "notes": notes, "tags": [],
                })
                st.success("Negócio criado!")
                st.rerun()


def _manage_stages(pipeline_id: int, stages: list):
    st.write("**Etapas atuais:**")
    for s in stages:
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"<span style='color:{s['color']}'>■</span> **{s['name']}** — {s['probability']}% prob.", unsafe_allow_html=True)
        if c2.button("🗑️", key=f"del_stage_{s['id']}"):
            delete_stage(s["id"])
            st.rerun()

    st.markdown("---")
    with st.form("form_new_stage", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        stage_name = c1.text_input("Nome da Etapa")
        stage_color = c2.color_picker("Cor", "#4D9FFF")
        stage_prob  = c3.slider("Probabilidade (%)", 0, 100, 50)
        if st.form_submit_button("Adicionar Etapa"):
            if stage_name:
                create_stage(pipeline_id, stage_name, stage_color, stage_prob)
                st.rerun()


def _modal_edit_deal(deal_id: int, stages: list):
    deal = get_deal(deal_id)
    if not deal:
        del st.session_state["edit_deal_id"]
        return

    st.markdown(f"### ✏️ Editando: {deal['title']}")
    contacts  = get_contacts(limit=500)
    companies = get_companies(limit=500)
    users     = get_users()

    with st.form("form_edit_deal"):
        c1, c2 = st.columns(2)
        title  = c1.text_input("Título", value=deal["title"])
        value  = c2.number_input("Valor (R$)", value=float(deal["value"] or 0), step=100.0)
        c3, c4, c5 = st.columns(3)
        stage_names = {s["name"]: s["id"] for s in stages}
        cur_stage   = next((s["name"] for s in stages if s["id"] == deal.get("stage_id")), stages[0]["name"] if stages else "")
        sel_stage   = c3.selectbox("Etapa", list(stage_names.keys()), index=list(stage_names.keys()).index(cur_stage) if cur_stage in stage_names else 0)
        probability = c4.slider("Probabilidade (%)", 0, 100, int(deal.get("probability") or 50))
        try:
            cd = datetime.strptime(deal["close_date"][:10], "%Y-%m-%d").date() if deal.get("close_date") else date.today()
        except Exception:
            cd = date.today()
        close_date = c5.date_input("Fechamento", value=cd)
        c6, c7 = st.columns(2)
        status_opts = ["aberto", "ganho", "perdido"]
        sel_status  = c6.selectbox("Status", status_opts, index=status_opts.index(deal.get("status", "aberto")))
        lost_reason = c7.text_input("Motivo da Perda", value=deal.get("lost_reason") or "")
        notes = st.text_area("Observações", value=deal.get("notes") or "", height=80)

        c_upd, c_del, c_cancel = st.columns(3)
        submitted = c_upd.form_submit_button("💾 Salvar", type="primary")
        delete_btn = c_del.form_submit_button("🗑️ Excluir")
        cancel_btn = c_cancel.form_submit_button("✖ Cancelar")

        if submitted:
            update_deal(deal_id, {
                "title": title, "value": value, "stage_id": stage_names[sel_stage],
                "probability": probability, "close_date": str(close_date),
                "status": sel_status, "lost_reason": lost_reason, "notes": notes,
            })
            del st.session_state["edit_deal_id"]
            st.rerun()
        if delete_btn:
            delete_deal(deal_id)
            del st.session_state["edit_deal_id"]
            st.rerun()
        if cancel_btn:
            del st.session_state["edit_deal_id"]
            st.rerun()

    # Histórico
    hist = get_deal_stage_history(deal_id)
    if hist:
        with st.expander("📋 Histórico de Movimentações"):
            for h in hist:
                st.markdown(f"- `{h['moved_at'][:16]}` — **{h.get('from_stage') or 'Início'}** → **{h['to_stage']}** *(por {h.get('moved_by') or 'sistema'})*")

    # Notas
    with st.expander("📝 Notas do Negócio"):
        notes_list = get_notes(deal_id=deal_id)
        for n in notes_list:
            c1, c2 = st.columns([9, 1])
            c1.markdown(f"**{n['created_at'][:16]}** — {n['content']}")
            if c2.button("🗑️", key=f"del_note_{n['id']}"):
                delete_note(n["id"])
                st.rerun()
        new_note = st.text_input("Nova nota", key="new_note_deal")
        if st.button("Adicionar nota") and new_note:
            create_note(new_note, deal_id=deal_id, author="usuário")
            st.rerun()


# ── Contatos ──────────────────────────────────────────────────────────────────

def render_contacts():
    st.markdown('<div class="section-title">👤 Gestão de Contatos</div>', unsafe_allow_html=True)

    col_search, col_add = st.columns([4, 1])
    with col_search:
        search = st.text_input("🔍 Buscar por nome, e-mail ou telefone", key="contact_search")
    with col_add:
        if st.button("➕ Novo Contato", type="primary", key="btn_new_contact"):
            st.session_state["show_contact_form"] = True

    if st.session_state.get("show_contact_form"):
        _form_new_contact()

    contacts = get_contacts(search=search)

    if not contacts:
        st.info("Nenhum contato encontrado. Adicione seu primeiro contato!")
        return

    # Tabela de contatos
    df = pd.DataFrame(contacts)
    display_cols = ["id", "name", "company_name", "cargo", "email", "phone", "whatsapp", "score", "created_at"]
    df = df[[c for c in display_cols if c in df.columns]]
    df.columns = ["ID", "Nome", "Empresa", "Cargo", "E-mail", "Telefone", "WhatsApp", "Score", "Criado em"][:len(df.columns)]

    st.dataframe(
        df.style.background_gradient(subset=["Score"], cmap="RdYlGn"),
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    # Detalhe / Edição
    contact_ids = {f"{c['name']} (ID:{c['id']})": c["id"] for c in contacts}
    sel = st.selectbox("Selecionar contato para visualizar/editar", ["-- Selecione --"] + list(contact_ids.keys()), key="contact_sel")
    if sel != "-- Selecione --":
        _contact_detail(contact_ids[sel])


def _form_new_contact():
    companies = get_companies(limit=500)
    tags      = get_tags()

    with st.form("form_new_contact", clear_on_submit=True):
        st.markdown("**Novo Contato**")
        c1, c2 = st.columns(2)
        name     = c1.text_input("Nome *")
        cargo    = c2.text_input("Cargo")
        c3, c4 = st.columns(2)
        email    = c3.text_input("E-mail")
        phone    = c4.text_input("Telefone")
        c5, c6 = st.columns(2)
        whatsapp = c5.text_input("WhatsApp")
        linkedin = c6.text_input("LinkedIn")
        c7, c8 = st.columns(2)
        company_opts = {"-- Nenhuma --": None, **{co["name"]: co["id"] for co in companies}}
        sel_company  = c7.selectbox("Empresa", list(company_opts.keys()))
        score        = c8.slider("Score de Engajamento", 0, 100, 50)
        sel_tags     = st.multiselect("Tags", [t["name"] for t in tags])
        notes        = st.text_area("Observações", height=60)
        address      = st.text_input("Endereço")

        c_sub, c_cancel = st.columns(2)
        submitted = c_sub.form_submit_button("✅ Salvar", type="primary")
        cancel    = c_cancel.form_submit_button("✖ Cancelar")

        if submitted:
            if not name:
                st.error("Nome obrigatório.")
            else:
                create_contact({
                    "name": name, "cargo": cargo, "email": email, "phone": phone,
                    "whatsapp": whatsapp, "linkedin": linkedin, "address": address,
                    "company_id": company_opts[sel_company], "score": score,
                    "tags": sel_tags, "notes": notes,
                })
                st.success(f"Contato '{name}' criado!")
                st.session_state["show_contact_form"] = False
                st.rerun()
        if cancel:
            st.session_state["show_contact_form"] = False
            st.rerun()


def _contact_detail(contact_id: int):
    c = get_contact(contact_id)
    if not c:
        return

    tags = json.loads(c.get("tags") or "[]")
    tag_html = " ".join(f'<span class="crm-badge" style="background:#4D9FFF22;color:#4D9FFF">{t}</span>' for t in tags)
    score_color = "#00C851" if c["score"] >= 70 else "#FFD700" if c["score"] >= 40 else "#FF4444"

    st.markdown(f"""
    <div class="crm-card" style="border-left-color:{score_color}; padding:16px">
        <div style="font-size:1.1rem; font-weight:800; color:#F0F0F0">👤 {c['name']}</div>
        <div style="color:#999; margin:4px 0">{c.get('cargo') or ''} {('@ ' + c['company_name']) if c.get('company_name') else ''}</div>
        <div style="margin:8px 0">
            {('📧 ' + c['email'] + '&nbsp;&nbsp;') if c.get('email') else ''}
            {('📞 ' + c['phone'] + '&nbsp;&nbsp;') if c.get('phone') else ''}
            {('💬 ' + c['whatsapp']) if c.get('whatsapp') else ''}
        </div>
        {tag_html}
        <div style="margin-top:8px; color:{score_color}; font-weight:700">Score: {c['score']}/100</div>
    </div>""", unsafe_allow_html=True)

    col_edit, col_del = st.columns([1, 1])
    with col_edit:
        if st.button("✏️ Editar Contato", key=f"edit_contact_{contact_id}"):
            st.session_state[f"edit_contact_{contact_id}"] = True
    with col_del:
        if st.button("🗑️ Excluir", key=f"del_contact_{contact_id}"):
            delete_contact(contact_id)
            st.rerun()

    if st.session_state.get(f"edit_contact_{contact_id}"):
        companies = get_companies(limit=500)
        all_tags  = get_tags()
        with st.form(f"edit_contact_form_{contact_id}"):
            c1, c2 = st.columns(2)
            name  = c1.text_input("Nome", value=c["name"])
            cargo = c2.text_input("Cargo", value=c.get("cargo") or "")
            c3, c4 = st.columns(2)
            email = c3.text_input("E-mail", value=c.get("email") or "")
            phone = c4.text_input("Telefone", value=c.get("phone") or "")
            c5, c6 = st.columns(2)
            whatsapp = c5.text_input("WhatsApp", value=c.get("whatsapp") or "")
            linkedin = c6.text_input("LinkedIn", value=c.get("linkedin") or "")
            score    = st.slider("Score", 0, 100, int(c.get("score") or 50))
            cur_tags = json.loads(c.get("tags") or "[]")
            sel_tags = st.multiselect("Tags", [t["name"] for t in all_tags], default=cur_tags)
            notes    = st.text_area("Observações", value=c.get("notes") or "", height=60)
            if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                update_contact(contact_id, {
                    "name": name, "cargo": cargo, "email": email, "phone": phone,
                    "whatsapp": whatsapp, "linkedin": linkedin, "score": score,
                    "tags": sel_tags, "notes": notes,
                })
                st.session_state[f"edit_contact_{contact_id}"] = False
                st.rerun()

    # Atividades vinculadas
    acts = get_activities(contact_id=contact_id)
    if acts:
        with st.expander(f"📅 Atividades ({len(acts)})"):
            for a in acts:
                icon = ACTIVITY_ICONS.get(a["type"], "•")
                emoji, _ = STATUS_BADGE.get(a["status"], ("⚪", "#888"))
                st.markdown(f"- {emoji} {icon} **{a['title']}** — {a.get('due_date','')[:10]} ({a['status']})")

    # Notas
    notes_list = get_notes(contact_id=contact_id)
    with st.expander(f"📝 Notas ({len(notes_list)})"):
        for n in notes_list:
            cc1, cc2 = st.columns([9, 1])
            cc1.markdown(f"*{n['created_at'][:16]}* — {n['content']}")
            if cc2.button("🗑️", key=f"del_cnote_{n['id']}"):
                delete_note(n["id"]); st.rerun()
        nn = st.text_input("Nova nota", key=f"new_note_c_{contact_id}")
        if st.button("Adicionar", key=f"add_cnote_{contact_id}") and nn:
            create_note(nn, contact_id=contact_id); st.rerun()


# ── Empresas ──────────────────────────────────────────────────────────────────

def render_companies():
    st.markdown('<div class="section-title">🏢 Gestão de Empresas</div>', unsafe_allow_html=True)

    col_s, col_add = st.columns([4, 1])
    with col_s:
        search = st.text_input("🔍 Buscar empresa", key="co_search")
    with col_add:
        if st.button("➕ Nova Empresa", type="primary"):
            st.session_state["show_company_form"] = True

    if st.session_state.get("show_company_form"):
        _form_new_company()

    companies = get_companies(search=search)

    if not companies:
        st.info("Nenhuma empresa cadastrada.")
        return

    df = pd.DataFrame(companies)
    show_cols = ["id", "name", "cnpj", "sector", "size", "website", "contact_count", "deal_count", "created_at"]
    df = df[[c for c in show_cols if c in df.columns]]
    labels = {"id": "ID", "name": "Empresa", "cnpj": "CNPJ", "sector": "Setor", "size": "Porte",
               "website": "Website", "contact_count": "Contatos", "deal_count": "Negócios", "created_at": "Criado em"}
    df = df.rename(columns={k: v for k, v in labels.items() if k in df.columns})
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    co_opts = {f"{c['name']} (ID:{c['id']})": c["id"] for c in companies}
    sel = st.selectbox("Selecionar empresa", ["-- Selecione --"] + list(co_opts.keys()), key="co_sel")
    if sel != "-- Selecione --":
        _company_detail(co_opts[sel])


def _form_new_company():
    with st.form("form_new_company", clear_on_submit=True):
        st.markdown("**Nova Empresa**")
        c1, c2 = st.columns(2)
        name   = c1.text_input("Razão Social *")
        cnpj   = c2.text_input("CNPJ")
        c3, c4 = st.columns(2)
        sector = c3.text_input("Setor")
        size   = c4.selectbox("Porte", ["", "MEI", "Micro", "Pequena", "Média", "Grande"])
        c5, c6 = st.columns(2)
        website = c5.text_input("Website")
        phone   = c6.text_input("Telefone")
        email   = st.text_input("E-mail")
        address = st.text_input("Endereço")
        notes   = st.text_area("Observações", height=60)
        c_sub, c_cancel = st.columns(2)
        submitted = c_sub.form_submit_button("✅ Salvar", type="primary")
        cancel    = c_cancel.form_submit_button("✖ Cancelar")
        if submitted:
            if not name:
                st.error("Razão social obrigatória.")
            else:
                create_company({"name": name, "cnpj": cnpj, "sector": sector, "size": size,
                                "website": website, "phone": phone, "email": email, "address": address, "notes": notes})
                st.success(f"Empresa '{name}' criada!")
                st.session_state["show_company_form"] = False
                st.rerun()
        if cancel:
            st.session_state["show_company_form"] = False
            st.rerun()


def _company_detail(company_id: int):
    co = get_company(company_id)
    if not co:
        return

    st.markdown(f"""
    <div class="crm-card" style="border-left-color:#B07FFF; padding:16px">
        <div style="font-size:1.1rem; font-weight:800; color:#F0F0F0">🏢 {co['name']}</div>
        <div style="color:#999; margin:4px 0">{co.get('sector','') or ''} · {co.get('size','') or ''}</div>
        <div>
            {('🌐 ' + co['website'] + '&nbsp;&nbsp;') if co.get('website') else ''}
            {('📞 ' + co['phone']) if co.get('phone') else ''}
        </div>
        {('<div style="color:#888; margin-top:4px">📍 ' + co['address'] + '</div>') if co.get('address') else ''}
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    if c1.button("✏️ Editar", key=f"edit_co_{company_id}"):
        st.session_state[f"edit_co_{company_id}"] = True
    if c2.button("🗑️ Excluir", key=f"del_co_{company_id}"):
        delete_company(company_id); st.rerun()

    if st.session_state.get(f"edit_co_{company_id}"):
        with st.form(f"edit_co_form_{company_id}"):
            c1, c2 = st.columns(2)
            name    = c1.text_input("Razão Social", value=co["name"])
            cnpj    = c2.text_input("CNPJ", value=co.get("cnpj") or "")
            c3, c4  = st.columns(2)
            sector  = c3.text_input("Setor", value=co.get("sector") or "")
            sizes   = ["", "MEI", "Micro", "Pequena", "Média", "Grande"]
            size    = c4.selectbox("Porte", sizes, index=sizes.index(co.get("size") or "") if co.get("size") in sizes else 0)
            website = st.text_input("Website", value=co.get("website") or "")
            notes   = st.text_area("Observações", value=co.get("notes") or "", height=60)
            if st.form_submit_button("💾 Salvar", type="primary"):
                update_company(company_id, {"name": name, "cnpj": cnpj, "sector": sector, "size": size,
                                            "website": website, "notes": notes})
                st.session_state[f"edit_co_{company_id}"] = False
                st.rerun()

    # Contatos da empresa
    co_contacts = get_contacts(company_id=company_id)
    if co_contacts:
        with st.expander(f"👤 Contatos da Empresa ({len(co_contacts)})"):
            for c in co_contacts:
                st.markdown(f"- **{c['name']}** — {c.get('cargo') or ''} {c.get('email') or ''}")

    # Negócios da empresa
    co_deals = get_deals(company_id=company_id, status="aberto")
    if co_deals:
        with st.expander(f"💼 Negócios ({len(co_deals)})"):
            for d in co_deals:
                st.markdown(f"- **{d['title']}** — {_fmt_brl(d['value'])} ({d.get('stage_name') or 'sem etapa'})")


# ── Atividades ────────────────────────────────────────────────────────────────

def render_activities():
    st.markdown('<div class="section-title">📅 Gestão de Atividades</div>', unsafe_allow_html=True)

    col_f1, col_f2, col_f3, col_add = st.columns([2, 2, 2, 1])
    with col_f1:
        status_f = st.selectbox("Status", ["todos", "pendente", "concluida", "atrasada"], key="act_status")
    with col_f2:
        users = get_users()
        owner_f = st.selectbox("Responsável", ["Todos"] + [u["name"] for u in users], key="act_owner")
    with col_f3:
        date_from = st.date_input("A partir de", value=date.today(), key="act_date_from")
    with col_add:
        if st.button("➕ Nova Atividade", type="primary"):
            st.session_state["show_activity_form"] = True

    if st.session_state.get("show_activity_form"):
        _form_new_activity()

    # Atualiza atividades atrasadas
    _update_overdue_activities()

    status_filter = None if status_f == "todos" else status_f
    owner_filter  = "" if owner_f == "Todos" else owner_f
    activities    = get_activities(
        status=status_filter, owner=owner_filter,
        date_from=str(date_from), limit=200
    )

    if not activities:
        st.info("Nenhuma atividade encontrada.")
        return

    # Agrupar por data
    grouped: dict = {}
    for a in activities:
        day = a.get("due_date", "Sem data")[:10]
        grouped.setdefault(day, []).append(a)

    for day, acts in grouped.items():
        try:
            dt = datetime.strptime(day, "%Y-%m-%d")
            label = dt.strftime("%d/%m/%Y (%A)").replace("Monday", "Segunda").replace("Tuesday", "Terça") \
                    .replace("Wednesday", "Quarta").replace("Thursday", "Quinta").replace("Friday", "Sexta") \
                    .replace("Saturday", "Sábado").replace("Sunday", "Domingo")
        except Exception:
            label = day

        is_today   = day == str(date.today())
        is_overdue = day < str(date.today())
        day_color  = "#FF4444" if is_overdue else "#FFD700" if is_today else "#4D9FFF"

        st.markdown(f"<div style='font-weight:700; color:{day_color}; margin:12px 0 6px'>{label}</div>",
                    unsafe_allow_html=True)

        for a in acts:
            icon = ACTIVITY_ICONS.get(a["type"], "•")
            em, color = STATUS_BADGE.get(a["status"], ("⚪", "#888"))
            col1, col2, col3, col4 = st.columns([5, 2, 1, 1])
            col1.markdown(f"{em} {icon} **{a['title']}**"
                          + (f" — {a.get('contact_name') or ''}" if a.get("contact_name") else "")
                          + (f" / {a.get('deal_title') or ''}" if a.get("deal_title") else ""))
            col2.markdown(f"<span style='color:#999;font-size:0.8rem'>{a.get('due_time','') or ''} · {a.get('duration',30)}min · {a.get('owner','') or ''}</span>",
                          unsafe_allow_html=True)
            with col3:
                if a["status"] == "pendente":
                    if st.button("✅", key=f"done_act_{a['id']}", help="Marcar como concluída"):
                        update_activity_status(a["id"], "concluida"); st.rerun()
            with col4:
                if st.button("🗑️", key=f"del_act_{a['id']}"):
                    delete_activity(a["id"]); st.rerun()


def _update_overdue_activities():
    """Marca como atrasadas as atividades pendentes com data passada."""
    from dashboard import crm_db
    today = str(date.today())
    with crm_db.get_connection() as conn:
        conn.execute(
            "UPDATE activities SET status='atrasada', updated_at=datetime('now','localtime') "
            "WHERE status='pendente' AND due_date < ?", (today,)
        )


def _form_new_activity():
    contacts  = get_contacts(limit=500)
    deals     = get_deals(limit=500, status="aberto")
    companies = get_companies(limit=500)
    users     = get_users()

    with st.form("form_new_activity", clear_on_submit=True):
        st.markdown("**Nova Atividade**")
        c1, c2, c3 = st.columns(3)
        act_type = c1.selectbox("Tipo", ["ligacao", "email", "reuniao", "tarefa", "whatsapp", "almoco", "prazo"],
                                 format_func=lambda x: f"{ACTIVITY_ICONS.get(x,'')} {x.capitalize()}")
        title    = c2.text_input("Título *")
        due_date = c3.date_input("Data", value=date.today())
        c4, c5, c6 = st.columns(3)
        due_time  = c4.time_input("Hora")
        duration  = c5.number_input("Duração (min)", min_value=15, max_value=480, value=30, step=15)
        owner_opts = [u["name"] for u in users]
        sel_owner  = c6.selectbox("Responsável", owner_opts if owner_opts else ["—"])
        c7, c8, c9 = st.columns(3)
        contact_opts = {"-- Nenhum --": None, **{c["name"]: c["id"] for c in contacts}}
        company_opts = {"-- Nenhuma --": None, **{co["name"]: co["id"] for co in companies}}
        deal_opts    = {"-- Nenhum --": None, **{d["title"]: d["id"] for d in deals}}
        sel_contact  = c7.selectbox("Contato", list(contact_opts.keys()))
        sel_company  = c8.selectbox("Empresa", list(company_opts.keys()))
        sel_deal     = c9.selectbox("Negócio", list(deal_opts.keys()))
        description  = st.text_area("Descrição", height=60)
        c_sub, c_cancel = st.columns(2)
        submitted = c_sub.form_submit_button("✅ Criar Atividade", type="primary")
        cancel    = c_cancel.form_submit_button("✖ Cancelar")
        if submitted:
            if not title:
                st.error("Título obrigatório.")
            else:
                create_activity({
                    "type": act_type, "title": title, "description": description,
                    "due_date": str(due_date), "due_time": str(due_time)[:5],
                    "duration": duration, "owner": sel_owner, "recurrence": "none",
                    "contact_id": contact_opts[sel_contact],
                    "company_id": company_opts[sel_company],
                    "deal_id": deal_opts[sel_deal],
                })
                st.success("Atividade criada!")
                st.session_state["show_activity_form"] = False
                st.rerun()
        if cancel:
            st.session_state["show_activity_form"] = False
            st.rerun()


# ── Produtos CRM ──────────────────────────────────────────────────────────────

def render_products():
    st.markdown('<div class="section-title">📁 Catálogo de Produtos / Serviços</div>', unsafe_allow_html=True)

    col_s, col_add = st.columns([4, 1])
    with col_s:
        search = st.text_input("🔍 Buscar produto", key="prod_search")
    with col_add:
        if st.button("➕ Novo Produto", type="primary"):
            st.session_state["show_prod_form"] = True

    if st.session_state.get("show_prod_form"):
        with st.form("form_new_product", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name  = c1.text_input("Nome do Produto *")
            code  = c2.text_input("Código SKU")
            c3, c4, c5 = st.columns(3)
            price    = c3.number_input("Preço (R$)", min_value=0.0, step=10.0)
            category = c4.text_input("Categoria")
            desc     = c5.text_input("Descrição")
            c_sub, c_cancel = st.columns(2)
            if c_sub.form_submit_button("✅ Salvar", type="primary"):
                if name:
                    create_crm_product({"name": name, "code": code, "price": price,
                                        "category": category, "description": desc})
                    st.session_state["show_prod_form"] = False
                    st.rerun()
            if c_cancel.form_submit_button("✖ Cancelar"):
                st.session_state["show_prod_form"] = False
                st.rerun()

    products = get_crm_products(search=search)
    if not products:
        st.info("Nenhum produto cadastrado.")
        return

    for p in products:
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.markdown(f"**{p['name']}** `{p.get('code') or ''}`")
        c2.markdown(f"{p.get('category') or '—'}")
        c3.markdown(f"**{_fmt_brl(p['price'])}**")
        if c4.button("🗑️", key=f"del_prod_{p['id']}"):
            delete_crm_product(p["id"]); st.rerun()


# ── Relatórios ────────────────────────────────────────────────────────────────

def render_reports():
    st.markdown('<div class="section-title">📈 Relatórios e Analytics</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Funil", "📅 Vendas por Mês", "👥 Performance", "🤖 Automações"])

    with tab1:
        _report_funnel()
    with tab2:
        _report_monthly()
    with tab3:
        _report_performance()
    with tab4:
        _report_automations()


def _report_funnel():
    pipelines = get_pipelines()
    if not pipelines:
        st.info("Nenhum pipeline."); return

    pip_names = {p["name"]: p["id"] for p in pipelines}
    sel = st.selectbox("Pipeline", list(pip_names.keys()), key="rep_pip")
    summary = get_pipeline_summary(pip_names[sel])

    if not summary:
        st.info("Nenhum dado."); return

    names  = [s["name"] for s in summary]
    values = [s["total_value"] for s in summary]
    counts = [s["deal_count"] for s in summary]
    colors = [s["color"] for s in summary]

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Funnel(
            y=names, x=counts, textinfo="value+percent initial",
            marker={"color": colors},
        ))
        fig.update_layout(
            title="Negócios por Etapa",
            paper_bgcolor="#0D0D0D", plot_bgcolor="#0D0D0D",
            font={"color": "#F0F0F0"}, height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(
            x=names, y=values, color=names, color_discrete_sequence=colors,
            title="Valor por Etapa (R$)",
            labels={"x": "Etapa", "y": "Valor (R$)"},
        )
        fig2.update_layout(
            paper_bgcolor="#0D0D0D", plot_bgcolor="#0D0D0D",
            font={"color": "#F0F0F0"}, showlegend=False, height=350,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Tabela resumo
    df = pd.DataFrame(summary)[["name", "deal_count", "total_value", "avg_probability"]]
    df.columns = ["Etapa", "Negócios", "Valor Total (R$)", "Prob. Média (%)"]
    df["Valor Total (R$)"] = df["Valor Total (R$)"].apply(_fmt_brl)
    df["Prob. Média (%)"]  = df["Prob. Média (%)"].apply(lambda x: f"{x:.0f}%")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # KPIs
    total_in_funnel = sum(s["total_value"] for s in summary)
    weighted        = sum(s["total_value"] * s["avg_probability"] / 100 for s in summary)
    conv_rate       = get_conversion_rate()
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor Total no Funil", _fmt_brl(total_in_funnel))
    c2.metric("Receita Ponderada (forecast)", _fmt_brl(weighted))
    c3.metric("Taxa de Conversão Geral", f"{conv_rate}%")


def _report_monthly():
    months_back = st.slider("Período (meses)", 3, 24, 6, key="rep_months")
    data = get_deals_by_month(months_back)

    if not data:
        st.info("Sem dados suficientes para o período."); return

    df = pd.DataFrame(data)
    df["month_label"] = pd.to_datetime(df["month"]).dt.strftime("%b/%y")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df, x="month_label", y=["total", "ganhos"], barmode="group",
                     title="Negócios Criados vs Ganhos",
                     labels={"value": "Quantidade", "month_label": "Mês"},
                     color_discrete_map={"total": "#4D9FFF", "ganhos": "#00C851"})
        fig.update_layout(paper_bgcolor="#0D0D0D", plot_bgcolor="#0D0D0D",
                          font={"color": "#F0F0F0"}, height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.line(df, x="month_label", y="receita", title="Receita Gerada (R$)",
                       markers=True, line_shape="spline",
                       labels={"receita": "Receita (R$)", "month_label": "Mês"},
                       color_discrete_sequence=["#FFD700"])
        fig2.update_layout(paper_bgcolor="#0D0D0D", plot_bgcolor="#0D0D0D",
                           font={"color": "#F0F0F0"}, height=320)
        st.plotly_chart(fig2, use_container_width=True)

    # Atividades por tipo
    act_summary = get_activities_summary()
    if act_summary:
        df_act = pd.DataFrame(act_summary)
        fig3 = px.pie(df_act, names="type", values="count", title="Atividades por Tipo",
                      hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
        fig3.update_layout(paper_bgcolor="#0D0D0D", font={"color": "#F0F0F0"}, height=300)
        st.plotly_chart(fig3, use_container_width=True)


def _report_performance():
    top_owners = get_top_owners(10)
    if not top_owners:
        st.info("Nenhum dado de performance disponível.")
        return

    df = pd.DataFrame(top_owners)
    fig = px.bar(df, x="owner", y="receita", color="ganhos",
                 title="Top Vendedores — Receita Gerada",
                 labels={"owner": "Vendedor", "receita": "Receita (R$)", "ganhos": "Neg. Ganhos"},
                 color_continuous_scale="Greens")
    fig.update_layout(paper_bgcolor="#0D0D0D", plot_bgcolor="#0D0D0D",
                      font={"color": "#F0F0F0"}, height=350)
    st.plotly_chart(fig, use_container_width=True)

    df_display = df.copy()
    df_display["receita"] = df_display["receita"].apply(_fmt_brl)
    df_display.columns = ["Vendedor", "Total Negócios", "Ganhos", "Receita"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Metas (usuários CRM)
    st.markdown("### 🎯 Metas por Vendedor")
    users = get_users()
    won_revenue = sum_deals_value("ganho")
    for u in users:
        meta = u.get("meta_mensal") or 0
        if meta > 0:
            pct = min(won_revenue / meta * 100, 100)
            st.markdown(f"**{u['name']}** — Meta: {_fmt_brl(meta)}")
            st.progress(int(pct), text=f"{pct:.1f}% atingido")


def _report_automations():
    st.markdown("### 🤖 Automações Configuradas")
    automations = get_automations()

    if not automations:
        st.info("Nenhuma automação configurada.")
    else:
        for a in automations:
            with st.container():
                c1, c2, c3 = st.columns([5, 2, 1])
                active = bool(a["active"])
                icon   = "✅" if active else "⏸️"
                c1.markdown(f"{icon} **{a['name']}** — Gatilho: `{a['trigger_type']}`"
                            + f" | Execuções: **{a['executions']}**")
                c2.markdown(f"<span style='color:#888;font-size:0.8rem'>{a['created_at'][:10]}</span>",
                            unsafe_allow_html=True)
                if c3.button("Toggle", key=f"tog_auto_{a['id']}"):
                    toggle_automation(a["id"], not active)
                    st.rerun()

    st.markdown("---")
    st.markdown("### ➕ Nova Automação")

    triggers = {
        "deal_created":        "Negócio Criado",
        "deal_status_changed": "Status do Negócio Alterado",
        "stage_changed":       "Etapa Alterada",
        "activity_done":       "Atividade Concluída",
        "contact_created":     "Contato Criado",
    }
    actions_opts = {
        "notify":       "Enviar Notificação",
        "create_task":  "Criar Tarefa",
        "assign_owner": "Atribuir Responsável",
        "add_tag":      "Adicionar Tag",
        "move_stage":   "Mover Etapa",
    }

    with st.form("form_new_auto", clear_on_submit=True):
        name_a    = st.text_input("Nome da Automação *")
        trigger   = st.selectbox("Gatilho", list(triggers.keys()),
                                 format_func=lambda x: triggers[x])
        action    = st.selectbox("Ação", list(actions_opts.keys()),
                                 format_func=lambda x: actions_opts[x])
        action_val = st.text_input("Valor da Ação (ex: nome do responsável, tag, etc.)")
        if st.form_submit_button("✅ Criar Automação", type="primary"):
            if name_a:
                create_automation({
                    "name": name_a, "trigger_type": trigger,
                    "trigger_config": {},
                    "actions": [{"type": action, "value": action_val}],
                })
                st.success("Automação criada!")
                st.rerun()


# ── Configurações CRM ─────────────────────────────────────────────────────────

def render_crm_settings():
    st.markdown('<div class="section-title">⚙️ Configurações do CRM</div>', unsafe_allow_html=True)

    tab_users, tab_tags, tab_pipeline = st.tabs(["👥 Usuários", "🏷️ Tags", "🔧 Pipeline"])

    with tab_users:
        users = get_users()
        if users:
            df = pd.DataFrame(users)[["id", "name", "email", "role", "meta_mensal", "created_at"]]
            df.columns = ["ID", "Nome", "E-mail", "Perfil", "Meta Mensal", "Criado em"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum usuário.")

        with st.form("form_new_user", clear_on_submit=True):
            st.markdown("**Adicionar Usuário**")
            c1, c2 = st.columns(2)
            uname = c1.text_input("Nome *")
            uemail = c2.text_input("E-mail *")
            c3, c4 = st.columns(2)
            urole = c3.selectbox("Perfil", ["vendedor", "gerente", "admin", "visualizador"])
            umeta = c4.number_input("Meta Mensal (R$)", min_value=0.0, step=100.0)
            if st.form_submit_button("Adicionar"):
                if uname and uemail:
                    from dashboard.crm_db import get_connection
                    with get_connection() as conn:
                        conn.execute(
                            "INSERT OR IGNORE INTO crm_users (name, email, role, meta_mensal) VALUES (?,?,?,?)",
                            (uname, uemail, urole, umeta)
                        )
                    st.rerun()

    with tab_tags:
        tags = get_tags()
        if tags:
            for t in tags:
                st.markdown(f'<span class="crm-badge" style="background:{t["color"]}33;color:{t["color"]}">{t["name"]}</span>',
                            unsafe_allow_html=True)

        with st.form("form_new_tag", clear_on_submit=True):
            c1, c2 = st.columns(2)
            tname  = c1.text_input("Nome da Tag *")
            tcolor = c2.color_picker("Cor", "#4D9FFF")
            if st.form_submit_button("Adicionar Tag"):
                if tname:
                    from dashboard.crm_db import get_connection
                    with get_connection() as conn:
                        conn.execute("INSERT OR IGNORE INTO tags (name, color) VALUES (?,?)", (tname, tcolor))
                    st.rerun()

    with tab_pipeline:
        pipelines = get_pipelines()
        for p in pipelines:
            st.markdown(f"**Pipeline:** {p['name']} (ID: {p['id']})")
            stages = get_stages(p["id"])
            for s in stages:
                st.markdown(f"  └─ <span style='color:{s['color']}'>■</span> {s['name']} ({s['probability']}%)",
                            unsafe_allow_html=True)

        with st.form("form_new_pipeline", clear_on_submit=True):
            pname = st.text_input("Nome do Novo Pipeline *")
            pdesc = st.text_input("Descrição")
            if st.form_submit_button("Criar Pipeline"):
                if pname:
                    from dashboard.crm_db import get_connection
                    with get_connection() as conn:
                        conn.execute("INSERT INTO pipelines (name, description) VALUES (?,?)", (pname, pdesc))
                    st.rerun()


# ── Entry Point ───────────────────────────────────────────────────────────────

def render_crm():
    """Ponto de entrada do módulo CRM — chamado pelo app.py."""
    init_db()

    st.markdown(CRM_CSS, unsafe_allow_html=True)

    # Navegação CRM
    crm_tabs = st.tabs([
        "🏠 Dashboard",
        "📊 Pipeline",
        "👤 Contatos",
        "🏢 Empresas",
        "📅 Atividades",
        "📁 Produtos",
        "📈 Relatórios",
        "⚙️ Configurações",
    ])

    with crm_tabs[0]:
        st.markdown('<div class="section-title">🏠 Dashboard CRM</div>', unsafe_allow_html=True)
        render_crm_kpis()

        # Mini pipeline preview
        st.markdown("---")
        st.markdown("**Pipeline — Visão Rápida**")
        pipelines = get_pipelines()
        if pipelines:
            summary = get_pipeline_summary(pipelines[0]["id"])
            if summary:
                cols = st.columns(len(summary))
                for col, s in zip(cols, summary):
                    col.markdown(f"""
                    <div style="background:#1A1A1A; border-radius:10px; padding:14px; text-align:center;
                                border-top:3px solid {s['color']}">
                        <div style="color:{s['color']}; font-weight:700; font-size:0.85rem">{s['name']}</div>
                        <div style="font-size:1.4rem; font-weight:800; color:#F0F0F0">{s['deal_count']}</div>
                        <div style="font-size:0.78rem; color:#999">{_fmt_brl(s['total_value'])}</div>
                    </div>""", unsafe_allow_html=True)

        # Próximas atividades
        st.markdown("---")
        st.markdown("**📅 Próximas Atividades**")
        upcoming = get_activities(status="pendente",
                                   date_from=str(date.today()),
                                   date_to=str(date.today() + timedelta(days=7)),
                                   limit=8)
        if upcoming:
            for a in upcoming:
                icon = ACTIVITY_ICONS.get(a["type"], "•")
                st.markdown(f"- {icon} **{a['title']}** — {a.get('due_date','')[:10]} "
                            + (f"· {a.get('contact_name','')}" if a.get("contact_name") else "")
                            + (f" · *{a.get('owner','')}*" if a.get("owner") else ""))
        else:
            st.info("Nenhuma atividade nos próximos 7 dias.")

        # Negócios com fechamento próximo
        st.markdown("---")
        st.markdown("**💼 Negócios — Fechamento Próximo (30 dias)**")
        closing = get_deals(status="aberto",
                             date_from=str(date.today()),
                             limit=500)
        closing_soon = [d for d in closing
                        if d.get("close_date") and _days_until(d["close_date"]) <= 30][:8]
        if closing_soon:
            for d in closing_soon:
                days = _days_until(d["close_date"])
                color = "#FF4444" if days <= 7 else "#FFD700" if days <= 14 else "#00C851"
                st.markdown(f"- 💼 **{d['title']}** — {_fmt_brl(d['value'])} "
                            f"· <span style='color:{color}'>{days}d restantes</span> "
                            f"· {d.get('owner','') or ''}",
                            unsafe_allow_html=True)
        else:
            st.info("Nenhum negócio com fechamento iminente.")

    with crm_tabs[1]:
        render_pipeline()

    with crm_tabs[2]:
        render_contacts()

    with crm_tabs[3]:
        render_companies()

    with crm_tabs[4]:
        render_activities()

    with crm_tabs[5]:
        render_products()

    with crm_tabs[6]:
        render_reports()

    with crm_tabs[7]:
        render_crm_settings()
