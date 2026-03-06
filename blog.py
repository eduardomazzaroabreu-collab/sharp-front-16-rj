#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🔴🏴 SHARP - FRONT 16 RJ 🏴🔴                          ║
║                 SISTEMA SUPREMO ANTIFA - VERSÃO 9.0                          ║
║         RADAR INFORMACIONAL ANTIFASCISTA GLOBAL MULTILÍNGUE                  ║
║              "A informação é nossa arma mais poderosa"                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from flask import Flask, jsonify, send_from_directory, render_template_string, request
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
from collections import Counter, defaultdict
import hashlib
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import re
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import queue
from urllib.parse import urlparse, quote_plus, urljoin, urlencode
import html
import xml.etree.ElementTree as ET
import gzip
import zlib
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURAÇÕES PROFISSIONAIS AVANÇADAS
# ============================================

class Config:
    """Configurações avançadas do sistema supremo antifa"""
    
    # Identidade
    NOME_SITE = "SHARP - FRONT 16 RJ"
    LEMA = "A informação é nossa arma mais poderosa"
    COR_PRIMARIA = "#ff0000"  # Vermelho
    COR_SECUNDARIA = "#000000"  # Preto
    
    # Arquivos
    ARQUIVO_NOTICIAS = 'noticias_salvas.json'
    ARQUIVO_CACHE = 'cache_fontes.json'
    ARQUIVO_HISTORICO = 'historico_buscas.json'
    ARQUIVO_PALAVRAS = 'palavras_chave.json'
    ARQUIVO_LOG = 'radar_antifa.log'
    
    # Tempos
    TEMPO_ATUALIZACAO = 10  # minutos
    TIMEOUT_REQUISICAO = 8  # segundos
    TIMEOUT_TOTAL = 30  # segundos
    DELAY_ENTRE_REQUISICOES = 0.3  # segundos
    
    # Limites
    MAX_NOTICIAS_POR_FONTE = 5
    MAX_NOTICIAS_TOTAL = 3000
    MAX_TRABALHADORES = 40  # Threads simultâneas
    MAX_TENTATIVAS = 3
    MAX_PALAVRAS_POR_BUSCA = 10
    
    # Headers para parecer navegador real (evita bloqueios)
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7,fr;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

config = Config()

# ============================================
# LOGGING PROFISSIONAL
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - 🔴🏴 %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.ARQUIVO_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ANTIFA-RADAR')

# ============================================
# SISTEMA DE PROXY INTELIGENTE (EVITA BLOQUEIOS)
# ============================================

class ProxyManagerSupremo:
    """Gerencia rotação de proxies para evitar bloqueios"""
    
    def __init__(self):
        self.proxies_http = []
        self.proxies_socks = []
        self.proxies_https = []
        self.proxy_atual = None
        self.blacklist = set()
        self.cache_proxies = {}
        self.atualizar_lista()
    
    def atualizar_lista(self):
        """Busca proxies públicos atualizados de múltiplas fontes"""
        try:
            fontes_proxy = [
                'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
                'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
                'https://raw.githubusercontent.com/themiralay/Proxy-List/master/http.txt',
                'https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt',
                'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
                'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
            ]
            
            for url in fontes_proxy:
                try:
                    response = requests.get(url, timeout=5, headers=config.HEADERS)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        for proxy in proxies:
                            proxy = proxy.strip()
                            if proxy and ':' in proxy and proxy not in self.blacklist:
                                if 'socks' in proxy.lower():
                                    self.proxies_socks.append(proxy)
                                elif 'https' in proxy.lower():
                                    self.proxies_https.append(proxy)
                                else:
                                    self.proxies_http.append(proxy)
                except Exception as e:
                    logger.debug(f"Erro ao carregar proxy de {url}: {e}")
                    continue
            
            # Remove duplicatas
            self.proxies_http = list(set(self.proxies_http))
            self.proxies_https = list(set(self.proxies_https))
            self.proxies_socks = list(set(self.proxies_socks))
            
            logger.info(f"✅🏴 PROXYS CARREGADOS: HTTP={len(self.proxies_http)} HTTPS={len(self.proxies_https)} SOCKS={len(self.proxies_socks)}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar proxies: {e}")
    
    def obter_proxy(self, tipo='http'):
        """Retorna um proxy aleatório da lista"""
        if tipo == 'https' and self.proxies_https:
            proxy = random.choice(self.proxies_https)
            return {tipo: f'http://{proxy}'}
        elif tipo == 'socks' and self.proxies_socks:
            proxy = random.choice(self.proxies_socks)
            return {'http': f'socks5://{proxy}', 'https': f'socks5://{proxy}'}
        elif self.proxies_http:
            proxy = random.choice(self.proxies_http)
            return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        return None
    
    def reportar_falha(self, proxy):
        """Reporta um proxy que falhou"""
        self.blacklist.add(proxy)
        if proxy in self.proxies_http:
            self.proxies_http.remove(proxy)
        elif proxy in self.proxies_https:
            self.proxies_https.remove(proxy)
        elif proxy in self.proxies_socks:
            self.proxies_socks.remove(proxy)

proxy_manager = ProxyManagerSupremo()

# ============================================
# PALAVRAS-CHAVE MULTILÍNGUE (FOCO ANTIFA)
# ============================================

PALAVRAS_CHAVE = {
    # 🇧🇷 PORTUGUÊS (BRASIL)
    'pt': [
        'antifa', 'antifascista', 'fascismo', 'nazismo', 'neonazista',
        'movimento social', 'protesto', 'manifestação', 'greve', 'ocupação',
        'direitos humanos', 'igualdade', 'racismo', 'feminismo', 'lgbtqia+',
        'trabalhador', 'sindicato', 'sem terra', 'mst', 'mtst',
        'comunismo', 'socialismo', 'anarquismo', 'resistência', 'luta',
        'polícia', 'repressão', 'violência estatal', 'prisão política',
        'liberdade', 'democracia', 'justiça social', 'reforma agrária',
        'amazônia', 'indígena', 'quilombola', 'meio ambiente', 'sustentabilidade',
        'governo', 'congresso', 'eleição', 'presidente', 'bolsonaro', 'lula',
        'economia', 'inflação', 'desemprego', 'fome', 'pobreza',
        'educação', 'saúde', 'susp', 'forças armadas', 'intervenção',
        'guerra', 'conflito', 'ataque', 'bomba', 'exercito', 'tropas',
        'genocídio', 'ocupação', 'resistência', 'revolução',
    ],
    
    # 🇺🇸 INGLÊS (INTERNACIONAL)
    'en': [
        'antifa', 'antifascist', 'fascism', 'nazism', 'neonazi',
        'social movement', 'protest', 'demonstration', 'strike', 'occupation',
        'human rights', 'equality', 'racism', 'feminism', 'lgbtqia+',
        'worker', 'union', 'landless', 'indigenous', 'black lives matter',
        'communism', 'socialism', 'anarchism', 'resistance', 'struggle',
        'police', 'repression', 'state violence', 'political prisoner',
        'freedom', 'democracy', 'social justice', 'land reform',
        'climate', 'environment', 'sustainability', 'amazon rainforest',
        'government', 'congress', 'election', 'president', 'trump', 'biden',
        'economy', 'inflation', 'unemployment', 'hunger', 'poverty',
        'education', 'health', 'police brutality', 'military', 'intervention',
        'war', 'conflict', 'attack', 'bomb', 'army', 'troops',
        'genocide', 'occupation', 'resistance', 'revolution',
        'palestine', 'israel', 'gaza', 'ukraine', 'russia', 'syria',
        'climate strike', 'fridays for future', 'extinction rebellion',
    ],
    
    # 🇪🇸 ESPANHOL (AMÉRICA LATINA)
    'es': [
        'antifa', 'antifascista', 'fascismo', 'nazismo', 'neonazi',
        'movimiento social', 'protesta', 'manifestación', 'huelga', 'ocupación',
        'derechos humanos', 'igualdad', 'racismo', 'feminismo', 'lgbtqia+',
        'trabajador', 'sindicato', 'sin tierra', 'indígena', 'mapuche',
        'comunismo', 'socialismo', 'anarquismo', 'resistencia', 'lucha',
        'policía', 'represión', 'violencia estatal', 'preso político',
        'libertad', 'democracia', 'justicia social', 'reforma agraria',
        'amazonía', 'medio ambiente', 'sostenibilidad', 'cambio climático',
        'gobierno', 'congreso', 'elección', 'presidente', 'petro', 'milei',
        'economía', 'inflación', 'desempleo', 'hambre', 'pobreza',
        'educación', 'salud', 'militar', 'intervención',
        'guerra', 'conflicto', 'ataque', 'bomba', 'ejército', 'tropas',
        'genocidio', 'ocupación', 'resistencia', 'revolución',
        'palestina', 'israel', 'gaza', 'ucrania', 'rusia',
    ],
    
    # 🇫🇷 FRANCÊS (ÁFRICA E EUROPA)
    'fr': [
        'antifa', 'antifasciste', 'fascisme', 'nazisme', 'néonazi',
        'mouvement social', 'manifestation', 'grève', 'occupation',
        'droits humains', 'égalité', 'racisme', 'féminisme', 'lgbtqia+',
        'travailleur', 'syndicat', 'sans terre', 'autochtone',
        'communisme', 'socialisme', 'anarchisme', 'résistance', 'lutte',
        'police', 'répression', 'violence d\'état', 'prisonnier politique',
        'liberté', 'démocratie', 'justice sociale', 'réforme agraire',
        'environnement', 'climat', 'développement durable',
        'gouvernement', 'élection', 'président', 'macron',
        'économie', 'inflation', 'chômage', 'faim', 'pauvreté',
        'éducation', 'santé', 'armée', 'intervention',
        'guerre', 'conflit', 'attaque', 'bombe', 'armée', 'troupes',
        'génocide', 'occupation', 'résistance', 'révolution',
    ],
    
    # 🇩🇪 ALEMÃO
    'de': [
        'antifa', 'antifaschist', 'faschismus', 'nazismus', 'neonazi',
        'soziale bewegung', 'protest', 'demonstration', 'streik', 'besetzung',
        'menschenrechte', 'gleichheit', 'rassismus', 'feminismus', 'lgbtqia+',
        'arbeiter', 'gewerkschaft', 'landlos', 'indigen',
        'kommunismus', 'sozialismus', 'anarchismus', 'widerstand', 'kampf',
        'polizei', 'repression', 'staatsgewalt', 'politischer gefangener',
        'freiheit', 'demokratie', 'soziale gerechtigkeit', 'landreform',
        'umwelt', 'klima', 'nachhaltigkeit',
        'regierung', 'wahl', 'präsident', 'scholz',
        'wirtschaft', 'inflation', 'arbeitslosigkeit', 'hunger', 'armut',
        'bildung', 'gesundheit', 'militär', 'intervention',
        'krieg', 'konflikt', 'angriff', 'bombe', 'armee', 'truppen',
        'völkermord', 'besetzung', 'widerstand', 'revolution',
    ],
}

# ============================================
# FONTES CONFIÁVEIS (NACIONAL E INTERNACIONAL)
# ============================================

FONTES_CONFIAVEIS = [
    # ===== 🇧🇷 BRASIL (NACIONAL) =====
    # Movimentos sociais
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 8},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'The Intercept Brasil', 'pais': 'Brasil', 'url': 'https://theintercept.com/brasil/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 8},
    {'nome': 'Revista Fórum', 'pais': 'Brasil', 'url': 'https://revistaforum.com.br/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 8},
    {'nome': 'Brasil 247', 'pais': 'Brasil', 'url': 'https://www.brasil247.com/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 7},
    {'nome': 'Diário do Centro do Mundo', 'pais': 'Brasil', 'url': 'https://www.diariodocentrodomundo.com.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 7},
    
    # Mídia alternativa
    {'nome': 'Mídia Ninja', 'pais': 'Brasil', 'url': 'https://midianinja.org/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'Jornalistas Livres', 'pais': 'Brasil', 'url': 'https://jornalistaslivres.org/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'Brasil Wire', 'pais': 'Brasil', 'url': 'https://brasilwire.com/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 8},
    
    # Movimentos específicos
    {'nome': 'MTST', 'pais': 'Brasil', 'url': 'https://mtst.org/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'UNE', 'pais': 'Brasil', 'url': 'https://une.org.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 8},
    {'nome': 'CUT', 'pais': 'Brasil', 'url': 'https://www.cut.org.br/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'América do Sul', 'confiabilidade': 9},
    
    # ===== 🇵🇹 PORTUGAL =====
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'Europa', 'confiabilidade': 9},
    {'nome': 'Jornal Tornado', 'pais': 'Portugal', 'url': 'https://jornaltornado.pt/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'Europa', 'confiabilidade': 8},
    
    # ===== 🌎 AMÉRICA LATINA =====
    {'nome': 'Página 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'América do Sul', 'confiabilidade': 8},
    {'nome': 'La Jornada', 'pais': 'México', 'url': 'https://www.jornada.com.mx/rss', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'América do Norte', 'confiabilidade': 8},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'América do Sul', 'confiabilidade': 7},
    {'nome': 'Resumen Latinoamericano', 'pais': 'Argentina', 'url': 'https://www.resumenlatinoamericano.org/feed/', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'América do Sul', 'confiabilidade': 9},
    {'nome': 'ANRed', 'pais': 'Argentina', 'url': 'https://www.anred.org/feed/', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'América do Sul', 'confiabilidade': 9},
    
    # ===== 🇺🇸 USA / INTERNACIONAL =====
    {'nome': 'Its Going Down', 'pais': 'USA', 'url': 'https://itsgoingdown.org/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 9},
    {'nome': 'CrimethInc', 'pais': 'Global', 'url': 'https://crimethinc.com/feeds/all.atom.xml', 'categoria': 'anarquista', 'idioma': 'en', 'continente': 'Global', 'confiabilidade': 9},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Global', 'confiabilidade': 9},
    {'nome': 'The Real News', 'pais': 'USA', 'url': 'https://therealnews.com/rss', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 8},
    {'nome': 'Democracy Now', 'pais': 'USA', 'url': 'https://www.democracynow.org/podcast.xml', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 9},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 8},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 9},
    {'nome': 'Common Dreams', 'pais': 'USA', 'url': 'https://www.commondreams.org/feed', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 8},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria': 'comunista', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 8},
    
    # ===== 🇬🇧 UK / EUROPA =====
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 9},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 8},
    {'nome': 'Ceasefire Magazine', 'pais': 'UK', 'url': 'https://ceasefiremagazine.co.uk/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 8},
    {'nome': 'Red Pepper', 'pais': 'UK', 'url': 'https://www.redpepper.org.uk/feed/', 'categoria': 'comunista', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 9},
    {'nome': 'Morning Star', 'pais': 'UK', 'url': 'https://morningstaronline.co.uk/rss.xml', 'categoria': 'comunista', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 8},
    
    # ===== 🇩🇪 ALEMANHA =====
    {'nome': 'Junge Welt', 'pais': 'Alemanha', 'url': 'https://www.jungewelt.de/feed', 'categoria': 'comunista', 'idioma': 'de', 'continente': 'Europa', 'confiabilidade': 8},
    
    # ===== 🇫🇷 FRANÇA =====
    {'nome': 'Le Monde Diplomatique', 'pais': 'França', 'url': 'https://www.monde-diplomatique.fr/rss', 'categoria': 'antifa', 'idioma': 'fr', 'continente': 'Europa', 'confiabilidade': 8},
    
    # ===== 🇨🇦 CANADÁ =====
    {'nome': 'The Maple', 'pais': 'Canadá', 'url': 'https://www.themaple.ca/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'América do Norte', 'confiabilidade': 8},
    
    # ===== 🇦🇺 AUSTRÁLIA =====
    {'nome': 'Red Flag', 'pais': 'Austrália', 'url': 'https://redflag.org.au/feed', 'categoria': 'comunista', 'idioma': 'en', 'continente': 'Oceania', 'confiabilidade': 8},
    
    # ===== 🌍 ÁFRICA =====
    {'nome': 'Pambazuka News', 'pais': 'África', 'url': 'https://www.pambazuka.org/feed', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'África', 'confiabilidade': 9},
    
    # ===== 🇮🇳 ÍNDIA =====
    {'nome': 'The Wire', 'pais': 'Índia', 'url': 'https://thewire.in/feed', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Ásia', 'confiabilidade': 7},
    
    # ===== 🇯🇵 JAPÃO =====
    {'nome': 'Japan Press Weekly', 'pais': 'Japão', 'url': 'http://www.japan-press.co.jp/rss', 'categoria': 'comunista', 'idioma': 'en', 'continente': 'Ásia', 'confiabilidade': 7},
    
    # ===== 🇨🇳 CHINA =====
    {'nome': 'China Daily', 'pais': 'China', 'url': 'https://www.chinadaily.com.cn/rss/', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Ásia', 'confiabilidade': 5},
]

# ============================================
# SISTEMA DE RADAR SUPREMO (BUSCA PARALELA INTELIGENTE)
# ============================================

@dataclass
class NoticiaAntifa:
    """Estrutura de dados para notícias"""
    id: str
    fonte: str
    pais: str
    continente: str
    categoria: str
    idioma: str
    titulo: str
    resumo: str
    link: str
    data: str
    publicada_em: str
    destaque: bool = False
    palavras_chave: List[str] = field(default_factory=list)
    confiabilidade: int = 5
    imagem: Optional[str] = None
    autor: Optional[str] = None

class RadarSupremoAntifa:
    """Sistema de radar global com busca paralela"""
    
    def __init__(self):
        self.fontes_ativas = []
        self.estatisticas = {
            'total_buscas': 0,
            'fontes_funcionando': 0,
            'noticias_encontradas': 0,
            'continentes': set(),
            'paises': set(),
            'categorias': defaultdict(int),
            'idiomas': defaultdict(int),
            'palavras_mais_usadas': Counter(),
        }
        self.cache_resultados = {}
        self.fila_buscas = queue.Queue()
        self.sessoes = {}
        
    def varrer_mundo(self, palavras_especificas: List[str] = None) -> List[NoticiaAntifa]:
        """
        Executa varredura global em paralelo com palavras-chave
        """
        logger.info("🛰️🏴 ATIVANDO RADAR SUPREMO ANTIFA...")
        
        resultados = []
        fontes_para_buscar = FONTES_CONFIAVEIS.copy()
        
        # Prioriza fontes por confiabilidade
        fontes_para_buscar.sort(key=lambda x: x['confiabilidade'], reverse=True)
        
        # Usa palavras-chave se fornecidas
        palavras = palavras_especificas or self._selecionar_palavras_aleatorias()
        
        with ThreadPoolExecutor(max_workers=config.MAX_TRABALHADORES) as executor:
            futures = {}
            for fonte in fontes_para_buscar:
                future = executor.submit(
                    self._testar_fonte_com_palavras, 
                    fonte, 
                    palavras
                )
                futures[future] = fonte
            
            total_fontes = len(futures)
            processadas = 0
            
            for future in as_completed(futures):
                processadas += 1
                fonte = futures[future]
                try:
                    noticias = future.result(timeout=config.TIMEOUT_TOTAL)
                    if noticias:
                        resultados.extend(noticias)
                        self.fontes_ativas.append(fonte['nome'])
                        self.estatisticas['fontes_funcionando'] += 1
                        self.estatisticas['continentes'].add(fonte['continente'])
                        self.estatisticas['paises'].add(fonte['pais'])
                        self.estatisticas['categorias'][fonte['categoria']] += 1
                        self.estatisticas['idiomas'][fonte['idioma']] += 1
                        
                        # Atualiza palavras mais usadas
                        for noticia in noticias:
                            for palavra in noticia.palavras_chave:
                                self.estatisticas['palavras_mais_usadas'][palavra] += 1
                        
                        logger.info(f"📡 {processadas}/{total_fontes} - ✅ {fonte['continente']} - {fonte['pais']}: {fonte['nome']} ({len(noticias)} notícias)")
                    else:
                        logger.debug(f"📡 {processadas}/{total_fontes} - ❌ {fonte['nome']} - sem notícias")
                        
                except TimeoutError:
                    logger.debug(f"📡 {processadas}/{total_fontes} - ⏰ {fonte['nome']} - timeout")
                except Exception as e:
                    logger.debug(f"📡 {processadas}/{total_fontes} - ❌ {fonte['nome']} - erro: {str(e)[:50]}")
        
        logger.info(f"✅🏴 RADAR CONCLUÍDO: {len(resultados)} notícias de {self.estatisticas['fontes_funcionando']} fontes")
        return resultados
    
    def _selecionar_palavras_aleatorias(self) -> List[str]:
        """Seleciona palavras-chave aleatórias de diferentes idiomas"""
        palavras_selecionadas = []
        idiomas = list(PALAVRAS_CHAVE.keys())
        
        # Seleciona palavras de cada idioma
        for _ in range(config.MAX_PALAVRAS_POR_BUSCA):
            idioma = random.choice(idiomas)
            palavra = random.choice(PALAVRAS_CHAVE[idioma])
            palavras_selecionadas.append(palavra)
        
        return list(set(palavras_selecionadas))  # Remove duplicatas
    
    def _testar_fonte_com_palavras(self, fonte: Dict, palavras: List[str]) -> List[NoticiaAntifa]:
        """Testa uma fonte e busca notícias relacionadas às palavras-chave"""
        
        noticias = []
        try:
            # Tenta com proxy se necessário
            proxy = None
            for tentativa in range(config.MAX_TENTATIVAS):
                try:
                    if tentativa > 0:
                        proxy = proxy_manager.obter_proxy()
                    
                    response = requests.get(
                        fonte['url'],
                        headers=config.HEADERS,
                        proxies=proxy,
                        timeout=config.TIMEOUT_REQUISICAO,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        break
                    elif tentativa == config.MAX_TENTATIVAS - 1:
                        return []
                        
                except Exception as e:
                    if tentativa == config.MAX_TENTATIVAS - 1:
                        return []
                    time.sleep(config.DELAY_ENTRE_REQUISICOES)
            
            # Parse do feed
            feed = feedparser.parse(response.content)
            
            if len(feed.entries) == 0:
                return []
            
            # Processa cada entrada
            for entrada in feed.entries[:config.MAX_NOTICIAS_POR_FONTE]:
                noticia = self._criar_noticia(fonte, entrada, palavras)
                if noticia:
                    # Verifica relevância (se contém palavras-chave)
                    relevancia = self._calcular_relevancia(noticia, palavras)
                    if relevancia > 0.3:  # 30% de relevância mínima
                        noticias.append(noticia)
                        
                        # Registra palavras encontradas
                        for palavra in palavras:
                            if palavra.lower() in noticia.titulo.lower() or palavra.lower() in noticia.resumo.lower():
                                self.estatisticas['palavras_mais_usadas'][palavra] += 1
            
            # Pequeno delay para não sobrecarregar
            time.sleep(random.uniform(0.1, 0.3))
            
        except Exception as e:
            logger.debug(f"Erro ao processar {fonte['nome']}: {e}")
        
        return noticias
    
    def _criar_noticia(self, fonte: Dict, entrada, palavras: List[str]) -> Optional[NoticiaAntifa]:
        """Cria objeto de notícia a partir da entrada do feed"""
        try:
            # Extrai resumo
            resumo = ""
            if hasattr(entrada, 'summary'):
                resumo = BeautifulSoup(entrada.summary, 'html.parser').get_text()
            elif hasattr(entrada, 'description'):
                resumo = BeautifulSoup(entrada.description, 'html.parser').get_text()
            elif hasattr(entrada, 'content'):
                for content in entrada.content:
                    if content.get('type') == 'text/html':
                        resumo = BeautifulSoup(content.value, 'html.parser').get_text()
                        break
            
            resumo = resumo[:250] + "..." if resumo and len(resumo) > 250 else resumo or "Leia o artigo completo no site original..."
            
            # Extrai data
            data = None
            if hasattr(entrada, 'published'):
                data = entrada.published
            elif hasattr(entrada, 'pubDate'):
                data = entrada.pubDate
            elif hasattr(entrada, 'updated'):
                data = entrada.updated
            
            if not data:
                data = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Extrai autor se disponível
            autor = None
            if hasattr(entrada, 'author'):
                autor = entrada.author
            elif hasattr(entrada, 'creator'):
                autor = entrada.creator
            
            # Extrai imagem se disponível
            imagem = None
            if hasattr(entrada, 'media_content') and entrada.media_content:
                for media in entrada.media_content:
                    if media.get('url') and 'image' in media.get('type', ''):
                        imagem = media['url']
                        break
            elif hasattr(entrada, 'links'):
                for link in entrada.links:
                    if link.get('rel') == 'enclosure' and 'image' in link.get('type', ''):
                        imagem = link['href']
                        break
            
            # Palavras-chave encontradas na notícia
            palavras_encontradas = []
            titulo_lower = entrada.title.lower()
            resumo_lower = resumo.lower()
            
            for palavra in palavras:
                if palavra.lower() in titulo_lower or palavra.lower() in resumo_lower:
                    palavras_encontradas.append(palavra)
            
            noticia = NoticiaAntifa(
                id=hashlib.md5(entrada.link.encode()).hexdigest()[:12],
                fonte=fonte['nome'],
                pais=fonte['pais'],
                continente=fonte['continente'],
                categoria=fonte['categoria'],
                idioma=fonte['idioma'],
                titulo=html.unescape(entrada.title),
                resumo=html.unescape(resumo),
                link=entrada.link,
                data=data,
                publicada_em=datetime.now().isoformat(),
                palavras_chave=palavras_encontradas,
                confiabilidade=fonte['confiabilidade'],
                imagem=imagem,
                autor=autor
            )
            
            return noticia
            
        except Exception as e:
            logger.debug(f"Erro ao criar notícia: {e}")
            return None
    
    def _calcular_relevancia(self, noticia: NoticiaAntifa, palavras: List[str]) -> float:
        """Calcula a relevância da notícia baseada nas palavras-chave"""
        if not palavras:
            return 0.5
        
        texto_completo = (noticia.titulo + " " + noticia.resumo).lower()
        palavras_encontradas = 0
        
        for palavra in palavras:
            if palavra.lower() in texto_completo:
                palavras_encontradas += 1
        
        return palavras_encontradas / len(palavras) if palavras else 0

radar = RadarSupremoAntifa()

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def carregar_cache():
    """Carrega cache de fontes que funcionaram"""
    if os.path.exists(config.ARQUIVO_CACHE):
        try:
            with open(config.ARQUIVO_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'funcionaram': [], 'ultima_atualizacao': None}
    return {'funcionaram': [], 'ultima_atualizacao': None}

def salvar_cache(cache):
    """Salva cache de fontes que funcionaram"""
    try:
        with open(config.ARQUIVO_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

def salvar_noticias(noticias: List[NoticiaAntifa]):
    """Salva notícias com validação"""
    try:
        # Converte para dicionário
        noticias_dict = [asdict(n) for n in noticias]
        
        with open(config.ARQUIVO_NOTICIAS, 'w', encoding='utf-8') as f:
            json.dump({
                'noticias': noticias_dict,
                'ultima_atualizacao': datetime.now().isoformat(),
                'total': len(noticias_dict),
                'estatisticas': {
                    'continentes': list(radar.estatisticas['continentes']),
                    'paises': list(radar.estatisticas['paises']),
                    'categorias': dict(radar.estatisticas['categorias']),
                    'idiomas': dict(radar.estatisticas['idiomas']),
                    'palavras_mais_usadas': dict(radar.estatisticas['palavras_mais_usadas'].most_common(20)),
                },
                'versao': '9.0 - RADAR SUPREMO ANTIFA',
                'config': {
                    'fontes_total': len(FONTES_CONFIAVEIS),
                    'palavras_chave_total': sum(len(p) for p in PALAVRAS_CHAVE.values()),
                }
            }, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✅🏴 Notícias salvas: {len(noticias)}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        return False

def carregar_noticias() -> List[NoticiaAntifa]:
    """Carrega notícias com fallback"""
    if os.path.exists(config.ARQUIVO_NOTICIAS):
        try:
            with open(config.ARQUIVO_NOTICIAS, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                noticias_dict = dados.get('noticias', [])
                
                # Converte de volta para objetos NoticiaAntifa
                noticias = []
                for n in noticias_dict:
                    try:
                        noticias.append(NoticiaAntifa(**n))
                    except:
                        pass
                return noticias
        except:
            return []
    return []

def buscar_noticias_supremo():
    """Função principal de busca com radar supremo"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🛰️🏴 [{datetime.now().strftime('%H:%M:%S')}] ATIVANDO RADAR SUPREMO ANTIFA")
    logger.info(f"{'='*60}")
    
    # Seleciona palavras-chave aleatórias
    palavras = radar._selecionar_palavras_aleatorias()
    logger.info(f"🔍 Palavras-chave: {', '.join(palavras[:5])}... ({len(palavras)} total)")
    
    # Carrega notícias antigas
    noticias_antigas = carregar_noticias()
    links_antigos = {n.link for n in noticias_antigas}
    
    # Varre o mundo com palavras-chave
    novas_noticias = radar.varrer_mundo(palavras)
    
    # Filtra notícias já existentes
    noticias_novas = [n for n in novas_noticias if n.link not in links_antigos]
    
    # Relatório do radar
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 RELATÓRIO DO RADAR SUPREMO:")
    logger.info(f"  📡 Fontes ativas: {radar.estatisticas['fontes_funcionando']}")
    logger.info(f"  🌍 Continentes cobertos: {len(radar.estatisticas['continentes'])}")
    logger.info(f"  🏳️ Países: {len(radar.estatisticas['paises'])}")
    logger.info(f"  🔤 Idiomas: {len(radar.estatisticas['idiomas'])}")
    logger.info(f"  📰 Notícias novas: {len(noticias_novas)}")
    logger.info(f"{'='*60}")
    
    if noticias_novas:
        todas_noticias = noticias_novas + noticias_antigas
        todas_noticias.sort(key=lambda x: x.data, reverse=True)
        todas_noticias = todas_noticias[:config.MAX_NOTICIAS_TOTAL]
        
        # Marca algumas como destaque
        for i, n in enumerate(todas_noticias[:7]):
            n.destaque = True
        
        if salvar_noticias(todas_noticias):
            logger.info(f"  🎯 {len(noticias_novas)} nova(s) notícia(s) de {radar.estatisticas['fontes_funcionando']} fontes!")
            logger.info(f"  📊 Acervo total: {len(todas_noticias)}")
    else:
        logger.info("  ℹ️ Nenhuma notícia nova encontrada")
    
    return noticias_novas

app = Flask(__name__)

# ============================================
# PÁGINA PRINCIPAL - DESIGN ANTIFA SUPREMO
# ============================================

@app.route('/')
def home():
    noticias = carregar_noticias()
    
    # Separa por categoria
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    antifa = [n for n in noticias if n.categoria in ['antifa', 'anarquista', 'comunista']]
    nacionais = [n for n in noticias if n.pais == 'Brasil']
    internacionais = [n for n in noticias if n.pais != 'Brasil']
    
    # Destaques
    destaques = [n for n in noticias if n.destaque][:5]
    
    # Estatísticas por continente
    continentes = defaultdict(int)
    for n in noticias:
        continentes[n.continente] += 1
    
    # Estatísticas de palavras
    palavras_stats = radar.estatisticas['palavras_mais_usadas'].most_common(10)
    
    # HTML dos destaques
    destaques_html = ''
    for n in destaques:
        bandeira = get_bandeira(n.pais)
        destaques_html += f'''
        <div class="destaque-card">
            <span class="destaque-tag">⭐ DESTAQUE</span>
            <span class="fonte">{bandeira} {n.fonte}</span>
            <h3>{n.titulo}</h3>
            <p>{n.resumo[:150]}...</p>
            <div class="card-footer">
                <span class="data">{n.data[:16]}</span>
                <a href="{n.link}" target="_blank">Ler mais →</a>
            </div>
        </div>
        '''
    
    # HTML Geopolítica
    geo_html = ''
    for n in geopolitica[:10]:
        bandeira = get_bandeira(n.pais)
        geo_html += f'''
        <article class="noticia">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">{n.pais}</span>
                <span class="confiabilidade" title="Confiabilidade">{'★' * n.confiabilidade}{'☆' * (9 - n.confiabilidade)}</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:16]}</span>
                <a href="{n.link}" target="_blank">🔗</a>
            </div>
        </article>
        '''
    
    # HTML Antifa
    antifa_html = ''
    for n in antifa[:10]:
        bandeira = get_bandeira(n.pais)
        antifa_html += f'''
        <article class="noticia">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">{n.pais}</span>
                <span class="categoria-badge {n.categoria}">🏴 {n.categoria}</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:16]}</span>
                <a href="{n.link}" target="_blank">🔗</a>
            </div>
        </article>
        '''
    
    # HTML Nacionais (Brasil)
    nacional_html = ''
    for n in nacionais[:10]:
        bandeira = get_bandeira(n.pais)
        nacional_html += f'''
        <article class="noticia nacional">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">{n.pais}</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:16]}</span>
                <a href="{n.link}" target="_blank">🔗</a>
            </div>
        </article>
        '''
    
    # HTML Internacionais
    internacional_html = ''
    for n in internacionais[:10]:
        bandeira = get_bandeira(n.pais)
        internacional_html += f'''
        <article class="noticia internacional">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">{n.pais}</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:16]}</span>
                <a href="{n.link}" target="_blank">🔗</a>
            </div>
        </article>
        '''
    
    # HTML do mapa de continentes
    continentes_html = ''
    for cont, qtd in continentes.items():
        continentes_html += f'<span class="contente-badge">{cont}: {qtd}</span>'
    
    # HTML das palavras mais usadas
    palavras_html = ''
    for palavra, count in palavras_stats:
        palavras_html += f'<span class="palavra-badge">#{palavra}: {count}</span>'
    
    return f'''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Informação antifascista - Nacional e Internacional">
        <meta name="keywords" content="antifa, antifascista, notícias, brasil, mundo, geopolítica">
        <meta name="author" content="SHARP - FRONT 16 RJ">
        <title>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</title>
        <style>
            /* RESET E ESTILOS GLOBAIS */
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
            
            /* HEADER COM DUAS BOLAS ANTIFA */
            .header {{
                background: linear-gradient(135deg, #000000 0%, #1a0000 100%);
                border-bottom: 4px solid #ff0000;
                padding: 40px 20px 60px;
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
                background: repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 10px,
                    rgba(255,0,0,0.05) 10px,
                    rgba(255,0,0,0.05) 20px
                );
                animation: moveStripes 30s linear infinite;
            }}
            
            @keyframes moveStripes {{
                0% {{ transform: translateX(0) translateY(0); }}
                100% {{ transform: translateX(50%) translateY(50%); }}
            }}
            
            .bolas-container {{
                position: absolute;
                top: 20px;
                right: 30px;
                display: flex;
                gap: 20px;
                z-index: 10;
            }}
            
            .bola-vermelha {{
                width: 70px;
                height: 70px;
                background: #ff0000;
                border-radius: 50%;
                box-shadow: 0 0 40px rgba(255,0,0,0.8);
                animation: pulsar-vermelha 2s infinite ease-in-out;
            }}
            
            .bola-preta {{
                width: 70px;
                height: 70px;
                background: #000;
                border-radius: 50%;
                border: 3px solid #ff0000;
                box-shadow: 0 0 40px rgba(255,0,0,0.5);
                animation: pulsar-preta 2.5s infinite ease-in-out;
            }}
            
            @keyframes pulsar-vermelha {{
                0% {{ transform: scale(1); box-shadow: 0 0 40px rgba(255,0,0,0.8); }}
                50% {{ transform: scale(1.15); box-shadow: 0 0 70px rgba(255,0,0,1); }}
                100% {{ transform: scale(1); box-shadow: 0 0 40px rgba(255,0,0,0.8); }}
            }}
            
            @keyframes pulsar-preta {{
                0% {{ transform: scale(1); box-shadow: 0 0 30px rgba(255,0,0,0.4); }}
                50% {{ transform: scale(1.1); box-shadow: 0 0 60px rgba(255,0,0,0.8); }}
                100% {{ transform: scale(1); box-shadow: 0 0 30px rgba(255,0,0,0.4); }}
            }}
            
            h1 {{
                color: #ff0000;
                font-size: clamp(2.5rem, 8vw, 4rem);
                font-weight: 900;
                letter-spacing: 4px;
                margin-bottom: 15px;
                text-transform: uppercase;
                text-shadow: 3px 3px 0px #000, 0 0 30px rgba(255,0,0,0.5);
                position: relative;
                z-index: 1;
            }}
            
            .subtitulo {{
                color: #ccc;
                font-size: 1.3rem;
                margin-bottom: 30px;
                position: relative;
                z-index: 1;
                font-style: italic;
                border-top: 1px solid #ff0000;
                border-bottom: 1px solid #ff0000;
                padding: 15px 0;
                display: inline-block;
            }}
            
            .stats-supremas {{
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
                margin: 30px 0;
                position: relative;
                z-index: 1;
            }}
            
            .stat-supremo {{
                background: rgba(0,0,0,0.7);
                backdrop-filter: blur(10px);
                border: 1px solid #ff0000;
                padding: 12px 30px;
                border-radius: 50px;
                font-size: 1rem;
                font-weight: bold;
                transition: all 0.3s;
                box-shadow: 0 5px 15px rgba(255,0,0,0.2);
            }}
            
            .stat-supremo:hover {{
                background: #ff0000;
                color: #000;
                transform: translateY(-3px);
                box-shadow: 0 10px 25px rgba(255,0,0,0.4);
            }}
            
            .radar-info {{
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
                margin: 20px 0;
            }}
            
            .radar-badge {{
                background: #111;
                color: #ff0000;
                padding: 8px 20px;
                border-radius: 30px;
                font-size: 0.9rem;
                border: 1px solid #ff0000;
            }}
            
            /* SEÇÕES DE CONTEÚDO */
            .secao {{
                max-width: 1400px;
                margin: 50px auto;
                padding: 0 20px;
            }}
            
            .secao-titulo {{
                color: #ff0000;
                font-size: 2.2rem;
                margin-bottom: 30px;
                display: flex;
                align-items: center;
                gap: 15px;
                border-left: 5px solid #ff0000;
                padding-left: 20px;
            }}
            
            .secao-titulo .badge {{
                background: #ff0000;
                color: #000;
                padding: 5px 15px;
                border-radius: 30px;
                font-size: 1rem;
            }}
            
            .grid-destaques {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 30px;
                margin-top: 30px;
            }}
            
            .destaque-card {{
                background: linear-gradient(145deg, #111 0%, #1a0000 100%);
                border-radius: 20px;
                padding: 30px;
                position: relative;
                border: 1px solid #333;
                transition: all 0.3s;
                overflow: hidden;
                border-left: 5px solid #ff0000;
            }}
            
            .destaque-card::before {{
                content: '🏴';
                position: absolute;
                bottom: -20px;
                right: -20px;
                font-size: 100px;
                opacity: 0.1;
                transform: rotate(-15deg);
            }}
            
            .destaque-card:hover {{
                transform: translateY(-8px);
                border-color: #ff0000;
                box-shadow: 0 20px 40px rgba(255,0,0,0.3);
            }}
            
            .destaque-tag {{
                background: #ff0000;
                color: #000;
                padding: 5px 15px;
                border-radius: 30px;
                font-size: 0.9rem;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 20px;
            }}
            
            .grid-duplo {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
                margin-top: 40px;
            }}
            
            .coluna-especial {{
                background: rgba(17, 17, 17, 0.8);
                backdrop-filter: blur(10px);
                border-radius: 30px;
                padding: 30px;
                border: 1px solid #333;
                border-top: 4px solid #ff0000;
            }}
            
            .coluna-titulo {{
                color: #ff0000;
                font-size: 1.8rem;
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
                transform: translateX(8px);
                background: #1a1a1a;
                border-left-width: 6px;
            }}
            
            .noticia.nacional {{
                border-left-color: #00ff00;
            }}
            
            .noticia.internacional {{
                border-left-color: #ffaa00;
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
                font-weight: 700;
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
            
            .confiabilidade {{
                color: #ffaa00;
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
                padding: 5px 12px;
                border-radius: 5px;
                border: 1px solid transparent;
            }}
            
            a:hover {{
                background: #ff0000;
                color: #000;
                border-color: #ff0000;
            }}
            
            .mensagem-vazia {{
                text-align: center;
                padding: 80px 20px;
                color: #666;
                font-style: italic;
                background: #111;
                border-radius: 20px;
                border: 2px dashed #333;
            }}
            
            .badge-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 20px 0;
                justify-content: center;
            }}
            
            .contente-badge, .palavra-badge {{
                background: #1a1a1a;
                border: 1px solid #333;
                padding: 6px 18px;
                border-radius: 30px;
                font-size: 0.9rem;
                transition: all 0.3s;
            }}
            
            .contente-badge:hover {{
                background: #ff0000;
                color: #000;
                border-color: #ff0000;
            }}
            
            .palavra-badge {{
                background: #ff000020;
                border-color: #ff0000;
            }}
            
            /* BOTÃO RADAR */
            .radar-button-container {{
                text-align: center;
                margin: 50px 0;
            }}
            
            .radar-button {{
                display: inline-block;
                padding: 18px 50px;
                background: linear-gradient(135deg, #000, #ff0000);
                color: #fff;
                font-size: 1.3rem;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 2px;
                border-radius: 60px;
                border: 2px solid #ff0000;
                transition: all 0.3s;
                box-shadow: 0 10px 30px rgba(255,0,0,0.3);
                animation: pulsar-botao 2s infinite;
            }}
            
            .radar-button:hover {{
                transform: scale(1.05);
                box-shadow: 0 15px 40px rgba(255,0,0,0.6);
                background: linear-gradient(135deg, #ff0000, #000);
            }}
            
            @keyframes pulsar-botao {{
                0% {{ box-shadow: 0 10px 30px rgba(255,0,0,0.3); }}
                50% {{ box-shadow: 0 15px 50px rgba(255,0,0,0.8); }}
                100% {{ box-shadow: 0 10px 30px rgba(255,0,0,0.3); }}
            }}
            
            /* AGRADECIMENTO */
            .agradecimento {{
                max-width: 800px;
                margin: 60px auto;
                padding: 40px;
                background: linear-gradient(145deg, #111, #1a0000);
                border-radius: 30px;
                border: 1px solid #333;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .agradecimento::before {{
                content: '✊🏴';
                position: absolute;
                bottom: -20px;
                left: -20px;
                font-size: 120px;
                opacity: 0.1;
            }}
            
            .agradecimento::after {{
                content: '🔴';
                position: absolute;
                top: -20px;
                right: -20px;
                font-size: 120px;
                opacity: 0.1;
            }}
            
            .agradecimento p {{
                color: #ccc;
                font-size: 1.2rem;
                line-height: 1.8;
                font-style: italic;
            }}
            
            .assinatura {{
                color: #ff0000;
                font-weight: bold;
                margin-top: 30px;
                font-size: 1.4rem;
                letter-spacing: 2px;
            }}
            
            /* FOOTER */
            .footer {{
                background: #000;
                border-top: 4px solid #ff0000;
                padding: 60px 20px 40px;
                margin-top: 80px;
                text-align: center;
            }}
            
            .footer-stats {{
                display: flex;
                justify-content: center;
                gap: 40px;
                flex-wrap: wrap;
                margin-bottom: 40px;
                color: #888;
            }}
            
            .footer-links {{
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-bottom: 40px;
                flex-wrap: wrap;
            }}
            
            .footer-links a {{
                color: #666;
                font-size: 0.9rem;
                padding: 5px 20px;
                border: 1px solid #333;
                border-radius: 30px;
            }}
            
            .footer-links a:hover {{
                background: #ff0000;
                color: #000;
                border-color: #ff0000;
            }}
            
            /* RESPONSIVIDADE */
            @media (max-width: 900px) {{
                .grid-duplo {{
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
                .stats-supremas {{
                    flex-direction: column;
                    align-items: center;
                }}
                
                .stat-supremo {{
                    width: 100%;
                    text-align: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="bolas-container">
                <div class="bola-vermelha" title="Luta e Resistência"></div>
                <div class="bola-preta" title="Antifascismo"></div>
            </div>
            
            <h1>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</h1>
            <p class="subtitulo">📰 INFORMAÇÃO ANTIFASCISTA • NACIONAL & INTERNACIONAL</p>
            
            <div class="stats-supremas">
                <span class="stat-supremo">📰 {len(noticias)} notícias</span>
                <span class="stat-supremo">🌍 {len(continentes)} continentes</span>
                <span class="stat-supremo">🏳️ {len(set(n.pais for n in noticias))} países</span>
                <span class="stat-supremo">📡 {len(set(n.fonte for n in noticias))} fontes</span>
                <span class="stat-supremo">🔴 {len(antifa)} antifa</span>
                <span class="stat-supremo">⚔️ {len(geopolitica)} geopolitica</span>
                <span class="stat-supremo">🇧🇷 {len(nacionais)} nacional</span>
                <span class="stat-supremo">🌎 {len(internacionais)} internacional</span>
            </div>
            
            <div class="radar-info">
                <span class="radar-badge">🛰️ RADAR ATIVO: {radar.estatisticas['fontes_funcionando']} fontes</span>
                <span class="radar-badge">🔤 IDIOMAS: {len(radar.estatisticas['idiomas'])}</span>
                <span class="radar-badge">⚡ ÚLTIMA BUSCA: {datetime.now().strftime('%H:%M')}</span>
            </div>
            
            <div class="badge-container">
                {continentes_html}
            </div>
            
            <div class="badge-container">
                {palavras_html}
            </div>
        </div>
        
        <!-- DESTAQUES -->
        <div class="secao">
            <div class="secao-titulo">
                ⭐ DESTAQUES DO RADAR ANTIFA
                <span class="badge">mais relevantes</span>
            </div>
            <div class="grid-destaques">
                {destaques_html if destaques_html else '<div class="mensagem-vazia">🛰️ Radar em operação... buscando informações antifascistas...</div>'}
            </div>
        </div>
        
        <!-- COLUNAS PRINCIPAIS -->
        <div class="grid-duplo" style="max-width: 1400px; margin: 0 auto; padding: 0 20px;">
            <!-- COLUNA GEOPOLÍTICA -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    ⚔️ GEOPOLÍTICA & GUERRA
                    <span class="badge">{len(geopolitica)}</span>
                </div>
                {geo_html if geo_html else '<div class="mensagem-vazia">🛰️ Escaneando conflitos globais...</div>'}
            </div>
            
            <!-- COLUNA ANTIFA -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    🏴 MOVIMENTOS ANTIFASCISTAS
                    <span class="badge">{len(antifa)}</span>
                </div>
                {antifa_html if antifa_html else '<div class="mensagem-vazia">🛰️ Buscando movimentos sociais...</div>'}
            </div>
        </div>
        
        <!-- SEÇÃO NACIONAL vs INTERNACIONAL -->
        <div class="grid-duplo" style="max-width: 1400px; margin: 40px auto; padding: 0 20px;">
            <!-- COLUNA NACIONAL -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    🇧🇷 BRASIL (NACIONAL)
                    <span class="badge">{len(nacionais)}</span>
                </div>
                {nacional_html if nacional_html else '<div class="mensagem-vazia">🛰️ Buscando notícias nacionais...</div>'}
            </div>
            
            <!-- COLUNA INTERNACIONAL -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    🌍 INTERNACIONAL
                    <span class="badge">{len(internacionais)}</span>
                </div>
                {internacional_html if internacional_html else '<div class="mensagem-vazia">🛰️ Buscando notícias internacionais...</div>'}
            </div>
        </div>
        
        <!-- BOTÃO RADAR -->
        <div class="radar-button-container">
            <a href="/forcar-busca" class="radar-button">🛰️ ATIVAR RADAR SUPREMO</a>
        </div>
        
        <!-- AGRADECIMENTO ANTIFA -->
        <div class="agradecimento">
            <p>"A informação é nossa arma mais poderosa contra o fascismo. Agradecemos a todos os antifascistas, anarquistas, comunistas e lutadores sociais que constroem um mundo sem opressão. A luta continua!"</p>
            <div class="assinatura">✊🏴 SHARP - FRONT 16 RJ 🏴🔴</div>
            <p style="margin-top: 20px; color: #ff0000;">"Enquanto houver fascismo, haverá antifascismo."</p>
        </div>
        
        <!-- FOOTER -->
        <div class="footer">
            <div class="footer-stats">
                <span>🛰️ Radar a cada {config.TEMPO_ATUALIZACAO} minutos</span>
                <span>🔗 Links originais</span>
                <span>⚡ {len(noticias)} notícias no acervo</span>
                <span>🏴 {len(radar.estatisticas['fontes_funcionando'])} fontes ativas</span>
            </div>
            
            <div class="footer-links">
                <a href="#">Sobre</a>
                <a href="#">Fontes</a>
                <a href="#">Contato</a>
                <a href="#">Privacidade</a>
                <a href="#">Manifesto</a>
            </div>
            
            <p style="color: #444; font-size: 0.8rem; max-width: 800px; margin: 0 auto;">
                🔴🏴 SHARP - FRONT 16 RJ • Informação Antifascista • Nacional & Internacional
            </p>
            <p style="color: #333; font-size: 0.7rem; margin-top: 20px;">
                Todos os links são das fontes originais • Conteúdo sob responsabilidade de cada veículo
            </p>
            <p style="color: #222; font-size: 0.6rem; margin-top: 10px;">
                v9.0 • RADAR SUPREMO ANTIFA • 40+ fontes • 5 idiomas • 3000+ notícias
            </p>
        </div>
    </body>
    </html>
    '''

# ============================================
# FUNÇÃO PARA PEGAR BANDEIRAS
# ============================================

def get_bandeira(pais):
    """Retorna a bandeira emoji para o país"""
    bandeiras = {
        'Brasil': '🇧🇷',
        'Portugal': '🇵🇹',
        'Argentina': '🇦🇷',
        'México': '🇲🇽',
        'Venezuela': '🇻🇪',
        'USA': '🇺🇸',
        'UK': '🇬🇧',
        'Alemanha': '🇩🇪',
        'França': '🇫🇷',
        'Espanha': '🇪🇸',
        'Itália': '🇮🇹',
        'Canadá': '🇨🇦',
        'Austrália': '🇦🇺',
        'Japão': '🇯🇵',
        'China': '🇨🇳',
        'Índia': '🇮🇳',
        'Israel': '🇮🇱',
        'Qatar': '🇶🇦',
        'Global': '🌍',
        'África': '🌍',
        'África do Sul': '🇿🇦',
        'Quênia': '🇰🇪',
        'Congo': '🇨🇩',
        'Bélgica': '🇧🇪',
        'Irã': '🇮🇷',
        'Emirados': '🇦🇪',
        'Singapura': '🇸🇬',
        'Coreia do Sul': '🇰🇷',
        'Hong Kong': '🇭🇰',
        'Nova Zelândia': '🇳🇿',
    }
    return bandeiras.get(pais, '🏴')

# ============================================
# ROTA PARA FORÇAR BUSCA SUPREMA
# ============================================

@app.route('/forcar-busca')
def forcar_busca():
    import threading
    def busca_suprema():
        buscar_noticias_supremo()
    threading.Thread(target=busca_suprema).start()
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔴🏴 RADAR SUPREMO ATIVADO</title>
        <style>
            body { 
                background: black; 
                color: white; 
                font-family: 'Inter', Arial; 
                text-align: center; 
                padding: 50px; 
                background: linear-gradient(135deg, #000, #1a0000);
            }
            h1 { color: red; font-size: 3em; text-shadow: 2px 2px 0px black; }
            .info { 
                background: #111; 
                padding: 30px; 
                border-radius: 20px; 
                margin: 20px auto;
                max-width: 600px;
                border-left: 5px solid red;
                border-right: 5px solid black;
            }
            .bola { 
                width: 100px; 
                height: 100px; 
                background: red; 
                border-radius: 50%; 
                margin: 20px auto;
                box-shadow: 0 0 50px red;
                animation: pulsar 2s infinite;
            }
            @keyframes pulsar {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); box-shadow: 0 0 80px red; }
                100% { transform: scale(1); }
            }
            a { color: red; text-decoration: none; font-size: 1.2em; }
        </style>
    </head>
    <body>
        <div class="bola"></div>
        <h1>🔴🏴 RADAR SUPREMO ATIVADO!</h1>
        <div class="info">
            <h2 style="color: red;">🛰️ O RADAR ESTÁ VARRENDO O MUNDO</h2>
            <p style="font-size: 1.2em;">As notícias antifascistas estão sendo coletadas agora em 40+ fontes e 5 idiomas.</p>
            <p style="color: #888;">Aguarde 2-3 minutos e atualize a página.</p>
            <p style="margin-top: 30px;"><a href="/">⬅️ VOLTAR AO RADAR</a></p>
        </div>
    </body>
    </html>
    '''

# ============================================
# API DE ESTATÍSTICAS
# ============================================

@app.route('/api/stats')
def api_stats():
    noticias = carregar_noticias()
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    antifa = [n for n in noticias if n.categoria in ['antifa', 'anarquista', 'comunista']]
    nacionais = [n for n in noticias if n.pais == 'Brasil']
    internacionais = [n for n in noticias if n.pais != 'Brasil']
    
    return jsonify({
        'total': len(noticias),
        'geopolitica': len(geopolitica),
        'antifa': len(antifa),
        'nacional': len(nacionais),
        'internacional': len(internacionais),
        'paises': len(set(n.pais for n in noticias)),
        'continentes': len(set(n.continente for n in noticias)),
        'fontes': len(set(n.fonte for n in noticias)),
        'idiomas': len(set(n.idioma for n in noticias)),
        'ultima_atualizacao': datetime.now().isoformat(),
        'estatisticas_radar': {
            'fontes_ativas': radar.estatisticas['fontes_funcionando'],
            'palavras_mais_usadas': dict(radar.estatisticas['palavras_mais_usadas'].most_common(20)),
        }
    })

# ============================================
# INICIALIZAÇÃO SUPREMA
# ============================================

def inicializar_supremo():
    """Inicializa o sistema supremo"""
    logger.info("="*60)
    logger.info("🔴🏴 SHARP - FRONT 16 RJ - RADAR SUPREMO ANTIFA v9.0")
    logger.info("="*60)
    
    cache = carregar_cache()
    noticias = carregar_noticias()
    logger.info(f"📊 Acervo inicial: {len(noticias)} notícias")
    logger.info(f"🌍 Fontes configuradas: {len(FONTES_CONFIAVEIS)}")
    logger.info(f"🔤 Palavras-chave: {sum(len(p) for p in PALAVRAS_CHAVE.values())} em {len(PALAVRAS_CHAVE)} idiomas")
    
    # Busca inicial em background
    def busca_background():
        time.sleep(5)
        logger.info("🚀 Iniciando radar supremo automático...")
        try:
            buscar_noticias_supremo()
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
    
    thread = threading.Thread(target=busca_background, daemon=True)
    thread.start()
    logger.info("✅🏴 RADAR SUPREMO ATIVADO - 40+ THREADS SIMULTÂNEAS")
    logger.info("="*60)

inicializar_supremo()

# ============================================
# FIM - NÃO COLOQUE app.run() AQUI!
# ============================================
