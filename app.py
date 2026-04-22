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

# ==========================================
# 3. FUNÇÕES DE BANCO DE DADOS (RR)
# ==========================================
def carregar_rr(data_selecionada):
    """Busca apenas os dados de RR para a data selecionada"""
    resposta = supabase.table("visitas_operacionais").select("*") \
        .eq("data", str(data_selecionada)) \
        .eq("tipo", "RR") \
        .execute()
    return pd.DataFrame(resposta.data)

def incluir_rr(data_rr, setor, meta, realizado):
    """Insere um novo registro de RR no banco"""
    supabase.table("visitas_operacionais").insert({
        "data": str(data_rr),
        "setor": setor,
        "turno": "N/A", # RR não especificou turno inicialmente
        "tipo": "RR",
        "meta": meta,
        "realizado": realizado
    }).execute()

def excluir_rr(id_registro):
    """Exclui um registro baseado no ID"""
    supabase.table("visitas_operacionais").delete().eq("id", id_registro).execute()


# ==========================================
# 4. INTERFACE DO USUÁRIO (FRONTEND)
# ==========================================

# Estilização Global Customizada (Opcional para dar cara de sistema)
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
# ABA 1: CONTROLE DE RR
# ==========================================
with aba_rr:
    
    # Carrega dados do dia
    df_rr = carregar_rr(data_filtro)
    
    # --- RESUMO EXECUTIVO (KPIs) ---
    st.subheader(f"📊 Resumo Diário (RR) - {data_filtro.strftime('%d/%m/%Y')}")
    
    total_meta = int(df_rr['meta'].sum()) if not df_rr.empty else 0
    total_realizado = int(df_rr['realizado'].sum()) if not df_rr.empty else 0
    saldo = total_meta - total_realizado

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🎯 Meta Total do Dia", value=total_meta)
    with col2:
        st.metric(label="✅ Total Realizado", value=total_realizado)
    with col3:
        # Mostra o saldo. Se for negativo (excedeu a meta), fica verde. Se positivo (falta), fica vermelho.
        st.metric(label="⚖️ Saldo (Meta - Realizado)", value=saldo, delta=f"Faltam {saldo}" if saldo > 0 else "Meta Atingida", delta_color="inverse")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- PAINÉIS DE OPERAÇÃO (CRUD) ---
    col_add, col_view = st.columns([1, 1.5], gap="large")

    # PAINEL DE INCLUSÃO
    with col_add:
        with st.container(border=True):
            st.markdown("#### ➕ Incluir Novo Registro (RR)")
            
            # Seleção de Área altera a lista de setores
            area_selecionada = st.radio("Selecione a Área", ["Patrimonial", "Facilities"], horizontal=True)
            opcoes_setor = SETORES_PATRIMONIAL if area_selecionada == "Patrimonial" else SETORES_FACILITIES
            
            setor_input = st.selectbox("Setor / Unidade", opcoes_setor)
            
            col_m, col_r = st.columns(2)
            meta_input = col_m.number_input("Meta Diária", min_value=0, step=1, value=0)
            realizado_input = col_r.number_input("Realizado", min_value=0, step=1, value=0)
            
            if st.button("Salvar Registro", type="primary", use_container_width=True):
                with st.spinner("Salvando..."):
                    incluir_rr(data_filtro, setor_input, meta_input, realizado_input)
                st.success("✅ Registro incluído com sucesso!")
                st.rerun() # Recarrega a página para atualizar os gráficos

    # PAINEL DE LEITURA E EXCLUSÃO
    with col_view:
        with st.container(border=True):
            st.markdown("#### 📋 Registros Efetuados")
            
            if df_rr.empty:
                st.info("Nenhum registro de RR encontrado para esta data.")
            else:
                # Mostra tabela formatada limpa (sem parecer excel de edição)
                df_visual = df_rr[["setor", "meta", "realizado"]].copy()
                df_visual.columns = ["Setor / Unidade", "Meta", "Realizado"]
                st.dataframe(df_visual, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.markdown("#### 🗑️ Excluir Registro")
                st.caption("Selecione um lançamento abaixo para excluí-lo do banco de dados.")
                
                # Cria uma lista formatada para o usuário saber o que está excluindo
                opcoes_excluir = df_rr.apply(lambda x: f"{x['setor']} (Realizado: {x['realizado']}) | ID: {x['id']}", axis=1).tolist()
                
                selecao_excluir = st.selectbox("Selecione o registro:", ["Nenhum"] + opcoes_excluir, label_visibility="collapsed")
                
                if selecao_excluir != "Nenhum":
                    if st.button("❌ Excluir Selecionado", type="secondary"):
                        id_para_excluir = selecao_excluir.split("ID: ")[1]
                        with st.spinner("Excluindo..."):
                            excluir_rr(id_para_excluir)
                        st.success("Registro excluído!")
                        st.rerun()


# ==========================================
# ABA 2: VISITAS OPERACIONAIS (Em Construção)
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