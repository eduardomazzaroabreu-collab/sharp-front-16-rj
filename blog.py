#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHARP - FRONT 16 RJ
Sistema de Busca Global de Notícias
Versão 5.0 - Design Profissional
"""

from flask import Flask, jsonify, send_from_directory
from datetime import datetime, timedelta
import os
import random
import feedparser
from bs4 import BeautifulSoup
import threading
import time
import json
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import logging
from collections import Counter
import hashlib

# Configuração profissional de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================
# CONFIGURAÇÕES AVANÇADAS
# ============================================
ARQUIVO_NOTICIAS = 'noticias_salvas.json'
ARQUIVO_CACHE = 'cache_fontes.json'
ARQUIVO_HISTORICO = 'historico_buscas.json'
TEMPO_ATUALIZACAO = 15  # minutos
TIMEOUT_REQUISICAO = 8  # segundos
MAX_NOTICIAS_POR_FONTE = 4
MAX_NOTICIAS_TOTAL = 800

# ============================================
# SISTEMA DE PROXY INTELIGENTE
# ============================================
class ProxyManager:
    """Gerencia rotação de proxies para evitar bloqueios"""
    
    def __init__(self):
        self.proxies = []
        self.proxy_atual = None
        self.atualizar_lista()
    
    def atualizar_lista(self):
        """Busca proxies públicos atualizados"""
        try:
            # Fontes de proxies gratuitos
            fontes_proxy = [
                'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt'
            ]
            
            for url in fontes_proxy:
                try:
                    resposta = requests.get(url, timeout=5)
                    if resposta.status_code == 200:
                        proxies = resposta.text.strip().split('\n')
                        self.proxies.extend([p.strip() for p in proxies if p.strip()])
                except:
                    continue
            
            # Remove duplicatas
            self.proxies = list(set(self.proxies))
            logger.info(f"✅ {len(self.proxies)} proxies carregados")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar proxies: {e}")
    
    def obter_proxy(self):
        """Retorna um proxy aleatório da lista"""
        if self.proxies:
            proxy = random.choice(self.proxies)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return None

proxy_manager = ProxyManager()

# ============================================
# SISTEMA DE RETRY INTELIGENTE
# ============================================
session = requests.Session()
retry_strategy = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# ============================================
# LISTA DE SITES INTERNACIONAIS
# ============================================
SITES_CONFIAVEIS = [
    # ===== GEOPOLÍTICA & GUERRA =====
    {'nome': 'Al Jazeera', 'pais': 'Qatar', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'BBC News', 'pais': 'UK', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'Reuters', 'pais': 'UK', 'url': 'https://feeds.reuters.com/reuters/topNews', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'The Guardian', 'pais': 'UK', 'url': 'https://www.theguardian.com/world/rss', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'France 24', 'pais': 'França', 'url': 'https://www.france24.com/en/rss', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'Deutsche Welle', 'pais': 'Alemanha', 'url': 'https://rss.dw.com/feeds/rss-english-all', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'Middle East Eye', 'pais': 'UK', 'url': 'https://www.middleeasteye.net/rss', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'Haaretz', 'pais': 'Israel', 'url': 'https://www.haaretz.com/rss', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'The Jerusalem Post', 'pais': 'Israel', 'url': 'https://www.jpost.com/Rss/RssFeeds', 'categoria': 'geopolitica', 'idioma': 'en'},
    {'nome': 'Arab News', 'pais': 'Arábia Saudita', 'url': 'https://www.arabnews.com/rss', 'categoria': 'geopolitica', 'idioma': 'en'},
    
    # ===== ANTIFA, ANARQUISTAS & COMUNISTAS =====
    {'nome': 'Its Going Down', 'pais': 'USA', 'url': 'https://itsgoingdown.org/feed/', 'categoria': 'antifa', 'idioma': 'en'},
    {'nome': 'CrimethInc', 'pais': 'Global', 'url': 'https://crimethinc.com/feeds/all.atom.xml', 'categoria': 'anarquista', 'idioma': 'en'},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria': 'comunista', 'idioma': 'en'},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria': 'comunista', 'idioma': 'en'},
    {'nome': 'The Real News', 'pais': 'USA', 'url': 'https://therealnews.com/rss', 'categoria': 'antifa', 'idioma': 'en'},
    {'nome': 'Democracy Now', 'pais': 'USA', 'url': 'https://www.democracynow.org/podcast.xml', 'categoria': 'antifa', 'idioma': 'en'},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria': 'antifa', 'idioma': 'en'},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria': 'comunista', 'idioma': 'en'},
    {'nome': 'Common Dreams', 'pais': 'USA', 'url': 'https://www.commondreams.org/feed', 'categoria': 'antifa', 'idioma': 'en'},
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria': 'comunista', 'idioma': 'en'},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria': 'antifa', 'idioma': 'en'},
    {'nome': 'Ceasefire Magazine', 'pais': 'UK', 'url': 'https://ceasefiremagazine.co.uk/feed/', 'categoria': 'antifa', 'idioma': 'en'},
    
    # ===== BRASIL & PORTUGAL =====
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria': 'comunista', 'idioma': 'pt'},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria': 'comunista', 'idioma': 'pt'},
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria': 'antifa', 'idioma': 'pt'},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria': 'comunista', 'idioma': 'pt'},
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria': 'comunista', 'idioma': 'pt'},
    
    # ===== AMÉRICA LATINA =====
    {'nome': 'Página 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria': 'antifa', 'idioma': 'es'},
    {'nome': 'La Jornada', 'pais': 'México', 'url': 'https://www.jornada.com.mx/rss', 'categoria': 'antifa', 'idioma': 'es'},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria': 'comunista', 'idioma': 'es'},
]

# ============================================
# FUNÇÕES AUXILIARES
# ============================================
def carregar_cache():
    """Carrega cache de fontes que funcionaram"""
    if os.path.exists(ARQUIVO_CACHE):
        try:
            with open(ARQUIVO_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'funcionaram': []}
    return {'funcionaram': []}

def salvar_cache(cache):
    """Salva cache de fontes que funcionaram"""
    try:
        with open(ARQUIVO_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

def salvar_noticias(noticias):
    """Salva notícias com validação"""
    try:
        with open(ARQUIVO_NOTICIAS, 'w', encoding='utf-8') as f:
            json.dump({
                'noticias': noticias,
                'ultima_atualizacao': datetime.now().isoformat(),
                'total': len(noticias),
                'versao': '5.0'
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Notícias salvas: {len(noticias)}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        return False

def carregar_noticias():
    """Carrega notícias com fallback"""
    if os.path.exists(ARQUIVO_NOTICIAS):
        try:
            with open(ARQUIVO_NOTICIAS, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                return dados.get('noticias', [])
        except:
            return []
    return []

def extrair_resumo(entrada):
    """Extrai resumo de forma segura"""
    try:
        resumo = ""
        if hasattr(entrada, 'summary'):
            resumo = BeautifulSoup(entrada.summary, 'html.parser').get_text()
        elif hasattr(entrada, 'description'):
            resumo = BeautifulSoup(entrada.description, 'html.parser').get_text()
        
        resumo = resumo.strip()
        if len(resumo) > 250:
            resumo = resumo[:250] + "..."
        return resumo or "Leia o artigo completo no site original..."
    except:
        return "Leia o artigo completo no site original..."

# ============================================
# FUNÇÃO PRINCIPAL DE BUSCA
# ============================================
def buscar_noticias():
    """Busca notícias com múltiplas camadas de proteção"""
    
    logger.info(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🌍 Iniciando busca global...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }
    
    cache = carregar_cache()
    noticias_antigas = carregar_noticias()
    links_antigos = {n['link'] for n in noticias_antigas}
    noticias_novas = []
    
    estatisticas = {
        'testadas': 0,
        'geopolitica': 0,
        'antifa': 0,
        'anarquista': 0,
        'comunista': 0,
        'falharam': 0,
        'paises': set(),
        'fontes_ativas': []
    }
    
    logger.info("🔍 Escaneando fontes internacionais...")
    
    # Ordena: primeiro fontes em cache, depois novas
    fontes_para_testar = []
    for nome in cache.get('funcionaram', []):
        for site in SITES_CONFIAVEIS:
            if site['nome'] == nome:
                fontes_para_testar.append(site)
                break
    
    for site in SITES_CONFIAVEIS:
        if site not in fontes_para_testar:
            fontes_para_testar.append(site)
    
    for site in fontes_para_testar:
        estatisticas['testadas'] += 1
        
        # Tenta com proxy se falhar
        for tentativa in range(3):
            try:
                proxy = proxy_manager.obter_proxy() if tentativa > 0 else None
                
                logger.info(f"  → {estatisticas['testadas']:2d}. {site['nome']} ({site['pais']})... ", end="")
                
                resposta = session.get(
                    site['url'], 
                    headers=headers,
                    proxies=proxy,
                    timeout=TIMEOUT_REQUISICAO,
                    allow_redirects=True
                )
                
                if resposta.status_code == 200:
                    feed = feedparser.parse(resposta.content)
                    
                    if len(feed.entries) > 0:
                        logger.info(f"✅ {len(feed.entries)} notícias")
                        
                        # Atualiza estatísticas por categoria
                        if site['categoria'] in estatisticas:
                            estatisticas[site['categoria']] += 1
                        
                        estatisticas['paises'].add(site['pais'])
                        estatisticas['fontes_ativas'].append(site['nome'])
                        
                        for entrada in feed.entries[:MAX_NOTICIAS_POR_FONTE]:
                            if entrada.link not in links_antigos:
                                noticia = {
                                    'id': hashlib.md5(entrada.link.encode()).hexdigest()[:8],
                                    'fonte': site['nome'],
                                    'pais': site['pais'],
                                    'categoria': site['categoria'],
                                    'idioma': site['idioma'],
                                    'titulo': entrada.title,
                                    'resumo': extrair_resumo(entrada),
                                    'link': entrada.link,
                                    'data': entrada.get('published', datetime.now().strftime('%Y-%m-%d %H:%M')),
                                    'publicada_em': datetime.now().isoformat(),
                                    'destaque': False
                                }
                                noticias_novas.append(noticia)
                                logger.info(f"    ✅ {entrada.title[:80]}...")
                        break
                    else:
                        logger.info("❌ Sem notícias")
                        estatisticas['falharam'] += 1
                        break
                else:
                    logger.info(f"❌ Erro {resposta.status_code}")
                    if tentativa == 2:
                        estatisticas['falharam'] += 1
                        
            except Exception as e:
                if tentativa == 2:
                    logger.info("❌ Falhou")
                    estatisticas['falharam'] += 1
                continue
    
    # Atualiza cache
    cache['funcionaram'] = estatisticas['fontes_ativas']
    cache['ultima_atualizacao'] = datetime.now().isoformat()
    salvar_cache(cache)
    
    # Relatório completo
    logger.info(f"\n📊 RELATÓRIO GLOBAL:")
    logger.info(f"  📍 Total testadas: {estatisticas['testadas']}")
    logger.info(f"  ⚔️ Geopolítica: {estatisticas['geopolitica']}")
    logger.info(f"  🏴 Antifa: {estatisticas['antifa']}")
    logger.info(f"  🖤 Anarquista: {estatisticas['anarquista']}")
    logger.info(f"  🔴 Comunista: {estatisticas['comunista']}")
    logger.info(f"  ❌ Falharam: {estatisticas['falharam']}")
    logger.info(f"  🌍 Países: {len(estatisticas['paises'])}")
    
    if noticias_novas:
        todas_noticias = noticias_novas + noticias_antigas
        todas_noticias.sort(key=lambda x: x.get('data', ''), reverse=True)
        todas_noticias = todas_noticias[:MAX_NOTICIAS_TOTAL]
        
        # Marca algumas como destaque
        for i, n in enumerate(todas_noticias[:5]):
            n['destaque'] = True
        
        if salvar_noticias(todas_noticias):
            logger.info(f"  🎯 {len(noticias_novas)} nova(s) notícia(s) de {len(estatisticas['fontes_ativas'])} fontes!")
            logger.info(f"  📊 Acervo total: {len(todas_noticias)}")
    else:
        logger.info("  ℹ️ Nenhuma notícia nova encontrada")
    
    return noticias_novas

# ============================================
# PÁGINA PRINCIPAL - DESIGN PROFISSIONAL
# ============================================
@app.route('/')
def home():
    noticias = carregar_noticias()
    
    # Separa por categoria
    geopolitica = [n for n in noticias if n.get('categoria') == 'geopolitica']
    antifa = [n for n in noticias if n.get('categoria') == 'antifa']
    anarquista = [n for n in noticias if n.get('categoria') == 'anarquista']
    comunista = [n for n in noticias if n.get('categoria') == 'comunista']
    
    # Junta antifa, anarquista e comunista na coluna da esquerda
    esquerda = antifa + anarquista + comunista
    esquerda.sort(key=lambda x: x.get('data', ''), reverse=True)
    
    # Destaques
    destaques = [n for n in noticias if n.get('destaque')][:3]
    
    # Bandeiras dos países
    bandeiras = {
        'USA': '🇺🇸', 'UK': '🇬🇧', 'Brasil': '🇧🇷', 'Portugal': '🇵🇹',
        'Global': '🌍', 'Qatar': '🇶🇦', 'França': '🇫🇷', 'Alemanha': '🇩🇪',
        'Israel': '🇮🇱', 'Arábia Saudita': '🇸🇦', 'Argentina': '🇦🇷',
        'México': '🇲🇽', 'Venezuela': '🇻🇪', 'Espanha': '🇪🇸', 'Itália': '🇮🇹'
    }
    
    # HTML dos destaques
    destaques_html = ''
    for n in destaques:
        bandeira = bandeiras.get(n.get('pais', ''), '🌐')
        destaques_html += f'''
        <div class="destaque-card">
            <span class="destaque-tag">⭐ DESTAQUE</span>
            <span class="fonte">{bandeira} {n['fonte']}</span>
            <h3>{n['titulo']}</h3>
            <p>{n['resumo'][:150]}...</p>
            <div class="card-footer">
                <span class="data">{n['data'][:16]}</span>
                <a href="{n['link']}" target="_blank">Ler mais →</a>
            </div>
        </div>
        '''
    
    # HTML Geopolítica
    geo_html = ''
    for n in geopolitica[:15]:
        bandeira = bandeiras.get(n.get('pais', ''), '🌐')
        geo_html += f'''
        <article class="noticia">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n['fonte']}</span>
                <span class="pais">{n.get('pais', 'Global')}</span>
            </div>
            <h4>{n['titulo']}</h4>
            <p class="resumo">{n['resumo'][:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n['data'][:16]}</span>
                <a href="{n['link']}" target="_blank">🔗</a>
            </div>
        </article>
        '''
    
    # HTML Esquerda (Antifa + Anarquista + Comunista)
    esquerda_html = ''
    for n in esquerda[:15]:
        bandeira = bandeiras.get(n.get('pais', ''), '🌐')
        # Define ícone baseado na categoria
        if n.get('categoria') == 'antifa':
            icone = '🏴'
        elif n.get('categoria') == 'anarquista':
            icone = '🖤'
        else:
            icone = '🔴'
        
        esquerda_html += f'''
        <article class="noticia">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n['fonte']}</span>
                <span class="categoria-badge {n.get('categoria', '')}">{icone} {n.get('categoria', '')}</span>
            </div>
            <h4>{n['titulo']}</h4>
            <p class="resumo">{n['resumo'][:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n['data'][:16]}</span>
                <a href="{n['link']}" target="_blank">🔗</a>
            </div>
        </article>
        '''
    
    # Estatísticas
    total_paises = len(set(n.get('pais', '') for n in noticias))
    total_fontes = len(set(n.get('fonte', '') for n in noticias))
    
    return f'''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Notícias internacionais - Geopolítica, Antifa, Anarquismo e Comunismo">
        <meta name="keywords" content="geopolítica, guerra, antifa, anarquismo, comunismo, notícias">
        <meta name="author" content="SHARP - FRONT 16 RJ">
        <title>🔴 SHARP - FRONT 16 RJ</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0a0a0a;
                color: #e0e0e0;
                line-height: 1.6;
            }}
            
            /* HEADER PROFISSIONAL */
            .header {{
                background: linear-gradient(135deg, #000000 0%, #1a0000 100%);
                border-bottom: 3px solid #ff0000;
                padding: 40px 20px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .header::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,0,0,0.1) 0%, transparent 70%);
                animation: rotate 20s linear infinite;
            }}
            
            @keyframes rotate {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            
            h1 {{
                color: #ff0000;
                font-size: clamp(2rem, 6vw, 3.5rem);
                font-weight: 800;
                letter-spacing: 4px;
                margin-bottom: 10px;
                text-transform: uppercase;
                text-shadow: 0 0 20px rgba(255,0,0,0.5);
                position: relative;
                z-index: 1;
            }}
            
            .subtitulo {{
                color: #aaa;
                font-size: 1.2rem;
                margin-bottom: 30px;
                position: relative;
                z-index: 1;
            }}
            
            /* STATS BAR */
            .stats-bar {{
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
                margin: 30px 0;
                position: relative;
                z-index: 1;
            }}
            
            .stat-item {{
                background: rgba(255,0,0,0.1);
                backdrop-filter: blur(10px);
                border: 1px solid #ff0000;
                padding: 10px 25px;
                border-radius: 40px;
                font-size: 0.95rem;
                transition: all 0.3s;
            }}
            
            .stat-item:hover {{
                background: #ff0000;
                color: #000;
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(255,0,0,0.3);
            }}
            
            /* DESTAQUES */
            .destaques {{
                max-width: 1400px;
                margin: 40px auto;
                padding: 0 20px;
            }}
            
            .destaques h2 {{
                color: #ff0000;
                font-size: 2rem;
                margin-bottom: 30px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .destaques-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 30px;
            }}
            
            .destaque-card {{
                background: linear-gradient(145deg, #111 0%, #1a1a1a 100%);
                border-radius: 20px;
                padding: 30px;
                position: relative;
                border: 1px solid #333;
                transition: all 0.3s;
                overflow: hidden;
            }}
            
            .destaque-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #ff0000, transparent);
            }}
            
            .destaque-card:hover {{
                transform: translateY(-5px);
                border-color: #ff0000;
                box-shadow: 0 10px 30px rgba(255,0,0,0.2);
            }}
            
            .destaque-tag {{
                background: #ff0000;
                color: #000;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 15px;
            }}
            
            /* CONTAINER PRINCIPAL */
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
            }}
            
            /* COLUNAS */
            .coluna {{
                background: rgba(17, 17, 17, 0.5);
                backdrop-filter: blur(10px);
                border-radius: 30px;
                padding: 30px;
                border: 1px solid #333;
            }}
            
            .coluna h2 {{
                color: #ff0000;
                font-size: 2rem;
                margin-bottom: 25px;
                display: flex;
                align-items: center;
                gap: 10px;
                padding-bottom: 15px;
                border-bottom: 2px solid #ff0000;
            }}
            
            .coluna.geopolitica h2 {{
                border-bottom-color: #ff0000;
            }}
            
            .coluna.esquerda h2 {{
                border-bottom-color: #ff0000;
            }}
            
            /* NOTÍCIAS */
            .noticia {{
                background: #111;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                border-left: 4px solid #ff0000;
                transition: all 0.3s;
                position: relative;
            }}
            
            .noticia:hover {{
                transform: translateX(5px);
                background: #1a1a1a;
                border-left-width: 6px;
            }}
            
            .noticia-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                font-size: 0.9rem;
                flex-wrap: wrap;
                gap: 10px;
            }}
            
            .fonte {{
                color: #ff0000;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .pais {{
                color: #888;
                background: #1a1a1a;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
            }}
            
            .categoria-badge {{
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
            
            .categoria-badge.antifa {{
                background: #4a0000;
                color: #ff9999;
            }}
            
            .categoria-badge.anarquista {{
                background: #2a2a2a;
                color: #cccccc;
            }}
            
            .categoria-badge.comunista {{
                background: #8b0000;
                color: #ffb3b3;
            }}
            
            h4 {{
                font-size: 1.1rem;
                margin-bottom: 12px;
                line-height: 1.5;
                color: #fff;
            }}
            
            .resumo {{
                color: #aaa;
                font-size: 0.95rem;
                margin-bottom: 15px;
                line-height: 1.6;
            }}
            
            .noticia-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 15px;
                margin-top: 15px;
            }}
            
            .data {{
                color: #666;
                font-size: 0.8rem;
            }}
            
            a {{
                color: #ff0000;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s;
                padding: 5px 10px;
                border-radius: 5px;
            }}
            
            a:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            /* MENSAGEM VAZIA */
            .mensagem-vazia {{
                text-align: center;
                padding: 60px 20px;
                color: #666;
                font-style: italic;
                background: #111;
                border-radius: 15px;
                border: 1px dashed #333;
            }}
            
            .loader {{
                width: 48px;
                height: 48px;
                border: 3px solid #333;
                border-bottom-color: #ff0000;
                border-radius: 50%;
                display: inline-block;
                animation: rotation 1s linear infinite;
                margin: 20px auto;
            }}
            
            @keyframes rotation {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            /* FOOTER */
            .footer {{
                background: #000;
                border-top: 3px solid #ff0000;
                padding: 50px 20px 30px;
                margin-top: 60px;
                text-align: center;
            }}
            
            .footer-stats {{
                display: flex;
                justify-content: center;
                gap: 30px;
                flex-wrap: wrap;
                margin-bottom: 30px;
                color: #888;
            }}
            
            .footer-links {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }}
            
            .footer-links a {{
                color: #666;
                font-size: 0.9rem;
                padding: 5px 15px;
                border: 1px solid #333;
                border-radius: 30px;
            }}
            
            .footer-links a:hover {{
                background: #ff0000;
                color: #000;
                border-color: #ff0000;
            }}
            
            .agradecimento {{
                max-width: 600px;
                margin: 40px auto;
                padding: 30px;
                background: linear-gradient(145deg, #111, #1a1a1a);
                border-radius: 20px;
                border: 1px solid #333;
            }}
            
            .agradecimento p {{
                color: #ccc;
                font-style: italic;
                line-height: 1.8;
            }}
            
            .assinatura {{
                color: #ff0000;
                font-weight: bold;
                margin-top: 20px;
                font-size: 1.1rem;
            }}
            
            /* RESPONSIVO */
            @media (max-width: 900px) {{
                .container {{
                    grid-template-columns: 1fr;
                }}
                
                .destaques-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            @media (max-width: 600px) {{
                .stats-bar {{
                    flex-direction: column;
                    align-items: center;
                }}
                
                .stat-item {{
                    width: 100%;
                    text-align: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔴 SHARP - FRONT 16 RJ</h1>
            <p class="subtitulo">📰 INFORMAÇÃO PRECIOSA PARA TODOS • GEOPOLÍTICA & MOVIMENTOS SOCIAIS</p>
            
            <div class="stats-bar">
                <span class="stat-item">📰 {len(noticias)} notícias</span>
                <span class="stat-item">🌍 {total_paises} países</span>
                <span class="stat-item">📡 {total_fontes} fontes</span>
                <span class="stat-item">⚔️ {len(geopolitica)} conflitos</span>
                <span class="stat-item">🏴 {len(antifa)} antifa</span>
                <span class="stat-item">🖤 {len(anarquista)} anarquista</span>
                <span class="stat-item">🔴 {len(comunista)} comunista</span>
            </div>
        </div>
        
        <!-- DESTAQUES -->
        <div class="destaques">
            <h2>⭐ DESTAQUES DO DIA</h2>
            <div class="destaques-grid">
                {destaques_html if destaques_html else '<div class="mensagem-vazia">🔍 Buscando destaques...</div>'}
            </div>
        </div>
        
        <!-- COLUNAS PRINCIPAIS -->
        <div class="container">
            <!-- COLUNA GEOPOLÍTICA -->
            <div class="coluna geopolitica">
                <h2>⚔️ GEOPOLÍTICA & GUERRA</h2>
                {geo_html if geo_html else '<div class="mensagem-vazia">🔍 Buscando notícias de geopolítica...</div>'}
            </div>
            
            <!-- COLUNA ESQUERDA (ANTIFA + ANARQUISTA + COMUNISTA) -->
            <div class="coluna esquerda">
                <h2>🏴 MOVIMENTOS SOCIAIS</h2>
                {esquerda_html if esquerda_html else '<div class="mensagem-vazia">🔍 Buscando notícias de movimentos sociais...</div>'}
            </div>
        </div>
        
        <!-- ESPAÇO PARA IMAGEM -->
        <div style="text-align: center; margin: 50px auto; max-width: 1200px;">
            <div style="background: linear-gradient(145deg, #111, #1a1a1a); border-radius: 30px; padding: 40px; border: 1px solid #333;">
                <h3 style="color: #ff0000; margin-bottom: 20px;">📸 ESPAÇO RESERVADO PARA IMAGEM</h3>
                <div style="background: #0a0a0a; height: 300px; border-radius: 20px; display: flex; align-items: center; justify-content: center; border: 2px dashed #333;">
                    <p style="color: #666;">Aqui será inserida uma imagem representativa</p>
                </div>
            </div>
        </div>
        
        <!-- AGRADECIMENTO -->
        <div class="agradecimento">
            <p style="font-size: 1.2rem;">"A informação é a arma mais poderosa contra a ignorância. Agradecemos a todos que lutam por um mundo mais justo, igualitário e livre. A verdade não tem lado - ela apenas é."</p>
            <div class="assinatura">✊ SHARP - FRONT 16 RJ</div>
            <p style="margin-top: 20px; color: #666;">"Enquanto houver opressão, haverá resistência."</p>
        </div>
        
        <!-- FOOTER -->
        <div class="footer">
            <div class="footer-stats">
                <span>📡 Atualização a cada {TEMPO_ATUALIZACAO} minutos</span>
                <span>🔗 Links originais preservados</span>
                <span>⚡ {len(geopolitica) + len(esquerda)} notícias no acervo</span>
            </div>
            
            <div class="footer-links">
                <a href="#">Sobre</a>
                <a href="#">Fontes</a>
                <a href="#">Contato</a>
                <a href="#">Privacidade</a>
            </div>
            
            <p style="color: #444; font-size: 0.8rem; max-width: 800px; margin: 0 auto;">
                🔴 SHARP - FRONT 16 RJ • Notícias Internacionais • Geopolítica, Antifa, Anarquismo e Comunismo
            </p>
            <p style="color: #333; font-size: 0.7rem; margin-top: 20px;">
                Todos os links são das fontes originais • Conteúdo sob responsabilidade de cada veículo
            </p>
            <p style="color: #222; font-size: 0.6rem; margin-top: 10px;">
                v5.0 • Busca via satélite informacional
            </p>
        </div>
    </body>
    </html>
    '''

# ============================================
# ROTA PARA IMAGENS (quando adicionar)
# ============================================
@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

# ============================================
# API DE ESTATÍSTICAS
# ============================================
@app.route('/api/stats')
def api_stats():
    noticias = carregar_noticias()
    geopolitica = [n for n in noticias if n.get('categoria') == 'geopolitica']
    antifa = [n for n in noticias if n.get('categoria') == 'antifa']
    anarquista = [n for n in noticias if n.get('categoria') == 'anarquista']
    comunista = [n for n in noticias if n.get('categoria') == 'comunista']
    
    return jsonify({
        'total': len(noticias),
        'geopolitica': len(geopolitica),
        'antifa': len(antifa),
        'anarquista': len(anarquista),
        'comunista': len(comunista),
        'paises': len(set(n.get('pais', '') for n in noticias)),
        'fontes': len(set(n.get('fonte', '') for n in noticias)),
        'ultima_atualizacao': datetime.now().isoformat()
    })

# ============================================
# INICIALIZAÇÃO
# ============================================
def inicializar():
    """Inicializa o sistema"""
    cache = carregar_cache()
    noticias = carregar_noticias()
    logger.info(f"📊 Acervo inicial: {len(noticias)} notícias")
    
    # Busca inicial em background
    def busca_background():
        time.sleep(5)
        logger.info("🚀 Iniciando busca automática...")
        try:
            buscar_noticias()
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
    
    thread = threading.Thread(target=busca_background, daemon=True)
    thread.start()
    logger.info("✅ Sistema de busca via satélite ativo")
    logger.info("🌍 Modo: Busca global com proxy inteligente")

inicializar()

# ============================================
# FIM - NÃO COLOQUE app.run() AQUI!
# ============================================
# ============================================
# ROTA PARA FORÇAR BUSCA (USE ISSO PARA TESTAR)
# ============================================
@app.route('/forcar-busca')
def forcar_busca():
    import threading
    def busca_forcada():
        buscar_noticias()
    threading.Thread(target=busca_forcada).start()
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔴 Busca Iniciada</title>
        <style>
            body { background: black; color: white; font-family: Arial; text-align: center; padding: 50px; }
            h1 { color: red; }
            .info { background: #111; padding: 20px; border-radius: 10px; margin: 20px; }
        </style>
    </head>
    <body>
        <h1>🔴 SHARP - FRONT 16 RJ</h1>
        <div class="info">
            <h2>🚀 BUSCA INICIADA!</h2>
            <p>As notícias estão sendo coletadas agora.</p>
            <p>Volte para a página inicial e aguarde 1-2 minutos.</p>
            <p><a href="/" style="color: red;">⬅️ Voltar para o site</a></p>
        </div>
    </body>
    </html>
    """

# ============================================
# FIM - NÃO COLOQUE app.run() AQUI!
# ============================================
