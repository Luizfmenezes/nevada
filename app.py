import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date

# ==========================================
# 1. CONFIGURAÇÕES DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(
    page_title="Sistema de Gestão Operacional", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ATENÇÃO: Substitua pelas suas credenciais do Supabase
SUPABASE_URL = "https://uydnjzjefwqltvhbbscs.supabase.co"
SUPABASE_KEY = "sb_publishable_ehhX5M3x4pwxvQ1KDye56g_rZqJJLxr"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# ==========================================
# 2. LISTAS E PARÂMETROS
# ==========================================
SETORES_PATRIMONIAL = [
    "S.Águia", "S.Arco", "S.Delta", "S.Flecha", "S.Extremo", 
    "S.Rmc", "Bombeiros SP", "S.Extrema MG", "S.Curitiba", "S.Rio de Janeiro"
]

SETORES_FACILITIES = [
    "F.Águia", "F.Arco + F.Extremo", "F.Delta + F.Flecha", 
    "F.Curitiba", "F.Rio de Janeiro"
]

# Cria um DataFrame base com todos os setores para forçar a exibição na grade
df_base_setores = pd.DataFrame(
    [{"Área": "🏢 Patrimonial", "setor": s} for s in SETORES_PATRIMONIAL] + 
    [{"Área": "🛠️ Facilities", "setor": s} for s in SETORES_FACILITIES]
)

# ==========================================
# 3. FUNÇÕES DE BANCO DE DADOS (RR)
# ==========================================
def carregar_rr(data_selecionada):
    """Busca os dados de RR do banco e faz um 'merge' com a lista de todos os setores."""
    resposta = supabase.table("visitas_operacionais").select("*") \
        .eq("data", str(data_selecionada)) \
        .eq("tipo", "RR") \
        .execute()
    
    df_db = pd.DataFrame(resposta.data)
    
    # Cruza a lista base de setores com o que veio do banco
    if not df_db.empty:
        df_merged = pd.merge(df_base_setores, df_db, on="setor", how="left")
        df_merged['meta'] = df_merged['meta'].fillna(0).astype(int)
        df_merged['realizado'] = df_merged['realizado'].fillna(0).astype(int)
    else:
        # Se não tem nada no banco, cria a tabela zerada
        df_merged = df_base_setores.copy()
        df_merged['id'] = None
        df_merged['meta'] = 0
        df_merged['realizado'] = 0
        
    return df_merged

def sincronizar_rr(data_rr, df_original, df_editado):
    """Compara a tabela original com a editada e envia apenas as alterações para o Supabase"""
    alteracoes = 0
    for index, row in df_editado.iterrows():
        orig = df_original.iloc[index]
        
        # Verifica se houve alguma mudança nos números
        if row['meta'] != orig['meta'] or row['realizado'] != orig['realizado']:
            
            # Se não tem ID, é um registro novo para esse dia (INSERT)
            if pd.isna(row['id']):
                supabase.table("visitas_operacionais").insert({
                    "data": str(data_rr),
                    "setor": row['setor'],
                    "turno": "N/A",
                    "tipo": "RR",
                    "meta": int(row['meta']),
                    "realizado": int(row['realizado'])
                }).execute()
            # Se tem ID, atualiza o existente (UPDATE)
            else:
                supabase.table("visitas_operacionais").update({
                    "meta": int(row['meta']),
                    "realizado": int(row['realizado'])
                }).eq("id", row['id']).execute()
                
            alteracoes += 1
            
    return alteracoes


# ==========================================
# 4. INTERFACE DO USUÁRIO (FRONTEND)
# ==========================================

# Estilização Global Customizada
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Sistema de Gestão Operacional")
st.markdown("---")

# ---------------- BARRA LATERAL ----------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=80)
st.sidebar.header("Filtros Globais")
st.sidebar.caption("As datas selecionadas aqui refletem em todas as abas do sistema.")
data_filtro = st.sidebar.date_input("📅 Selecione a Data", date.today())


# ---------------- NAVEGAÇÃO POR ABAS ----------------
aba_rr, aba_visitas = st.tabs(["📋 Controle de RR", "🛡️ Visitas Operacionais"])

# ==========================================
# ABA 1: CONTROLE DE RR (Grade Otimizada)
# ==========================================
with aba_rr:
    
    # Carrega a tabela mestra (com dados do banco ou zerada)
    df_rr = carregar_rr(data_filtro)
    
    # --- CÁLCULOS DINÂMICOS (STATUS E SALDO) ---
    df_rr['saldo'] = df_rr['realizado'] - df_rr['meta']
    
    def definir_status(row):
        if row['meta'] == 0:
            return "⚪ Sem Meta"
        pct = row['realizado'] / row['meta']
        if pct >= 1.0:
            return "🟢 Atingida"
        elif pct >= 0.8:
            return "🟡 Atenção"
        else:
            return "🔴 Crítico"
            
    df_rr['status'] = df_rr.apply(definir_status, axis=1)
    
    # --- RESUMO EXECUTIVO (KPIs) ---
    st.subheader(f"📊 Resumo Diário (RR) - {data_filtro.strftime('%d/%m/%Y')}")
    
    total_meta = int(df_rr['meta'].sum())
    total_realizado = int(df_rr['realizado'].sum())
    saldo = total_meta - total_realizado

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🎯 Meta Total do Dia", value=total_meta)
    with col2:
        st.metric(label="✅ Total Realizado", value=total_realizado)
    with col3:
        st.metric(label="⚖️ Saldo (Meta - Realizado)", value=saldo, delta=f"Faltam {saldo}" if saldo > 0 else "Metas Batidas", delta_color="inverse")
    
    st.markdown("---")

    # --- GRADE DE EDIÇÃO RÁPIDA ---
    st.markdown("#### 📝 Lançamento em Grade (Edição Rápida)")
    st.caption("Clique diretamente nas colunas **Meta** ou **Realizado** para alterar os valores. As alterações só serão salvas após clicar em Sincronizar.")
    
    # Configuração visual das colunas da tabela
    config_colunas = {
        "id": None, # Oculta o ID interno
        "data": None,
        "tipo": None,
        "turno": None,
        "ultima_atualizacao": None,
        "Área": st.column_config.TextColumn("Categoria", disabled=True, width="medium"),
        "setor": st.column_config.TextColumn("Setor / Unidade", disabled=True, width="medium"),
        "meta": st.column_config.NumberColumn("🎯 Meta (Editar)", min_value=0, step=1, required=True),
        "realizado": st.column_config.NumberColumn("✅ Realizado (Editar)", min_value=0, step=1, required=True),
        "saldo": st.column_config.NumberColumn("⚖️ Saldo", disabled=True),
        "status": st.column_config.TextColumn("🚦 Status", disabled=True)
    }

    # Renderiza a grade editável na tela (height ajustado para caber tudo sem rolagem)
    altura_tabela = (len(df_rr) * 36) + 40 

    df_editado = st.data_editor(
        df_rr,
        column_config=config_colunas,
        hide_index=True,
        use_container_width=True,
        height=altura_tabela,
        key="editor_rr"
    )
    
    # --- BOTÃO DE SINCRONISMO ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 3])
    
    with col_btn:
        if st.button("🔄 Sincronizar Dados no Banco", type="primary", use_container_width=True):
            with st.spinner("Analisando alterações e salvando no Supabase..."):
                qtd_alteracoes = sincronizar_rr(data_filtro, df_rr, df_editado)
                
            if qtd_alteracoes > 0:
                st.success(f"✅ Sincronizado! {qtd_alteracoes} registro(s) atualizados com sucesso.")
                st.balloons()
            else:
                st.info("Nenhuma alteração foi detectada.")
            st.rerun() # Atualiza a tela para refletir os novos KPIs


# ==========================================
# ABA 2: VISITAS OPERACIONAIS (Aguardando Parâmetros)
# ==========================================
with aba_visitas:
    st.subheader("🛡️ Visitas Operacionais")
    
    with st.container(border=True):
        st.info("💡 **Aba preparada com sucesso!** Estou aguardando os seus parâmetros para configurar esta tela.")
        st.write("Por favor, me informe:")
        st.markdown("""
        * Quais serão os **setores** desta aba?
        * Vai ter divisão de **Turno** (Diurno/Noturno)?
        * O preenchimento será individual como no RR ou em grade de edição rápida?
        """)