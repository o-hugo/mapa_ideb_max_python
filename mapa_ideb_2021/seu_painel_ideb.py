# %% [markdown]
# IMPORTANTE: Este é um aplicativo Streamlit.
#  Para executá-lo, siga as instruções no arquivo environment.yml para criar o ambiente Conda.
#  Este ambiente deve incluir R, o pacote geobr do R, rpy2, e o pacote Python 'geobr' (instalado via pip).
#  Depois de ativar o ambiente, execute no terminal:
#    streamlit run nome_do_seu_arquivo.py

# %%

import streamlit as st
import pandas as pd
import geopandas # Para manipulação de dados geoespaciais
import folium # Para criar mapas interativos
from streamlit_folium import st_folium # Para integrar Folium com Streamlit
import numpy as np
import geobr # Wrapper Python para a biblioteca geobr do R

# %%

# Configuração da página do Streamlit
st.set_page_config(layout="wide", page_title="Painel IDEB Brasil")

# %% [markdown]
# funcoes de substituicao

# %%

@st.cache_data # Cache para otimizar o carregamento de dados
def carregar_dados_ideb(caminho_arquivo):
    """
    Carrega e limpa os dados do IDEB de um arquivo TXT delimitado por tabulação.
    """
    try:
        # Tenta ler com encoding utf-8, se falhar, tenta latin-1 (comum em arquivos brasileiros)
        try:
            df = pd.read_csv(caminho_arquivo, sep='\t', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(caminho_arquivo, sep='\t', encoding='latin-1', low_memory=False)

        # Define as colunas que são realmente necessárias para o painel
        colunas_necessarias = ['UF', 'cod_mun', 'nome_mun', 'ideb', 'nota_matem', 'nota_portugues']
        
        # Verifica se todas as colunas necessárias existem no arquivo carregado
        for col in colunas_necessarias:
            if col not in df.columns:
                st.error(f"Coluna essencial '{col}' não encontrada no arquivo '{caminho_arquivo}'. Verifique o conteúdo do arquivo.")
                return None
        
        df = df[colunas_necessarias].copy() # Usar .copy() para evitar SettingWithCopyWarning

        # Converte colunas de notas para tipo numérico.
        # Erros na conversão (ex: texto em campo de nota) se tornarão NaN (Not a Number).
        cols_numericas = ['ideb', 'nota_matem', 'nota_portugues']
        for col in cols_numericas:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Limpeza dos dados:
        # Remove linhas onde 'ideb' é NaN (após conversão) ou explicitamente 0.
        df.dropna(subset=['ideb'], inplace=True)
        df = df[df['ideb'] != 0].copy() # Usar .copy() após a filtragem
        
        # Converte 'cod_mun' para tipo numérico (inteiro Int64 para suportar NaN se houver)
        # e remove linhas onde 'cod_mun' não pôde ser convertido.
        df['cod_mun'] = pd.to_numeric(df['cod_mun'], errors='coerce').astype('Int64')
        df.dropna(subset=['cod_mun'], inplace=True)

        return df
    except FileNotFoundError:
        st.error(f"Arquivo '{caminho_arquivo}' não encontrado. Certifique-se de que ele está no mesmo diretório que o script Python.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados do IDEB: {e}")
        return None

# %%

@st.cache_data # Cache para otimizar o carregamento de dados geoespaciais
def carregar_dados_geoespaciais_com_python_geobr():
    """
    Carrega os dados geoespaciais de municípios e estados do Brasil
    usando o pacote Python 'geobr', que é um wrapper para o pacote R 'geobr'.
    Este pacote Python deve estar instalado via pip, conforme o environment.yml.
    """
    try:
        st.write("Carregando dados geoespaciais dos municípios via geobr (Python wrapper)...")
        # O pacote geobr (Python) retorna um GeoDataFrame diretamente
        br_muni_gdf = geobr.read_municipality(year=2019, simplified=True)
        
        st.write("Carregando dados geoespaciais dos estados via geobr (Python wrapper)...")
        br_estados_gdf = geobr.read_state(year=2019, simplified=True)

        # Verificações e conversões de tipo
        # A coluna de código do município no geobr é 'code_muni'
        if 'code_muni' in br_muni_gdf.columns:
            br_muni_gdf['code_muni'] = br_muni_gdf['code_muni'].astype('Int64')
        else:
            st.error("Coluna 'code_muni' não encontrada nos dados dos municípios carregados pelo geobr.")
            return None, None # Retorna None se a coluna chave estiver faltando

        if 'abbrev_state' not in br_estados_gdf.columns:
             st.error("Coluna 'abbrev_state' não encontrada nos dados dos estados carregados pelo geobr.")
             return None, None # Retorna None se a coluna chave estiver faltando

        st.write("Dados geoespaciais carregados com sucesso via geobr (Python wrapper).")
        return br_muni_gdf, br_estados_gdf
        
    except Exception as e:
        st.error(f"Erro ao carregar dados geoespaciais com o wrapper Python 'geobr': {e}")
        st.error("Verifique se o R, o pacote 'geobr' do R (r-geobr), rpy2, e o pacote Python 'geobr' (instalado via pip) estão corretamente configurados no ambiente Conda.")
        st.error("Consulte o arquivo environment.yml para as dependências necessárias.")
        return None, None

# %%
def criar_mapa_folium(gdf_mapa, coluna_valor, legenda_titulo, estado_coords_centro):
    """
    Cria um mapa Choropleth (mapa temático de áreas) com Folium.
    """
    # Verifica se há dados válidos para plotar
    if gdf_mapa is None or gdf_mapa.empty or coluna_valor not in gdf_mapa.columns:
        st.warning(f"Não há dados geográficos ou a coluna '{coluna_valor}' não existe para exibir no mapa de {legenda_titulo}.")
        return None

    # Remove linhas com valores NaN na coluna de interesse para evitar problemas com a escala de cores
    gdf_mapa_filtrado = gdf_mapa.dropna(subset=[coluna_valor])
    if gdf_mapa_filtrado.empty:
        st.warning(f"Não há dados válidos para exibir no mapa de {legenda_titulo} após remover valores ausentes (NaNs).")
        return None

    # Cria o mapa base, centralizado nas coordenadas do estado e com um nível de zoom inicial.
    mapa = folium.Map(location=[estado_coords_centro.y, estado_coords_centro.x], zoom_start=6, tiles="CartoDB positron")

    min_val = gdf_mapa_filtrado[coluna_valor].min()
    max_val = gdf_mapa_filtrado[coluna_valor].max()
    
    bins_mapa = None 
    cor_preenchimento = 'YlGnBu' # Paleta de cores padrão do Folium

    if not (pd.isna(min_val) or pd.isna(max_val) or min_val == max_val):
        try:
            n_cores = 6 # Número de classes de cores desejadas
            # Tenta criar 'bins' usando quantis para melhor distribuição visual.
            bins_mapa_tentativa = list(gdf_mapa_filtrado[coluna_valor].quantile([i/n_cores for i in range(n_cores + 1)]))
            bins_mapa_tentativa = sorted(list(set(bins_mapa_tentativa))) # Remove duplicados e garante a ordem
            
            if len(bins_mapa_tentativa) >= 2: # Se quantis resultarem em pelo menos 2 bins
                bins_mapa = bins_mapa_tentativa
            else: # Fallback para bins lineares se quantis não derem bons resultados
                bins_mapa = np.linspace(min_val, max_val, n_cores + 1).tolist()
            
            if len(bins_mapa) < 2: # Último fallback para garantir que bins_mapa tenha pelo menos 2 elementos
                 bins_mapa = [min_val, max_val] if min_val != max_val else [min_val, min_val + 0.1] # Adiciona pequena variação se min=max

        except Exception: # Se qualquer cálculo de bins falhar
            bins_mapa = [min_val, max_val] if min_val != max_val else [min_val, min_val + 0.1] # Fallback simples
            st.info(f"Não foi possível gerar uma escala de cores dinâmica para {legenda_titulo}. Usando escala simples.")
    else: # Caso não haja variação nos dados ou sejam NaN
        st.info(f"Variação de dados insuficiente ou valores ausentes para {legenda_titulo}. Usando cor padrão ou escala simples.")
        if not (pd.isna(min_val) or pd.isna(max_val)): # Se min_val e max_val são válidos
            bins_mapa = [min_val, max_val] if min_val != max_val else [min_val, min_val + 0.1]


    # Adiciona a camada Choropleth ao mapa
    choropleth_layer = folium.Choropleth(
        geo_data=gdf_mapa_filtrado.__geo_interface__, # Geometrias dos municípios
        name='Choropleth',
        data=gdf_mapa_filtrado, # DataFrame com os dados
        columns=['code_muni', coluna_valor], # Colunas: ID do município e valor a ser plotado
        key_on='feature.properties.code_muni', # Chave no GeoJSON para fazer o join com os dados
        fill_color=cor_preenchimento,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=legenda_titulo,
        bins=bins_mapa, # Intervalos para a legenda e coloração
        highlight=True # Destaca o município ao passar o mouse
    ).add_to(mapa)

    # Adiciona tooltips (informações que aparecem ao passar o mouse sobre um município)
    folium.GeoJsonTooltip(
        fields=['name_muni', coluna_valor], # Campos a serem exibidos no tooltip
        aliases=['Município:', legenda_titulo + ':'], # Rótulos para os campos
        localize=True, # Formata números de acordo com a localidade
        sticky=False, # Tooltip segue o mouse ou fica fixo
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """,
        max_width=800,
    ).add_to(choropleth_layer.geojson)
    
    return mapa

# %%

# --- Interface Principal do Streamlit ---
st.title("Painel IDEB Brasil (Python com wrapper geobr)")

# %%

# Carregamento dos dados (com cache para performance)
df_ideb = carregar_dados_ideb("/home/est/Documentos/GitHub/mapa_ideb_max_python/mapa_ideb_2021/ideb_escola_2021.txt") # Carrega dados do IDEB
br_muni_gdf, br_estados_gdf = carregar_dados_geoespaciais_com_python_geobr() # Carrega dados geoespaciais

# %%

# Prossegue apenas se todos os dados foram carregados com sucesso
if df_ideb is not None and br_muni_gdf is not None and br_estados_gdf is not None:
    
    st.sidebar.header("Filtros")
    lista_estados_sigla = sorted(br_estados_gdf['abbrev_state'].unique())
    default_index_estado = lista_estados_sigla.index('AM') if 'AM' in lista_estados_sigla else 0
    estado_selecionado_sigla = st.sidebar.selectbox(
        "Selecione um Estado:",
        options=lista_estados_sigla,
        index=default_index_estado
    )

    if estado_selecionado_sigla:
        estado_geom_centroide = br_estados_gdf[br_estados_gdf['abbrev_state'] == estado_selecionado_sigla].geometry.iloc[0].centroid
        muni_estado_gdf = br_muni_gdf[br_muni_gdf['abbrev_state'] == estado_selecionado_sigla].copy()
        ideb_estado_df = df_ideb[df_ideb['UF'] == estado_selecionado_sigla].copy()

        if muni_estado_gdf.empty:
            st.warning(f"Não foram encontrados municípios para o estado {estado_selecionado_sigla} nos dados geoespaciais.")
        elif ideb_estado_df.empty:
            st.warning(f"Não foram encontrados dados do IDEB para o estado {estado_selecionado_sigla}.")
        else:
            media_mat_df = ideb_estado_df.groupby('cod_mun')['nota_matem'].mean().reset_index().rename(columns={'nota_matem': 'media_mat'})
            media_por_df = ideb_estado_df.groupby('cod_mun')['nota_portugues'].mean().reset_index().rename(columns={'nota_portugues': 'media_por'})
            media_ideb_df = ideb_estado_df.groupby('cod_mun')['ideb'].mean().reset_index().rename(columns={'ideb': 'media_ideb'})

            # Assegura que code_muni (do GeoDataFrame) e cod_mun (do IDEB) são do mesmo tipo para o merge
            # O geobr retorna code_muni como int64, o IDEB foi convertido para Int64.
            # Para o merge, é mais seguro converter ambos para string temporariamente se houver dúvidas.
            # No entanto, se ambos são Int64 (que suporta NA), deve funcionar.
            # A função carregar_dados_geoespaciais_com_python_geobr já converte code_muni para Int64.
            # A função carregar_dados_ideb já converte cod_mun para Int64.
            
            muni_notas_gdf = pd.merge(muni_estado_gdf, media_mat_df, left_on='code_muni', right_on='cod_mun', how='left')
            muni_notas_gdf = pd.merge(muni_notas_gdf, media_por_df, on='cod_mun', how='left') # Assume cod_mun de media_mat_df
            muni_notas_gdf = pd.merge(muni_notas_gdf, media_ideb_df, on='cod_mun', how='left')
            
            # Limpeza de colunas de merge duplicadas (ex: cod_mun_x, cod_mun_y)
            # Mantém 'code_muni' do GeoDataFrame original e 'cod_mun' das médias se não houver conflito.
            # Se 'cod_mun' foi usado como chave de junção e não é mais necessário, pode ser removido.
            # O importante é que 'code_muni' esteja presente para o Choropleth.
            if 'cod_mun_x' in muni_notas_gdf.columns: # Se o merge criou sufixos
                muni_notas_gdf.drop(columns=[col for col in muni_notas_gdf.columns if '_y' in col], inplace=True, errors='ignore')
                muni_notas_gdf.rename(columns={col: col.replace('_x', '') for col in muni_notas_gdf.columns if '_x' in col}, inplace=True, errors='ignore')


            st.subheader(f"Notas Médias por Município - {estado_selecionado_sigla}")
            tabela_df_display = muni_notas_gdf[['name_muni', 'media_mat', 'media_por', 'media_ideb']].copy()
            tabela_df_display.rename(columns={
                'name_muni': 'Município', 'media_mat': 'Profic. Mat.',
                'media_por': 'Profic. Port.', 'media_ideb': 'IDEB (Média)'
            }, inplace=True)
            tabela_df_display.dropna(subset=['Profic. Mat.', 'Profic. Port.', 'IDEB (Média)'], how='all', inplace=True)
            st.dataframe(tabela_df_display.style.format({
                'Profic. Mat.': '{:.2f}', 'Profic. Port.': '{:.2f}', 'IDEB (Média)': '{:.2f}'
            }), height=400, use_container_width=True)

            st.subheader(f"Mapas de Distribuição das Notas - {estado_selecionado_sigla}")
            col_mapa1, col_mapa2, col_mapa3 = st.columns(3)

            with col_mapa1:
                st.markdown("##### Média de Matemática")
                mapa_mat = criar_mapa_folium(muni_notas_gdf, 'media_mat', 'Média Mat.', estado_geom_centroide)
                if mapa_mat: st_folium(mapa_mat, width=450, height=450)
                else: st.info("Mapa de Matemática não disponível (sem dados válidos).")
            with col_mapa2:
                st.markdown("##### Média de Português")
                mapa_por = criar_mapa_folium(muni_notas_gdf, 'media_por', 'Média Port.', estado_geom_centroide)
                if mapa_por: st_folium(mapa_por, width=450, height=450)
                else: st.info("Mapa de Português não disponível (sem dados válidos).")
            with col_mapa3:
                st.markdown("##### Média do IDEB")
                mapa_ideb_geral = criar_mapa_folium(muni_notas_gdf, 'media_ideb', 'IDEB (Média)', estado_geom_centroide)
                if mapa_ideb_geral: st_folium(mapa_ideb_geral, width=450, height=450)
                else: st.info("Mapa do IDEB não disponível (sem dados válidos).")
else:
    st.error("Não foi possível carregar os dados necessários para exibir o painel. Verifique os arquivos de dados e as mensagens de erro acima.")




