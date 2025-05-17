# IMPORTANTE: Este é um aplicativo Streamlit.
# Para executá-lo, certifique-se de que seu ambiente tenha as bibliotecas listadas
# no requirements.txt (sem dependências R).
# Execute no terminal:
#   streamlit run nome_do_seu_arquivo.py

import streamlit as st
import pandas as pd
import geopandas # Para manipulação de dados geoespaciais
import folium # Para criar mapas interativos
from streamlit_folium import st_folium # Para integrar Folium com Streamlit
import numpy as np
# Não precisamos mais importar 'geobr' aqui se os dados são locais

# Configuração da página do Streamlit
st.set_page_config(layout="wide", page_title="Painel IDEB Brasil")

@st.cache_data # Cache para otimizar o carregamento de dados
def carregar_dados_ideb(caminho_arquivo):
    """
    Carrega e limpa os dados do IDEB de um arquivo TXT delimitado por tabulação.
    (Esta função permanece a mesma)
    """
    try:
        try:
            df = pd.read_csv(caminho_arquivo, sep='\t', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(caminho_arquivo, sep='\t', encoding='latin-1', low_memory=False)

        colunas_necessarias = ['UF', 'cod_mun', 'nome_mun', 'ideb', 'nota_matem', 'nota_portugues']
        for col in colunas_necessarias:
            if col not in df.columns:
                st.error(f"Coluna essencial '{col}' não encontrada no arquivo '{caminho_arquivo}'. Verifique o conteúdo do arquivo.")
                return None
        
        df = df[colunas_necessarias].copy()
        cols_numericas = ['ideb', 'nota_matem', 'nota_portugues']
        for col in cols_numericas:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(subset=['ideb'], inplace=True)
        df = df[df['ideb'] != 0].copy()
        df['cod_mun'] = pd.to_numeric(df['cod_mun'], errors='coerce').astype('Int64')
        df.dropna(subset=['cod_mun'], inplace=True)
        return df
    except FileNotFoundError:
        st.error(f"Arquivo '{caminho_arquivo}' não encontrado. Certifique-se de que ele está no mesmo diretório que o script Python ou que o caminho está correto.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados do IDEB: {e}")
        return None

@st.cache_data # Cache para otimizar o carregamento de dados geoespaciais
def carregar_dados_geoespaciais_locais():
    """
    Carrega os dados geoespaciais de municípios e estados do Brasil
    a partir de arquivos GeoJSON locais (previamente baixados e incluídos no repositório).
    ATUALIZADO PARA USAR ARQUIVOS DE 2020.
    """
    # Caminhos para os arquivos GeoJSON DENTRO do seu repositório
    path_municipios = "mapa_ideb_2021/dados_geoespaciais/municipios_br_2020.geojson" # ATUALIZADO para 2020
    path_estados = "mapa_ideb_2021/dados_geoespaciais/estados_br_2020.geojson"     # ATUALIZADO para 2020

    try:
        st.write("Carregando dados geoespaciais dos municípios (local, ano 2020)...") # Mensagem atualizada
        br_muni_gdf = geopandas.read_file(path_municipios)
        
        st.write("Carregando dados geoespaciais dos estados (local, ano 2020)...") # Mensagem atualizada
        br_estados_gdf = geopandas.read_file(path_estados)

        # Verificações e conversões de tipo
        if 'code_muni' in br_muni_gdf.columns:
            br_muni_gdf['code_muni'] = br_muni_gdf['code_muni'].astype('Int64')
        else:
            st.error(f"Coluna 'code_muni' não encontrada no arquivo local: {path_municipios}")
            return None, None

        if 'abbrev_state' not in br_estados_gdf.columns:
             st.error(f"Coluna 'abbrev_state' não encontrada no arquivo local: {path_estados}")
             return None, None

        st.write("Dados geoespaciais locais (2020) carregados com sucesso.") # Mensagem atualizada
        return br_muni_gdf, br_estados_gdf
        
    except FileNotFoundError:
        st.error(f"Erro: Um ou ambos os arquivos GeoJSON de 2020 não foram encontrados. Verifique os caminhos:") # Mensagem atualizada
        st.error(f"- Municípios: {path_municipios}")
        st.error(f"- Estados: {path_estados}")
        st.error("Certifique-se de que a pasta 'dados_geoespaciais' com os arquivos .geojson de 2020 está na raiz do seu repositório GitHub.")
        return None, None
    except Exception as e:
        st.error(f"Erro ao carregar dados geoespaciais locais (2020): {e}") # Mensagem atualizada
        return None, None


def criar_mapa_folium(gdf_mapa, coluna_valor, legenda_titulo, estado_coords_centro):
    """
    Cria um mapa Choropleth (mapa temático de áreas) com Folium.
    (Esta função permanece a mesma)
    """
    if gdf_mapa is None or gdf_mapa.empty or coluna_valor not in gdf_mapa.columns:
        st.warning(f"Não há dados geográficos ou a coluna '{coluna_valor}' não existe para exibir no mapa de {legenda_titulo}.")
        return None

    gdf_mapa_filtrado = gdf_mapa.dropna(subset=[coluna_valor])
    if gdf_mapa_filtrado.empty:
        st.warning(f"Não há dados válidos para exibir no mapa de {legenda_titulo} após remover valores ausentes (NaNs).")
        return None

    mapa = folium.Map(location=[estado_coords_centro.y, estado_coords_centro.x], zoom_start=6, tiles="CartoDB positron")

    min_val = gdf_mapa_filtrado[coluna_valor].min()
    max_val = gdf_mapa_filtrado[coluna_valor].max()
    
    bins_mapa = None 
    cor_preenchimento = 'YlGnBu'

    if not (pd.isna(min_val) or pd.isna(max_val) or min_val == max_val):
        try:
            n_cores = 6
            bins_mapa_tentativa = list(gdf_mapa_filtrado[coluna_valor].quantile([i/n_cores for i in range(n_cores + 1)]))
            bins_mapa_tentativa = sorted(list(set(bins_mapa_tentativa)))
            if len(bins_mapa_tentativa) >= 2:
                bins_mapa = bins_mapa_tentativa
            else:
                bins_mapa = np.linspace(min_val, max_val, n_cores + 1).tolist()
            if len(bins_mapa) < 2:
                 bins_mapa = [min_val, max_val] if min_val != max_val else [min_val, min_val + 0.1]
        except Exception:
            bins_mapa = [min_val, max_val] if min_val != max_val else [min_val, min_val + 0.1]
            st.info(f"Não foi possível gerar uma escala de cores dinâmica para {legenda_titulo}. Usando escala simples.")
    else:
        st.info(f"Variação de dados insuficiente ou valores ausentes para {legenda_titulo}. Usando cor padrão ou escala simples.")
        if not (pd.isna(min_val) or pd.isna(max_val)):
            bins_mapa = [min_val, max_val] if min_val != max_val else [min_val, min_val + 0.1]

    choropleth_layer = folium.Choropleth(
        geo_data=gdf_mapa_filtrado.__geo_interface__,
        name='Choropleth',
        data=gdf_mapa_filtrado,
        columns=['code_muni', coluna_valor],
        key_on='feature.properties.code_muni',
        fill_color=cor_preenchimento,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=legenda_titulo,
        bins=bins_mapa,
        highlight=True
    ).add_to(mapa)

    folium.GeoJsonTooltip(
        fields=['name_muni', coluna_valor],
        aliases=['Município:', legenda_titulo + ':'],
        localize=True, sticky=False, labels=True,
        style="background-color: #F0EFEF; border: 2px solid black; border-radius: 3px; box-shadow: 3px;",
        max_width=800,
    ).add_to(choropleth_layer.geojson)
    
    return mapa

# --- Interface Principal do Streamlit ---
st.title("Painel IDEB Brasil (Dados Geo Locais - Ano 2020)") # Título atualizado

# Carregamento dos dados
# Certifique-se de que 'ideb_escola_2021.txt' está na raiz do repositório ou ajuste o caminho
# Os dados do IDEB ainda são de 2021, mas os dados geoespaciais são de 2020.
# Isso pode ou não ser um problema, dependendo da sua análise.
# Se precisar de dados do IDEB de 2020, você precisaria de um arquivo diferente.
df_ideb = carregar_dados_ideb("mapa_ideb_2021/ideb_escola_2021.txt")
br_muni_gdf, br_estados_gdf = carregar_dados_geoespaciais_locais() # Carrega dados geoespaciais locais de 2020

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
            st.warning(f"Não foram encontrados municípios para o estado {estado_selecionado_sigla} nos dados geoespaciais de 2020.")
        elif ideb_estado_df.empty:
            st.warning(f"Não foram encontrados dados do IDEB (2021) para o estado {estado_selecionado_sigla}.")
        else:
            media_mat_df = ideb_estado_df.groupby('cod_mun')['nota_matem'].mean().reset_index().rename(columns={'nota_matem': 'media_mat'})
            media_por_df = ideb_estado_df.groupby('cod_mun')['nota_portugues'].mean().reset_index().rename(columns={'nota_portugues': 'media_por'})
            media_ideb_df = ideb_estado_df.groupby('cod_mun')['ideb'].mean().reset_index().rename(columns={'ideb': 'media_ideb'})
            
            muni_notas_gdf = pd.merge(muni_estado_gdf, media_mat_df, left_on='code_muni', right_on='cod_mun', how='left')
            muni_notas_gdf = pd.merge(muni_notas_gdf, media_por_df, on='cod_mun', how='left')
            muni_notas_gdf = pd.merge(muni_notas_gdf, media_ideb_df, on='cod_mun', how='left')
            
            if 'cod_mun_x' in muni_notas_gdf.columns:
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

