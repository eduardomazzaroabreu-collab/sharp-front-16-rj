#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHARP - FRONT 16 RJ
SISTEMA DE BUSCA GLOBAL VIA SATÉLITE INFORMACIONAL
Versão 6.0 - RADAR MUNDIAL COM DUAS BOLAS
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
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

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
TIMEOUT_REQUISICAO = 5  # segundos
MAX_NOTICIAS_POR_FONTE = 3
MAX_NOTICIAS_TOTAL = 1000
MAX_TRABALHADORES = 20  # Threads simultâneas

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
            # Múltiplas fontes de proxies
            fontes_proxy = [
                'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt'
            ]
            
            for url in fontes_proxy:
                try:
                    resposta = requests.get(url, timeout=5)
                    if resposta.status_code == 200:
                        proxies = resposta.text.strip().split('\n')
                        self.proxies.extend([p.strip() for p in proxies if p.strip()])
                except:
                    continue
            
            # Remove duplicatas e proxies inválidos
            self.proxies = list(set(self.proxies))
            self.proxies = [p for p in self.proxies if ':' in p]
            
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
# LISTA DE SITES GLOBAIS (VARRE O MUNDO TODO)
# ============================================
SITES_CONFIAVEIS = [
    # ===== ÁFRICA =====
    {'nome': 'News24', 'pais': 'África do Sul', 'url': 'https://www.news24.com/feeds', 'categoria': 'geral', 'idioma': 'en', 'continente': 'África'},
    {'nome': 'Daily Maverick', 'pais': 'África do Sul', 'url': 'https://www.dailymaverick.co.za/feed/', 'categoria': 'geral', 'idioma': 'en', 'continente': 'África'},
    {'nome': 'The East African', 'pais': 'Quênia', 'url': 'https://www.theeastafrican.co.ke/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'África'},
    {'nome': 'Africanews', 'pais': 'Congo', 'url': 'https://www.africanews.com/feed/', 'categoria': 'geral', 'idioma': 'en', 'continente': 'África'},
    
    # ===== AMÉRICA LATINA =====
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria': 'social', 'idioma': 'pt', 'continente': 'América Latina'},
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria': 'social', 'idioma': 'pt', 'continente': 'América Latina'},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria': 'social', 'idioma': 'pt', 'continente': 'América Latina'},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria': 'social', 'idioma': 'pt', 'continente': 'América Latina'},
    {'nome': 'Página 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria': 'geral', 'idioma': 'es', 'continente': 'América Latina'},
    {'nome': 'La Jornada', 'pais': 'México', 'url': 'https://www.jornada.com.mx/rss', 'categoria': 'geral', 'idioma': 'es', 'continente': 'América Latina'},
    {'nome': 'El Tiempo', 'pais': 'Colômbia', 'url': 'https://www.eltiempo.com/rss', 'categoria': 'geral', 'idioma': 'es', 'continente': 'América Latina'},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria': 'social', 'idioma': 'es', 'continente': 'América Latina'},
    {'nome': 'Clarín', 'pais': 'Argentina', 'url': 'https://www.clarin.com/rss', 'categoria': 'geral', 'idioma': 'es', 'continente': 'América Latina'},
    {'nome': 'El Universal', 'pais': 'México', 'url': 'https://www.eluniversal.com.mx/rss', 'categoria': 'geral', 'idioma': 'es', 'continente': 'América Latina'},
    {'nome': 'O Globo', 'pais': 'Brasil', 'url': 'https://oglobo.globo.com/rss.xml', 'categoria': 'geral', 'idioma': 'pt', 'continente': 'América Latina'},
    {'nome': 'Folha de S.Paulo', 'pais': 'Brasil', 'url': 'https://feeds.folha.uol.com.br/emcimadahora/rss.xml', 'categoria': 'geral', 'idioma': 'pt', 'continente': 'América Latina'},
    
    # ===== EUROPA =====
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria': 'social', 'idioma': 'pt', 'continente': 'Europa'},
    {'nome': 'Deutsche Welle', 'pais': 'Alemanha', 'url': 'https://rss.dw.com/feeds/rss-english-all', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'France 24', 'pais': 'França', 'url': 'https://www.france24.com/en/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'The Guardian', 'pais': 'UK', 'url': 'https://www.theguardian.com/world/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria': 'social', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria': 'social', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'Ceasefire Magazine', 'pais': 'UK', 'url': 'https://ceasefiremagazine.co.uk/feed/', 'categoria': 'social', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'Le Monde', 'pais': 'França', 'url': 'https://www.lemonde.fr/rss/une.xml', 'categoria': 'geral', 'idioma': 'fr', 'continente': 'Europa'},
    {'nome': 'El País', 'pais': 'Espanha', 'url': 'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada', 'categoria': 'geral', 'idioma': 'es', 'continente': 'Europa'},
    {'nome': 'La Repubblica', 'pais': 'Itália', 'url': 'https://www.repubblica.it/rss', 'categoria': 'geral', 'idioma': 'it', 'continente': 'Europa'},
    {'nome': 'Corriere della Sera', 'pais': 'Itália', 'url': 'https://www.corriere.it/rss', 'categoria': 'geral', 'idioma': 'it', 'continente': 'Europa'},
    {'nome': 'Der Spiegel', 'pais': 'Alemanha', 'url': 'https://www.spiegel.de/international/index.rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'Die Welt', 'pais': 'Alemanha', 'url': 'https://www.welt.de/feeds/english.rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'BBC News', 'pais': 'UK', 'url': 'http://feeds.bbci.co.uk/news/rss.xml', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'Reuters', 'pais': 'UK', 'url': 'https://feeds.reuters.com/reuters/topNews', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'The Independent', 'pais': 'UK', 'url': 'https://www.independent.co.uk/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Europa'},
    {'nome': 'EUobserver', 'pais': 'Bélgica', 'url': 'https://euobserver.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Europa'},
    
    # ===== ORIENTE MÉDIO =====
    {'nome': 'Al Jazeera', 'pais': 'Qatar', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    {'nome': 'Middle East Eye', 'pais': 'UK', 'url': 'https://www.middleeasteye.net/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    {'nome': 'Haaretz', 'pais': 'Israel', 'url': 'https://www.haaretz.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    {'nome': 'The Jerusalem Post', 'pais': 'Israel', 'url': 'https://www.jpost.com/Rss/RssFeeds', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    {'nome': 'Arab News', 'pais': 'Arábia Saudita', 'url': 'https://www.arabnews.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    {'nome': 'Gulf News', 'pais': 'Emirados', 'url': 'https://gulfnews.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    {'nome': 'Iran International', 'pais': 'Irã', 'url': 'https://www.iranintl.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Médio'},
    
    # ===== ÁSIA =====
    {'nome': 'The Hindu', 'pais': 'Índia', 'url': 'https://www.thehindu.com/news/feeder', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'Times of India', 'pais': 'Índia', 'url': 'https://timesofindia.indiatimes.com/rss.cms', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'The Japan Times', 'pais': 'Japão', 'url': 'https://www.japantimes.co.jp/feed/', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'China Daily', 'pais': 'China', 'url': 'https://www.chinadaily.com.cn/rss/', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'The Korea Herald', 'pais': 'Coreia do Sul', 'url': 'http://www.koreaherald.com/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'The Straits Times', 'pais': 'Singapura', 'url': 'https://www.straitstimes.com/news/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'South China Morning Post', 'pais': 'Hong Kong', 'url': 'https://www.scmp.com/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'Nikkei Asia', 'pais': 'Japão', 'url': 'https://asia.nikkei.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Ásia'},
    
    # ===== OCEANIA =====
    {'nome': 'ABC News', 'pais': 'Austrália', 'url': 'https://www.abc.net.au/news/feed', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Oceania'},
    {'nome': 'The Sydney Morning Herald', 'pais': 'Austrália', 'url': 'https://www.smh.com.au/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Oceania'},
    {'nome': 'The Age', 'pais': 'Austrália', 'url': 'https://www.theage.com.au/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Oceania'},
    {'nome': 'RNZ', 'pais': 'Nova Zelândia', 'url': 'https://www.rnz.co.nz/rss', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Oceania'},
    
    # ===== INTERNACIONAIS =====
    {'nome': 'Democracy Now', 'pais': 'USA', 'url': 'https://www.democracynow.org/podcast.xml', 'categoria': 'social', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria': 'social', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria': 'social', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria': 'social', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'Common Dreams', 'pais': 'USA', 'url': 'https://www.commondreams.org/feed', 'categoria': 'social', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria': 'social', 'idioma': 'en', 'continente': 'Global'},
    
    # ===== GEOPOLÍTICA =====
    {'nome': 'Foreign Policy', 'pais': 'USA', 'url': 'https://foreignpolicy.com/feed/', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'The Diplomat', 'pais': 'Japão', 'url': 'https://thediplomat.com/feed/', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Ásia'},
    {'nome': 'War on the Rocks', 'pais': 'USA', 'url': 'https://warontherocks.com/feed/', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'América do Norte'},
    {'nome': 'Stratfor', 'pais': 'USA', 'url': 'https://worldview.stratfor.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'América do Norte'},
]

# ============================================
# SISTEMA DE RADAR GLOBAL (BUSCA PARALELA)
# ============================================
class RadarGlobal:
    """Sistema de busca paralela tipo radar"""
    
    def __init__(self):
        self.fontes_ativas = []
        self.estatisticas = {
            'total_buscas': 0,
            'fontes_funcionando': 0,
            'noticias_encontradas': 0,
            'continentes': set()
        }
    
    def varrer_mundo(self):
        """Executa varredura global em paralelo"""
        logger.info("🛰️ ATIVANDO RADAR GLOBAL...")
        
        resultados = []
        with ThreadPoolExecutor(max_workers=MAX_TRABALHADORES) as executor:
            futures = {executor.submit(self.testar_fonte, site): site for site in SITES_CONFIAVEIS}
            
            for future in as_completed(futures):
                site = futures[future]
                try:
                    resultado = future.result(timeout=TIMEOUT_REQUISICAO)
                    if resultado:
                        resultados.extend(resultado)
                except Exception as e:
                    logger.debug(f"❌ {site['nome']} falhou: {e}")
        
        return resultados
    
    def testar_fonte(self, site):
        """Testa uma fonte individual"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        noticias = []
        try:
            resposta = requests.get(site['url'], headers=headers, timeout=TIMEOUT_REQUISICAO)
            
            if resposta.status_code == 200:
                feed = feedparser.parse(resposta.content)
                
                if len(feed.entries) > 0:
                    logger.info(f"📡 {site['continente']} - {site['pais']}: {site['nome']} ({len(feed.entries)} notícias)")
                    
                    for entrada in feed.entries[:MAX_NOTICIAS_POR_FONTE]:
                        noticia = self.criar_noticia(site, entrada)
                        if noticia:
                            noticias.append(noticia)
                    
                    self.fontes_ativas.append(site['nome'])
                    self.estatisticas['fontes_funcionando'] += 1
                    self.estatisticas['continentes'].add(site['continente'])
        except:
            pass
        
        return noticias
    
    def criar_noticia(self, site, entrada):
        """Cria objeto de notícia"""
        try:
            resumo = ""
            if hasattr(entrada, 'summary'):
                resumo = BeautifulSoup(entrada.summary, 'html.parser').get_text()
            elif hasattr(entrada, 'description'):
                resumo = BeautifulSoup(entrada.description, 'html.parser').get_text()
            
            resumo = resumo[:200] + "..." if resumo and len(resumo) > 200 else resumo or "Leia o artigo completo..."
            
            return {
                'id': hashlib.md5(entrada.link.encode()).hexdigest()[:8],
                'fonte': site['nome'],
                'pais': site['pais'],
                'continente': site['continente'],
                'categoria': site['categoria'],
                'idioma': site['idioma'],
                'titulo': entrada.title,
                'resumo': resumo,
                'link': entrada.link,
                'data': entrada.get('published', datetime.now().strftime('%Y-%m-%d %H:%M')),
                'publicada_em': datetime.now().isoformat(),
                'destaque': False
            }
        except:
            return None

radar = RadarGlobal()

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
                'versao': '6.0 - Radar Global'
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

# ============================================
# FUNÇÃO PRINCIPAL DE BUSCA (RADAR GLOBAL)
# ============================================
def buscar_noticias():
    """Executa varredura global via radar"""
    
    logger.info(f"\n🛰️ [{datetime.now().strftime('%H:%M:%S')}] ATIVANDO RADAR GLOBAL...")
    
    noticias_antigas = carregar_noticias()
    links_antigos = {n['link'] for n in noticias_antigas}
    
    # Varre o mundo em paralelo
    novas_noticias = radar.varrer_mundo()
    
    # Filtra notícias já existentes
    noticias_novas = [n for n in novas_noticias if n['link'] not in links_antigos]
    
    # Relatório do radar
    logger.info(f"\n📊 RELATÓRIO DO RADAR GLOBAL:")
    logger.info(f"  📡 Fontes ativas: {radar.estatisticas['fontes_funcionando']}")
    logger.info(f"  🌍 Continentes cobertos: {len(radar.estatisticas['continentes'])}")
    logger.info(f"  📰 Notícias novas: {len(noticias_novas)}")
    
    if noticias_novas:
        todas_noticias = noticias_novas + noticias_antigas
        todas_noticias.sort(key=lambda x: x.get('data', ''), reverse=True)
        todas_noticias = todas_noticias[:MAX_NOTICIAS_TOTAL]
        
        # Marca algumas como destaque
        for i, n in enumerate(todas_noticias[:5]):
            n['destaque'] = True
        
        if salvar_noticias(todas_noticias):
            logger.info(f"  🎯 {len(noticias_novas)} nova(s) notícia(s) de {radar.estatisticas['fontes_funcionando']} fontes!")
            logger.info(f"  📊 Acervo total: {len(todas_noticias)}")
    else:
        logger.info("  ℹ️ Nenhuma notícia nova encontrada")
    
    return noticias_novas

# ============================================
# PÁGINA PRINCIPAL - DESIGN COM DUAS BOLAS
# ============================================
@app.route('/')
def home():
    noticias = carregar_noticias()
    
    # Separa por categoria
    geopolitica = [n for n in noticias if n.get('categoria') == 'geopolitica']
    social = [n for n in noticias if n.get('categoria') in ['social', 'geral']]
    
    # Destaques
    destaques = [n for n in noticias if n.get('destaque')][:3]
    
    # Estatísticas por continente
    continentes = {}
    for n in noticias:
        cont = n.get('continente', 'Desconhecido')
        continentes[cont] = continentes.get(cont, 0) + 1
    
    # Bandeiras dos países
    bandeiras = {
        'USA': '🇺🇸', 'UK': '🇬🇧', 'Brasil': '🇧🇷', 'Portugal': '🇵🇹',
        'Global': '🌍', 'Qatar': '🇶🇦', 'França': '🇫🇷', 'Alemanha': '🇩🇪',
        'Israel': '🇮🇱', 'Arábia Saudita': '🇸🇦', 'Argentina': '🇦🇷',
        'México': '🇲🇽', 'Venezuela': '🇻🇪', 'Espanha': '🇪🇸', 'Itália': '🇮🇹',
        'África do Sul': '🇿🇦', 'Quênia': '🇰🇪', 'Congo': '🇨🇩', 'Índia': '🇮🇳',
        'Japão': '🇯🇵', 'China': '🇨🇳', 'Coreia do Sul': '🇰🇷', 'Singapura': '🇸🇬',
        'Hong Kong': '🇭🇰', 'Austrália': '🇦🇺', 'Nova Zelândia': '🇳🇿',
        'Bélgica': '🇧🇪', 'Irã': '🇮🇷', 'Emirados': '🇦🇪'
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
    
    # HTML Movimentos Sociais
    social_html = ''
    for n in social[:15]:
        bandeira = bandeiras.get(n.get('pais', ''), '🌐')
        social_html += f'''
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
    
    # HTML do mapa de continentes
    continentes_html = ''
    for cont, qtd in continentes.items():
        continentes_html += f'<span class="contente-badge">{cont}: {qtd}</span>'
    
    return f'''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Notícias internacionais - Radar Global">
        <meta name="keywords" content="geopolítica, movimentos sociais, notícias, radar global">
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
            
            /* HEADER PROFISSIONAL COM DUAS BOLAS */
            .header {{
                background: linear-gradient(135deg, #000000 0%, #1a0000 100%);
                border-bottom: 3px solid #ff0000;
                padding: 40px 20px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .bolas-container {{
                position: absolute;
                top: 20px;
                right: 30px;
                display: flex;
                gap: 15px;
                z-index: 10;
            }}
            
            .bola-vermelha {{
                width: 60px;
                height: 60px;
                background: #ff0000;
                border-radius: 50%;
                box-shadow: 0 0 30px rgba(255,0,0,0.7);
                animation: pulsar-vermelha 2s infinite ease-in-out;
            }}
            
            .bola-preta {{
                width: 60px;
                height: 60px;
                background: #000;
                border-radius: 50%;
                border: 2px solid #ff0000;
                box-shadow: 0 0 30px rgba(255,0,0,0.3);
                animation: pulsar-preta 2.5s infinite ease-in-out;
            }}
            
            @keyframes pulsar-vermelha {{
                0% {{ transform: scale(1); box-shadow: 0 0 30px rgba(255,0,0,0.7); }}
                50% {{ transform: scale(1.1); box-shadow: 0 0 50px rgba(255,0,0,1); }}
                100% {{ transform: scale(1); box-shadow: 0 0 30px rgba(255,0,0,0.7); }}
            }}
            
            @keyframes pulsar-preta {{
                0% {{ transform: scale(1); box-shadow: 0 0 30px rgba(255,0,0,0.3); }}
                50% {{ transform: scale(1.05); box-shadow: 0 0 40px rgba(255,0,0,0.6); }}
                100% {{ transform: scale(1); box-shadow: 0 0 30px rgba(255,0,0,0.3); }}
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
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
            }}
            
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
            
            .mensagem-vazia {{
                text-align: center;
                padding: 60px 20px;
                color: #666;
                font-style: italic;
                background: #111;
                border-radius: 15px;
                border: 1px dashed #333;
            }}
            
            .contente-badge {{
                display: inline-block;
                background: #1a1a1a;
                border: 1px solid #333;
                padding: 5px 15px;
                border-radius: 30px;
                margin: 5px;
                font-size: 0.8rem;
                color: #ff0000;
            }}
            
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
            
            @media (max-width: 900px) {{
                .container {{
                    grid-template-columns: 1fr;
                }}
                
                .destaques-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .bolas-container {{
                    position: relative;
                    top: 0;
                    right: 0;
                    justify-content: center;
                    margin-bottom: 20px;
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
            <div class="bolas-container">
                <div class="bola-vermelha"></div>
                <div class="bola-preta"></div>
            </div>
            
            <h1>🔴 SHARP - FRONT 16 RJ</h1>
            <p class="subtitulo">📰 INFORMAÇÃO PRECIOSA PARA TODOS • GEOPOLÍTICA & MOVIMENTOS SOCIAIS</p>
            
            <div class="stats-bar">
                <span class="stat-item">📰 {len(noticias)} notícias</span>
                <span class="stat-item">🌍 {len(set(n.get('pais', '') for n in noticias))} países</span>
                <span class="stat-item">📡 {len(set(n.get('fonte', '') for n in noticias))} fontes</span>
                <span class="stat-item">⚔️ {len(geopolitica)} geopolitica</span>
                <span class="stat-item">🏴 {len(social)} social</span>
            </div>
            
            <div class="contente-badge-container">
                {continentes_html}
            </div>
        </div>
        
        <!-- DESTAQUES -->
        <div class="destaques">
            <h2>⭐ DESTAQUES DO DIA</h2>
            <div class="destaques-grid">
                {destaques_html if destaques_html else '<div class="mensagem-vazia">🛰️ Radar global em operação... buscando destaques...</div>'}
            </div>
        </div>
        
        <!-- COLUNAS PRINCIPAIS -->
        <div class="container">
            <!-- COLUNA GEOPOLÍTICA -->
            <div class="coluna">
                <h2>⚔️ GEOPOLÍTICA & GUERRA</h2>
                {geo_html if geo_html else '<div class="mensagem-vazia">🛰️ Escaneando conflitos globais...</div>'}
            </div>
            
            <!-- COLUNA MOVIMENTOS SOCIAIS -->
            <div class="coluna">
                <h2>🏴 MOVIMENTOS SOCIAIS</h2>
                {social_html if social_html else '<div class="mensagem-vazia">🛰️ Buscando movimentos sociais...</div>'}
            </div>
        </div>
        
        <!-- ROTA DE TESTE PARA BUSCA -->
        <div style="text-align: center; margin: 30px auto;">
            <a href="/forcar-busca" style="display: inline-block; padding: 10px 30px; background: #ff0000; color: #000; border-radius: 30px; text-decoration: none; font-weight: bold;">🚀 ATIVAR RADAR GLOBAL</a>
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
                <span>⚡ {len(noticias)} notícias no acervo</span>
            </div>
            
            <p style="color: #444; font-size: 0.8rem; max-width: 800px; margin: 0 auto;">
                🔴 SHARP - FRONT 16 RJ • Radar Global de Notícias • Geopolítica & Movimentos Sociais
            </p>
            <p style="color: #333; font-size: 0.7rem; margin-top: 20px;">
                Todos os links são das fontes originais • Conteúdo sob responsabilidade de cada veículo
            </p>
            <p style="color: #222; font-size: 0.6rem; margin-top: 10px;">
                v6.0 • Radar Global com Busca Paralela
            </p>
        </div>
    </body>
    </html>
    '''

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
        <title>🔴 Radar Ativado</title>
        <style>
            body { background: black; color: white; font-family: Arial; text-align: center; padding: 50px; }
            h1 { color: red; }
            .info { background: #111; padding: 20px; border-radius: 10px; margin: 20px; }
        </style>
    </head>
    <body>
        <h1>🔴 SHARP - FRONT 16 RJ</h1>
        <div class="info">
            <h2>🛰️ RADAR GLOBAL ATIVADO!</h2>
            <p>As notícias estão sendo coletadas agora em paralelo.</p>
            <p>Volte para a página inicial e aguarde 1-2 minutos.</p>
            <p><a href="/" style="color: red;">⬅️ Voltar para o site</a></p>
        </div>
    </body>
    </html>
    """

# ============================================
# API DE ESTATÍSTICAS
# ============================================
@app.route('/api/stats')
def api_stats():
    noticias = carregar_noticias()
    geopolitica = [n for n in noticias if n.get('categoria') == 'geopolitica']
    social = [n for n in noticias if n.get('categoria') in ['social', 'geral']]
    
    return jsonify({
        'total': len(noticias),
        'geopolitica': len(geopolitica),
        'social': len(social),
        'paises': len(set(n.get('pais', '') for n in noticias)),
        'continentes': len(set(n.get('continente', '') for n in noticias)),
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
    logger.info("✅ Sistema de radar global ativo")
    logger.info("🌍 Modo: Busca paralela com 20 threads simultâneas")

inicializar()

# ============================================
# FIM - NÃO COLOQUE app.run() AQUI!
# ============================================
