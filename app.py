import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date

# ==========================================
# 1. CONFIGURAÇÕES DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(
    page_title="Gestão de Visitas e RR", 
    page_icon="🛡️", 
    layout="wide"
)

# ATENÇÃO: Substitua pelas suas credenciais do Supabase
SUPABASE_URL = "https://uydnjzjefwqltvhbbscs.supabase.co"
SUPABASE_KEY = "sb_publishable_ehhX5M3x4pwxvQ1KDye56g_rZqJJLxr"

# Inicializa a conexão com o banco de forma cacheada para ficar rápido
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# ==========================================
# 2. FUNÇÕES DE DADOS
# ==========================================
def carregar_dados(data_selecionada, turno_selecionado):
    """Busca os dados no Supabase baseados nos filtros do usuário"""
    query = supabase.table("visitas_operacionais").select("*").eq("data", str(data_selecionada))
    
    if turno_selecionado != "Todos":
        query = query.eq("turno", turno_selecionado)
        
    resposta = query.execute()
    return pd.DataFrame(resposta.data)

def salvar_alteracoes(df_original, df_editado):
    """Compara o antes e depois e envia apenas o que mudou para o Supabase"""
    alteracoes = 0
    for index, row in df_editado.iterrows():
        valor_original = df_original.loc[index, 'realizado']
        valor_novo = row['realizado']
        
        if valor_original != valor_novo:
            # Envia o UPDATE (atualização) para o banco online
            supabase.table("visitas_operacionais").update({
                "realizado": int(valor_novo)
            }).eq("id", row['id']).execute()
            alteracoes += 1
            
    return alteracoes

# ==========================================
# 3. INTERFACE DO USUÁRIO (FRONTEND)
# ==========================================
st.title("🛡️ Painel de Visitas Operacionais e RR's")
st.markdown("---")

# Barra lateral para Filtros
st.sidebar.header("Filtros de Pesquisa")
data_filtro = st.sidebar.date_input("Data da Visita", date.today())
turno_filtro = st.sidebar.selectbox("Turno", ["Todos", "Diurno", "Noturno"])

# Carrega os dados com base nos filtros
df_atual = carregar_dados(data_filtro, turno_filtro)

if df_atual.empty:
    st.warning(f"Nenhum registro encontrado para a data {data_filtro.strftime('%d/%m/%Y')} e turno {turno_filtro}.")
    st.info("💡 Dica: Certifique-se de que as metas do dia foram inseridas no banco de dados.")
else:
    # --- Seção de KPIs ---
    total_meta = df_atual['meta'].sum()
    total_realizado = df_atual['realizado'].sum()
    pct_conclusao = (total_realizado / total_meta * 100) if total_meta > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Total Meta Diária", total_meta)
    col2.metric("✅ Total Realizado", total_realizado)
    col3.metric("📊 Conclusão (%)", f"{pct_conclusao:.1f}%")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Seção da Grade Editável ---
    st.subheader("📝 Lançamento Rápido")
    st.write("Altere os valores na coluna **Realizado** e clique em Sincronizar.")

    # Configuração das colunas (Bloqueando o que não pode ser editado)
    configuracao_colunas = {
        "id": None, # Esconde o ID do banco
        "ultima_atualizacao": None, # Esconde a data de atualização
        "data": st.column_config.DateColumn("Data", disabled=True),
        "setor": st.column_config.TextColumn("Setor/Unidade", disabled=True),
        "turno": st.column_config.TextColumn("Turno", disabled=True),
        "tipo": st.column_config.TextColumn("Tipo", disabled=True),
        "meta": st.column_config.NumberColumn("Meta", disabled=True),
        "realizado": st.column_config.NumberColumn(
            "Realizado (Clique para Editar) ✏️", 
            min_value=0, 
            step=1,
            required=True
        )
    }

    # Renderiza a grade
    df_editado = st.data_editor(
        df_atual,
        column_config=configuracao_colunas,
        hide_index=True,
        use_container_width=True,
        key="editor_visitas"
    )

    # --- Botão de Sincronismo ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 4]) # Botão alinhado à esquerda
    
    with col_btn:
        if st.button("🔄 Sincronizar Alterações", type="primary", use_container_width=True):
            with st.spinner("Salvando no Supabase..."):
                qtd_alterada = salvar_alteracoes(df_atual, df_editado)
                
            if qtd_alterada > 0:
                st.success(f"Sucesso! {qtd_alterada} registro(s) atualizado(s) em toda a rede.")
                st.balloons()
            else:
                st.info("Nenhuma alteração foi feita na grade.")