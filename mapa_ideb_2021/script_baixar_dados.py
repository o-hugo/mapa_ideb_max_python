# Script para rodar localmente UMA VEZ para baixar os dados geoespaciais.
# Certifique-se de que seu ambiente Conda com geobr (Python wrapper), R, r-geobr, etc., está ativo.

import geobr # O wrapper Python para a biblioteca geobr do R
import geopandas
import os

def baixar_e_salvar_dados_geo():
    """
    Baixa os dados de municípios e estados do Brasil para o ano de 2021
    e salva como arquivos GeoJSON.
    """
    ano = 2021 # ATUALIZADO PARA 2021
    pasta_dados_geo = "dados_geoespaciais" # Nome da pasta para salvar os arquivos

    # Cria a pasta se não existir
    if not os.path.exists(pasta_dados_geo):
        os.makedirs(pasta_dados_geo)
        print(f"Pasta '{pasta_dados_geo}' criada.")

    try:
        print(f"Baixando dados dos municípios para {ano}...")
        municipios_gdf = geobr.read_municipality(year=ano, simplified=True)
        path_municipios = os.path.join(pasta_dados_geo, f"municipios_br_{ano}.geojson")
        municipios_gdf.to_file(path_municipios, driver="GeoJSON")
        print(f"Dados dos municípios salvos em: {path_municipios}")

        print(f"\nBaixando dados dos estados para {ano}...")
        estados_gdf = geobr.read_state(year=ano, simplified=True)
        path_estados = os.path.join(pasta_dados_geo, f"estados_br_{ano}.geojson")
        estados_gdf.to_file(path_estados, driver="GeoJSON")
        print(f"Dados dos estados salvos em: {path_estados}")

        print("\nProcesso concluído!")
        print(f"Certifique-se de adicionar a pasta '{pasta_dados_geo}' com os arquivos .geojson ao seu repositório GitHub.")
        print(f"Lembre-se também de atualizar os nomes dos arquivos no seu script principal do painel para refletir o ano de {ano}, se necessário.")

    except Exception as e:
        print(f"Ocorreu um erro ao baixar ou salvar os dados geoespaciais: {e}")
        print("Verifique se o ambiente com geobr (Python), R e r-geobr está configurado e ativo.")
        print(f"Verifique também se dados para o ano {ano} estão disponíveis na API do geobr.")


if __name__ == "__main__":
    baixar_e_salvar_dados_geo()
