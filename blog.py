#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    [Vermelho][Preto] SHARP - FRONT 16 RJ [Preto][Vermelho]   ║
║              SISTEMA SUPREMO ANTIFA - VERSAO 10.0 - FINAL                    ║
║         RADAR AUTOMATICO COM TIMER DE 5 SEGUNDOS - HORARIO DE BRASILIA       ║
║              "A informacao e nossa arma mais poderosa"                       ║
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
# CONFIGURACOES PROFISSIONAIS AVANCADAS
# ============================================

class Config:
    """Configuracoes avancadas do sistema supremo antifa"""
    
    # Identidade
    NOME_SITE = "SHARP - FRONT 16 RJ"
    LEMA = "A informacao e nossa arma mais poderosa"
    COR_PRIMARIA = "#ff0000"  # Vermelho
    COR_SECUNDARIA = "#000000"  # Preto
    
    # Arquivos
    ARQUIVO_NOTICIAS = 'noticias_salvas.json'
    ARQUIVO_CACHE = 'cache_fontes.json'
    ARQUIVO_HISTORICO = 'historico_buscas.json'
    ARQUIVO_PALAVRAS = 'palavras_chave.json'
    ARQUIVO_LOG = 'radar_antifa.log'
    
    # Tempos - AJUSTADOS para 5 segundos
    TEMPO_ATUALIZACAO = 10  # minutos
    TIMEOUT_REQUISICAO = 8  # segundos
    TIMEOUT_TOTAL = 30  # segundos
    DELAY_ENTRE_REQUISICOES = 5  # 5 SEGUNDOS entre cada site (mais seguro)
    DELAY_INICIAL = 2  # segundos antes de comecar
    
    # Limites
    MAX_NOTICIAS_POR_FONTE = 5
    MAX_NOTICIAS_TOTAL = 3000
    MAX_TRABALHADORES = 10  # Reduzido para evitar sobrecarga
    MAX_TENTATIVAS = 2
    MAX_PALAVRAS_POR_BUSCA = 8
    
    # Headers para parecer navegador real
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7,fr;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    # Horario
    TIMEZONE = -3  # Brasilia (UTC-3)

config = Config()

# ============================================
# FUNCAO PARA HORARIO DE BRASILIA
# ============================================

def horario_brasilia():
    """Retorna o horario atual de Brasilia"""
    utc = datetime.utcnow()
    brasilia = utc - timedelta(hours=3)  # UTC-3
    return brasilia.strftime('%d/%m/%Y %H:%M:%S')

def hora_brasilia():
    """Retorna apenas a hora de Brasilia"""
    utc = datetime.utcnow()
    brasilia = utc - timedelta(hours=3)
    return brasilia.strftime('%H:%M')

# ============================================
# LOGGING PROFISSIONAL
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Vermelho][Preto] %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.ARQUIVO_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ANTIFA-RADAR')

# ============================================
# SISTEMA DE PROXY INTELIGENTE
# ============================================

class ProxyManagerSupremo:
    """Gerencia rotacao de proxies para evitar bloqueios"""
    
    def __init__(self):
        self.proxies_http = []
        self.proxies_https = []
        self.proxies_socks = []
        self.proxy_atual = None
        self.blacklist = set()
        self.cache_proxies = {}
        self.atualizar_lista()
    
    def atualizar_lista(self):
        """Busca proxies publicos atualizados de multiplas fontes"""
        try:
            fontes_proxy = [
                'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
                'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
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
            
            logger.info(f"[OK] PROXYS CARREGADOS: HTTP={len(self.proxies_http)} HTTPS={len(self.proxies_https)} SOCKS={len(self.proxies_socks)}")
            
        except Exception as e:
            logger.error(f"[Erro] ao carregar proxies: {e}")
    
    def obter_proxy(self, tipo='http'):
        """Retorna um proxy aleatorio da lista"""
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
# PALAVRAS-CHAVE MULTILINGUE (FOCO ANTIFA)
# ============================================

PALAVRAS_CHAVE = {
    # Brasil
    'pt': [
        'antifa', 'antifascista', 'fascismo', 'nazismo', 'neonazista',
        'movimento social', 'protesto', 'manifestacao', 'greve', 'ocupacao',
        'direitos humanos', 'igualdade', 'racismo', 'feminismo', 'lgbtqia',
        'trabalhador', 'sindicato', 'sem terra', 'mst', 'mtst',
        'comunismo', 'socialismo', 'anarquismo', 'resistencia', 'luta',
        'policia', 'repressao', 'violencia estatal', 'prisao politica',
        'liberdade', 'democracia', 'justica social', 'reforma agraria',
        'amazonia', 'indigena', 'quilombola', 'meio ambiente', 'sustentabilidade',
        'governo', 'congresso', 'eleicao', 'presidente', 'economia',
        'guerra', 'conflito', 'ataque', 'bomba', 'exercito', 'tropas',
        'genocidio', 'ocupacao', 'revolucao',
        'bolsonaro', 'lula', 'moro', 'doria', 'boulos',
    ],
    
    # Ingles
    'en': [
        'antifa', 'antifascist', 'fascism', 'nazism', 'neonazi',
        'social movement', 'protest', 'demonstration', 'strike', 'occupation',
        'human rights', 'equality', 'racism', 'feminism', 'lgbtqia',
        'worker', 'union', 'landless', 'indigenous', 'black lives matter',
        'communism', 'socialism', 'anarchism', 'resistance', 'struggle',
        'police', 'repression', 'state violence', 'political prisoner',
        'freedom', 'democracy', 'social justice', 'land reform',
        'climate', 'environment', 'amazon rainforest', 'palestine', 'israel',
        'war', 'conflict', 'attack', 'bomb', 'army', 'troops',
        'genocide', 'occupation', 'resistance', 'revolution',
        'trump', 'biden', 'putin', 'zelensky', 'netanyahu',
    ],
    
    # Espanhol
    'es': [
        'antifa', 'antifascista', 'fascismo', 'nazismo', 'neonazi',
        'movimiento social', 'protesta', 'manifestacion', 'huelga', 'ocupacion',
        'derechos humanos', 'igualdad', 'racismo', 'feminismo', 'lgbtqia',
        'trabajador', 'sindicato', 'sin tierra', 'indigena', 'mapuche',
        'comunismo', 'socialismo', 'anarquismo', 'resistencia', 'lucha',
        'policia', 'represion', 'violencia estatal', 'preso politico',
        'libertad', 'democracia', 'justicia social', 'reforma agraria',
        'amazonia', 'medio ambiente', 'cambio climatico', 'palestina',
        'guerra', 'conflicto', 'ataque', 'bomba', 'ejercito', 'tropas',
        'genocidio', 'ocupacion', 'resistencia', 'revolucion',
        'petro', 'milei', 'lula', 'bukele', 'lopez',
    ],
}

# ============================================
# FONTES CONFIABEIS (NACIONAL E INTERNACIONAL)
# ============================================

FONTES_CONFIAVEIS = [
    # ===== BRASIL (NACIONAL) PRIORIDADE MAXIMA =====
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 10, 'prioridade': 1},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 10, 'prioridade': 1},
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 9, 'prioridade': 1},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 9, 'prioridade': 1},
    {'nome': 'The Intercept Brasil', 'pais': 'Brasil', 'url': 'https://theintercept.com/brasil/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 8, 'prioridade': 1},
    {'nome': 'Brasil 247', 'pais': 'Brasil', 'url': 'https://www.brasil247.com/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 7, 'prioridade': 1},
    {'nome': 'Diario do Centro do Mundo', 'pais': 'Brasil', 'url': 'https://www.diariodocentrodomundo.com.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 7, 'prioridade': 1},
    {'nome': 'Midia Ninja', 'pais': 'Brasil', 'url': 'https://midianinja.org/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 9, 'prioridade': 1},
    {'nome': 'Jornalistas Livres', 'pais': 'Brasil', 'url': 'https://jornalistaslivres.org/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 9, 'prioridade': 1},
    {'nome': 'MTST', 'pais': 'Brasil', 'url': 'https://mtst.org/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 9, 'prioridade': 1},
    {'nome': 'UNE', 'pais': 'Brasil', 'url': 'https://une.org.br/feed/', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 8, 'prioridade': 1},
    {'nome': 'CUT', 'pais': 'Brasil', 'url': 'https://www.cut.org.br/feed', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 9, 'prioridade': 1},
    {'nome': 'Folha de S.Paulo', 'pais': 'Brasil', 'url': 'https://feeds.folha.uol.com.br/emcimadahora/rss.xml', 'categoria': 'geral', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 6, 'prioridade': 2},
    {'nome': 'O Globo', 'pais': 'Brasil', 'url': 'https://oglobo.globo.com/rss.xml', 'categoria': 'geral', 'idioma': 'pt', 'continente': 'America do Sul', 'confiabilidade': 6, 'prioridade': 2},
    
    # ===== PORTUGAL =====
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria': 'antifa', 'idioma': 'pt', 'continente': 'Europa', 'confiabilidade': 9, 'prioridade': 2},
    
    # ===== AMERICA LATINA =====
    {'nome': 'Pagina 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'America do Sul', 'confiabilidade': 8, 'prioridade': 2},
    {'nome': 'La Jornada', 'pais': 'Mexico', 'url': 'https://www.jornada.com.mx/rss', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'America do Norte', 'confiabilidade': 8, 'prioridade': 2},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria': 'antifa', 'idioma': 'es', 'continente': 'America do Sul', 'confiabilidade': 7, 'prioridade': 2},
    
    # ===== USA / INTERNACIONAL =====
    {'nome': 'Its Going Down', 'pais': 'USA', 'url': 'https://itsgoingdown.org/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'America do Norte', 'confiabilidade': 9, 'prioridade': 2},
    {'nome': 'CrimethInc', 'pais': 'Global', 'url': 'https://crimethinc.com/feeds/all.atom.xml', 'categoria': 'anarquista', 'idioma': 'en', 'continente': 'Global', 'confiabilidade': 9, 'prioridade': 2},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Global', 'confiabilidade': 9, 'prioridade': 2},
    {'nome': 'Democracy Now', 'pais': 'USA', 'url': 'https://www.democracynow.org/podcast.xml', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'America do Norte', 'confiabilidade': 9, 'prioridade': 2},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'America do Norte', 'confiabilidade': 8, 'prioridade': 2},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'America do Norte', 'confiabilidade': 9, 'prioridade': 2},
    {'nome': 'Common Dreams', 'pais': 'USA', 'url': 'https://www.commondreams.org/feed', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'America do Norte', 'confiabilidade': 8, 'prioridade': 2},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria': 'comunista', 'idioma': 'en', 'continente': 'America do Norte', 'confiabilidade': 8, 'prioridade': 2},
    
    # ===== UK / EUROPA =====
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 9, 'prioridade': 2},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 8, 'prioridade': 2},
    {'nome': 'Ceasefire Magazine', 'pais': 'UK', 'url': 'https://ceasefiremagazine.co.uk/feed/', 'categoria': 'antifa', 'idioma': 'en', 'continente': 'Europa', 'confiabilidade': 8, 'prioridade': 2},
    
    # ===== ORIENTE MEDIO =====
    {'nome': 'Al Jazeera', 'pais': 'Qatar', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Medio', 'confiabilidade': 8, 'prioridade': 2},
    {'nome': 'Middle East Eye', 'pais': 'UK', 'url': 'https://www.middleeasteye.net/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Medio', 'confiabilidade': 7, 'prioridade': 2},
    {'nome': 'Haaretz', 'pais': 'Israel', 'url': 'https://www.haaretz.com/rss', 'categoria': 'geopolitica', 'idioma': 'en', 'continente': 'Oriente Medio', 'confiabilidade': 7, 'prioridade': 2},
    
    # ===== ASIA =====
    {'nome': 'The Hindu', 'pais': 'India', 'url': 'https://www.thehindu.com/news/feeder', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Asia', 'confiabilidade': 7, 'prioridade': 3},
    {'nome': 'The Japan Times', 'pais': 'Japao', 'url': 'https://www.japantimes.co.jp/feed/', 'categoria': 'geral', 'idioma': 'en', 'continente': 'Asia', 'confiabilidade': 7, 'prioridade': 3},
]

# ============================================
# SISTEMA DE RADAR AUTOMATICO (SEM BOTAO)
# ============================================

@dataclass
class NoticiaAntifa:
    """Estrutura de dados para noticias"""
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
    horario_brasilia: str = field(default_factory=horario_brasilia)

class RadarAutomaticoAntifa:
    """Sistema de radar automatico com timer de 5 segundos"""
    
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
            'fontes_por_prioridade': {1: 0, 2: 0, 3: 0},
        }
        self.cache_resultados = {}
        self.fila_buscas = queue.Queue()
        self.radar_ativo = False
        self.thread_radar = None
        
    def iniciar_radar_automatico(self):
        """Inicia o radar automatico em background (SEM BOTAO)"""
        if self.radar_ativo:
            return
        
        self.radar_ativo = True
        self.thread_radar = threading.Thread(target=self._loop_radar)
        self.thread_radar.daemon = True
        self.thread_radar.start()
        logger.info("[Radar] RADAR AUTOMATICO INICIADO - 5 SEGUNDOS ENTRE FONTES")
    
    def _loop_radar(self):
        """Loop principal do radar (executa a cada 5 segundos)"""
        time.sleep(config.DELAY_INICIAL)
        
        while self.radar_ativo:
            try:
                self._executar_varredura_completa()
                time.sleep(config.TEMPO_ATUALIZACAO * 60)  # Espera minutos
            except Exception as e:
                logger.error(f"[Erro] no loop do radar: {e}")
                time.sleep(60)  # Espera 1 minuto em caso de erro
    
    def _executar_varredura_completa(self):
        """Executa varredura completa com timer de 5 segundos"""
        logger.info(f"\n{'='*60}")
        logger.info(f"[Radar] [{horario_brasilia()}] INICIANDO VARREDURA COMPLETA")
        logger.info(f"{'='*60}")
        
        # Ordena fontes por prioridade (primeiro as nacionais)
        fontes_ordenadas = sorted(FONTES_CONFIAVEIS, key=lambda x: x['prioridade'])
        
        noticias_antigas = self._carregar_noticias()
        links_antigos = {n.link for n in noticias_antigas}
        todas_noticias_novas = []
        
        total_fontes = len(fontes_ordenadas)
        processadas = 0
        fontes_ativas_temp = 0
        
        for fonte in fontes_ordenadas:
            processadas += 1
            logger.info(f"\n[Radar] [{processadas}/{total_fontes}] Processando: {fonte['nome']} ({fonte['pais']})")
            
            # TIMER DE 5 SEGUNDOS ENTRE CADA FONTE
            time.sleep(config.DELAY_ENTRE_REQUISICOES)
            
            # Seleciona palavras-chave para esta fonte
            palavras = self._selecionar_palavras_para_idioma(fonte['idioma'])
            
            # Processa a fonte
            noticias = self._processar_fonte(fonte, palavras, links_antigos)
            
            if noticias:
                todas_noticias_novas.extend(noticias)
                fontes_ativas_temp += 1
                self.fontes_ativas.append(fonte['nome'])
                self.estatisticas['fontes_funcionando'] += 1
                self.estatisticas['continentes'].add(fonte['continente'])
                self.estatisticas['paises'].add(fonte['pais'])
                self.estatisticas['categorias'][fonte['categoria']] += 1
                self.estatisticas['idiomas'][fonte['idioma']] += 1
                self.estatisticas['fontes_por_prioridade'][fonte['prioridade']] += 1
        
        # Atualiza estatisticas
        self.estatisticas['total_buscas'] += 1
        self.estatisticas['noticias_encontradas'] += len(todas_noticias_novas)
        
        # Salva noticias
        if todas_noticias_novas:
            todas_noticias = todas_noticias_novas + noticias_antigas
            todas_noticias.sort(key=lambda x: x.data, reverse=True)
            todas_noticias = todas_noticias[:config.MAX_NOTICIAS_TOTAL]
            
            # Marca destaques
            for i, n in enumerate(todas_noticias[:10]):
                n.destaque = True
            
            self._salvar_noticias(todas_noticias)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"[OK] VARREDURA CONCLUIDA - {horario_brasilia()}")
            logger.info(f"[Dados] RESULTADOS:")
            logger.info(f"  [Radar] Fontes ativas: {fontes_ativas_temp}")
            logger.info(f"  [Noticias] Novas: {len(todas_noticias_novas)}")
            logger.info(f"  [Continentes] {len(self.estatisticas['continentes'])}")
            logger.info(f"  [Paises] {len(self.estatisticas['paises'])}")
            logger.info(f"  [Brasil] Nacionais: {self.estatisticas['fontes_por_prioridade'][1]}")
            logger.info(f"  [Mundo] Internacionais: {self.estatisticas['fontes_por_prioridade'][2] + self.estatisticas['fontes_por_prioridade'][3]}")
            logger.info(f"{'='*60}")
        else:
            logger.info("[Info] Nenhuma noticia nova encontrada nesta varredura")
    
    def _processar_fonte(self, fonte, palavras, links_antigos):
        """Processa uma fonte individual com timer de 5 segundos"""
        noticias = []
        
        try:
            # Tenta com proxy se necessario
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
                        logger.debug(f"[Falha] {fonte['nome']} - status {response.status_code}")
                        return []
                        
                except Exception as e:
                    if tentativa == config.MAX_TENTATIVAS - 1:
                        logger.debug(f"[Falha] {fonte['nome']} - erro: {str(e)[:30]}")
                        return []
            
            # Parse do feed
            feed = feedparser.parse(response.content)
            
            if len(feed.entries) == 0:
                return []
            
            # Processa entradas
            for entrada in feed.entries[:config.MAX_NOTICIAS_POR_FONTE]:
                if entrada.link in links_antigos:
                    continue
                
                noticia = self._criar_noticia(fonte, entrada)
                if noticia:
                    # Verifica relevancia
                    relevancia = self._calcular_relevancia(noticia, palavras)
                    if relevancia > 0.2:  # 20% de relevancia minima
                        noticias.append(noticia)
                        
                        # Atualiza palavras-chave
                        for palavra in palavras:
                            if palavra.lower() in noticia.titulo.lower() or palavra.lower() in noticia.resumo.lower():
                                self.estatisticas['palavras_mais_usadas'][palavra] += 1
            
            logger.info(f"  [OK] {fonte['nome']} - {len(noticias)} noticias")
            
        except Exception as e:
            logger.debug(f"[Falha] Erro em {fonte['nome']}: {str(e)[:30]}")
        
        return noticias
    
    def _criar_noticia(self, fonte, entrada):
        """Cria objeto de noticia"""
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
            
            # Extrai autor
            autor = None
            if hasattr(entrada, 'author'):
                autor = entrada.author
            elif hasattr(entrada, 'creator'):
                autor = entrada.creator
            
            # Extrai imagem
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
            
            return NoticiaAntifa(
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
                publicada_em=horario_brasilia(),
                palavras_chave=[],
                confiabilidade=fonte['confiabilidade'],
                imagem=imagem,
                autor=autor,
                horario_brasilia=horario_brasilia()
            )
            
        except Exception as e:
            logger.debug(f"Erro ao criar noticia: {e}")
            return None
    
    def _selecionar_palavras_para_idioma(self, idioma):
        """Seleciona palavras-chave para um idioma especifico"""
        if idioma in PALAVRAS_CHAVE:
            palavras = PALAVRAS_CHAVE[idioma]
            return random.sample(palavras, min(config.MAX_PALAVRAS_POR_BUSCA, len(palavras)))
        return []
    
    def _selecionar_palavras_aleatorias(self):
        """Seleciona palavras-chave aleatorias de diferentes idiomas"""
        palavras_selecionadas = []
        idiomas = list(PALAVRAS_CHAVE.keys())
        
        for _ in range(config.MAX_PALAVRAS_POR_BUSCA):
            idioma = random.choice(idiomas)
            palavra = random.choice(PALAVRAS_CHAVE[idioma])
            palavras_selecionadas.append(palavra)
        
        return list(set(palavras_selecionadas))
    
    def _calcular_relevancia(self, noticia, palavras):
        """Calcula a relevancia da noticia baseada nas palavras-chave"""
        if not palavras:
            return 0.5
        
        texto_completo = (noticia.titulo + " " + noticia.resumo).lower()
        palavras_encontradas = 0
        
        for palavra in palavras:
            if palavra.lower() in texto_completo:
                palavras_encontradas += 1
        
        return palavras_encontradas / len(palavras) if palavras else 0
    
    def _carregar_noticias(self):
        """Carrega noticias do arquivo"""
        if os.path.exists(config.ARQUIVO_NOTICIAS):
            try:
                with open(config.ARQUIVO_NOTICIAS, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    noticias_dict = dados.get('noticias', [])
                    
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
    
    def _salvar_noticias(self, noticias):
        """Salva noticias no arquivo"""
        try:
            noticias_dict = [asdict(n) for n in noticias]
            
            with open(config.ARQUIVO_NOTICIAS, 'w', encoding='utf-8') as f:
                json.dump({
                    'noticias': noticias_dict,
                    'ultima_atualizacao': horario_brasilia(),
                    'total': len(noticias_dict),
                    'estatisticas': {
                        'continentes': list(self.estatisticas['continentes']),
                        'paises': list(self.estatisticas['paises']),
                        'categorias': dict(self.estatisticas['categorias']),
                        'idiomas': dict(self.estatisticas['idiomas']),
                        'palavras_mais_usadas': dict(self.estatisticas['palavras_mais_usadas'].most_common(30)),
                    },
                    'versao': '10.0 - FINAL',
                    'horario_brasilia': horario_brasilia(),
                }, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"[OK] Noticias salvas: {len(noticias)}")
            return True
        except Exception as e:
            logger.error(f"[Erro] ao salvar: {e}")
            return False

# ============================================
# INICIALIZACAO DO RADAR
# ============================================

radar = RadarAutomaticoAntifa()

# ============================================
# FUNCAO PARA PEGAR BANDEIRAS (TEXTO PURO)
# ============================================

def get_bandeira_texto(pais):
    """Retorna texto representando o pais (sem emojis)"""
    bandeiras_texto = {
        'Brasil': '[BR]',
        'Portugal': '[PT]',
        'Argentina': '[AR]',
        'Mexico': '[MX]',
        'Venezuela': '[VE]',
        'USA': '[US]',
        'UK': '[UK]',
        'Alemanha': '[DE]',
        'Franca': '[FR]',
        'Espanha': '[ES]',
        'Italia': '[IT]',
        'Canada': '[CA]',
        'Australia': '[AU]',
        'Japao': '[JP]',
        'China': '[CN]',
        'India': '[IN]',
        'Israel': '[IL]',
        'Qatar': '[QA]',
        'Global': '[GL]',
        'Africa do Sul': '[ZA]',
        'Quenia': '[KE]',
        'Congo': '[CG]',
        'Belgica': '[BE]',
        'Ira': '[IR]',
        'Emirados': '[AE]',
        'Singapura': '[SG]',
        'Coreia do Sul': '[KR]',
        'Hong Kong': '[HK]',
        'Nova Zelandia': '[NZ]',
        'America do Sul': '[SA]',
        'America do Norte': '[NA]',
        'Europa': '[EU]',
        'Asia': '[AS]',
        'Africa': '[AF]',
        'Oriente Medio': '[ME]',
        'Oceania': '[OC]',
    }
    return bandeiras_texto.get(pais, '[??]')

app = Flask(__name__)

# ============================================
# PAGINA PRINCIPAL - DESIGN SOFISTICADO (SEM EMOJIS)
# ============================================

@app.route('/')
def home():
    noticias = radar._carregar_noticias()
    
    # Separa por categoria
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    antifa = [n for n in noticias if n.categoria in ['antifa', 'anarquista', 'comunista']]
    nacionais = [n for n in noticias if n.pais == 'Brasil']
    internacionais = [n for n in noticias if n.pais != 'Brasil']
    destaques = [n for n in noticias if n.destaque][:8]
    
    # Estatisticas
    continentes = defaultdict(int)
    for n in noticias:
        continentes[n.continente] += 1
    
    # Palavras mais usadas
    palavras_stats = radar.estatisticas['palavras_mais_usadas'].most_common(15)
    
    # HTML dos destaques
    destaques_html = ''
    for n in destaques:
        bandeira = get_bandeira_texto(n.pais)
        destaques_html += f'''
        <div class="destaque-card">
            <span class="destaque-tag">[Destaque]</span>
            <div class="destaque-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="confiabilidade">{"*" * n.confiabilidade}{"+" * (10 - n.confiabilidade)}</span>
            </div>
            <h3>{n.titulo}</h3>
            <p class="destaque-resumo">{n.resumo[:150]}...</p>
            <div class="destaque-footer">
                <span class="data">[Hora] {n.data[:16]}</span>
                <a href="{n.link}" target="_blank" class="ler-mais">Ler artigo completo ></a>
            </div>
            <div class="horario-brasilia">[BR] {n.horario_brasilia if hasattr(n, 'horario_brasilia') else horario_brasilia()}</div>
        </div>
        '''
    
    # HTML Geopolitica
    geo_html = ''
    for n in geopolitica[:12]:
        bandeira = get_bandeira_texto(n.pais)
        geo_html += f'''
        <article class="noticia">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">[Hora] {n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="ler-link">[Link]</a>
            </div>
        </article>
        '''
    
    # HTML Antifa
    antifa_html = ''
    for n in antifa[:12]:
        bandeira = get_bandeira_texto(n.pais)
        antifa_html += f'''
        <article class="noticia antifa">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">[Hora] {n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="ler-link">[Link]</a>
            </div>
        </article>
        '''
    
    # HTML Nacionais
    nacional_html = ''
    for n in nacionais[:12]:
        bandeira = get_bandeira_texto(n.pais)
        nacional_html += f'''
        <article class="noticia nacional">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">[Hora] {n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="ler-link">[Link]</a>
            </div>
        </article>
        '''
    
    # HTML Internacionais
    internacional_html = ''
    for n in internacionais[:12]:
        bandeira = get_bandeira_texto(n.pais)
        internacional_html += f'''
        <article class="noticia internacional">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">[Hora] {n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="ler-link">[Link]</a>
            </div>
        </article>
        '''
    
    # HTML dos badges de continentes
    continentes_html = ''
    for cont, qtd in continentes.items():
        continentes_html += f'<span class="badge-continente">[{cont}]: {qtd}</span>'
    
    # HTML das palavras mais usadas
    palavras_html = ''
    for palavra, count in palavras_stats:
        palavras_html += f'<span class="badge-palavra">#{palavra} ({count})</span>'
    
    return f'''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Informacao antifascista - Nacional e Internacional - Horario de Brasilia">
        <meta name="keywords" content="antifa, antifascista, noticias, brasil, mundo, geopolitica">
        <meta name="author" content="SHARP - FRONT 16 RJ">
        <title>[Vermelho][Preto] SHARP - FRONT 16 RJ [Preto][Vermelho]</title>
        <style>
            /* RESET E ESTILOS GLOBAIS SOFISTICADOS */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
                background: #0a0a0a;
                color: #e0e0e0;
                line-height: 1.6;
            }}
            
            /* HEADER SUPREMO COM DUAS BOLAS ANIMADAS */
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
            
            .header::after {{
                content: '';
                position: absolute;
                bottom: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,0,0,0.1) 0%, transparent 70%);
                animation: rotate 40s linear infinite;
            }}
            
            @keyframes moveStripes {{
                0% {{ transform: translateX(0) translateY(0); }}
                100% {{ transform: translateX(50%) translateY(50%); }}
            }}
            
            @keyframes rotate {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            
            .bolas-container {{
                position: absolute;
                top: 30px;
                right: 40px;
                display: flex;
                gap: 25px;
                z-index: 10;
            }}
            
            .bola-vermelha {{
                width: 80px;
                height: 80px;
                background: #ff0000;
                border-radius: 50%;
                box-shadow: 0 0 50px rgba(255,0,0,0.8);
                animation: pulsar-vermelha 2.5s infinite ease-in-out;
            }}
            
            .bola-preta {{
                width: 80px;
                height: 80px;
                background: #000;
                border-radius: 50%;
                border: 3px solid #ff0000;
                box-shadow: 0 0 50px rgba(255,0,0,0.5);
                animation: pulsar-preta 3s infinite ease-in-out;
            }}
            
            @keyframes pulsar-vermelha {{
                0% {{ transform: scale(1); box-shadow: 0 0 50px rgba(255,0,0,0.8); }}
                50% {{ transform: scale(1.15); box-shadow: 0 0 80px rgba(255,0,0,1); }}
                100% {{ transform: scale(1); box-shadow: 0 0 50px rgba(255,0,0,0.8); }}
            }}
            
            @keyframes pulsar-preta {{
                0% {{ transform: scale(1); box-shadow: 0 0 40px rgba(255,0,0,0.4); }}
                50% {{ transform: scale(1.1); box-shadow: 0 0 70px rgba(255,0,0,0.8); }}
                100% {{ transform: scale(1); box-shadow: 0 0 40px rgba(255,0,0,0.4); }}
            }}
            
            h1 {{
                color: #ff0000;
                font-size: clamp(2.8rem, 8vw, 4.5rem);
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
                font-size: 1.4rem;
                margin-bottom: 30px;
                position: relative;
                z-index: 1;
                font-style: italic;
                border-top: 1px solid #ff0000;
                border-bottom: 1px solid #ff0000;
                padding: 15px 0;
                display: inline-block;
                background: rgba(0,0,0,0.5);
                backdrop-filter: blur(5px);
                border-radius: 50px;
                padding: 15px 40px;
            }}
            
            .horario-brasilia-header {{
                position: absolute;
                bottom: 15px;
                left: 30px;
                color: #888;
                font-size: 0.9rem;
                background: rgba(0,0,0,0.7);
                padding: 8px 20px;
                border-radius: 30px;
                border: 1px solid #ff0000;
                z-index: 10;
                animation: pulse-border 2s infinite;
            }}
            
            @keyframes pulse-border {{
                0% {{ border-color: #ff0000; }}
                50% {{ border-color: #ff6666; }}
                100% {{ border-color: #ff0000; }}
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
                transform: translateY(-5px);
                box-shadow: 0 15px 30px rgba(255,0,0,0.4);
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
                padding: 10px 25px;
                border-radius: 30px;
                font-size: 0.95rem;
                border: 1px solid #ff0000;
                animation: pulse 2s infinite;
            }}
            
            .badge-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 20px 0;
                justify-content: center;
            }}
            
            .badge-continente, .badge-palavra {{
                background: rgba(255,0,0,0.1);
                border: 1px solid #ff0000;
                padding: 8px 20px;
                border-radius: 30px;
                font-size: 0.9rem;
                transition: all 0.3s;
                backdrop-filter: blur(5px);
            }}
            
            .badge-continente:hover, .badge-palavra:hover {{
                background: #ff0000;
                color: #000;
                transform: scale(1.05);
                cursor: default;
            }}
            
            /* SECOES PRINCIPAIS */
            .secao {{
                max-width: 1400px;
                margin: 60px auto;
                padding: 0 20px;
            }}
            
            .secao-titulo {{
                color: #ff0000;
                font-size: 2.5rem;
                margin-bottom: 40px;
                display: flex;
                align-items: center;
                gap: 20px;
                border-left: 6px solid #ff0000;
                padding-left: 25px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .secao-titulo .badge {{
                background: #ff0000;
                color: #000;
                padding: 8px 25px;
                border-radius: 40px;
                font-size: 1.1rem;
                font-weight: bold;
            }}
            
            /* GRID DE DESTAQUES */
            .grid-destaques {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 35px;
                margin-top: 30px;
            }}
            
            .destaque-card {{
                background: linear-gradient(145deg, #111 0%, #1a0000 100%);
                border-radius: 25px;
                padding: 35px;
                position: relative;
                border: 1px solid #333;
                transition: all 0.4s;
                overflow: hidden;
                border-left: 5px solid #ff0000;
                border-right: 5px solid #000;
            }}
            
            .destaque-card::before {{
                content: '✊';
                position: absolute;
                bottom: -30px;
                right: -30px;
                font-size: 120px;
                opacity: 0.1;
                transform: rotate(-15deg);
            }}
            
            .destaque-card::after {{
                content: '⚡';
                position: absolute;
                top: -30px;
                left: -30px;
                font-size: 120px;
                opacity: 0.1;
                transform: rotate(15deg);
            }}
            
            .destaque-card:hover {{
                transform: translateY(-10px);
                border-color: #ff0000;
                box-shadow: 0 30px 50px rgba(255,0,0,0.3);
            }}
            
            .destaque-tag {{
                background: #ff0000;
                color: #000;
                padding: 8px 20px;
                border-radius: 30px;
                font-size: 0.95rem;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 25px;
            }}
            
            .destaque-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            
            .destaque-resumo {{
                color: #aaa;
                font-size: 1rem;
                margin: 20px 0;
                line-height: 1.7;
            }}
            
            .destaque-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 20px;
                margin-top: 20px;
            }}
            
            .horario-brasilia {{
                position: absolute;
                bottom: 15px;
                right: 15px;
                font-size: 0.7rem;
                color: #444;
                background: #0a0a0a;
                padding: 3px 10px;
                border-radius: 15px;
            }}
            
            /* GRID PRINCIPAL DE 4 COLUNAS */
            .grid-principal {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 35px;
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
            }}
            
            .coluna-especial {{
                background: rgba(17, 17, 17, 0.9);
                backdrop-filter: blur(10px);
                border-radius: 30px;
                padding: 35px;
                border: 1px solid #333;
                border-top: 4px solid #ff0000;
                border-bottom: 4px solid #000;
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
            
            .coluna-titulo .badge {{
                background: #ff0000;
                color: #000;
                padding: 5px 15px;
                border-radius: 25px;
                font-size: 0.9rem;
                margin-left: auto;
            }}
            
            .noticia {{
                background: #111;
                border-radius: 20px;
                padding: 25px;
                margin-bottom: 25px;
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
            
            .noticia.antifa {{
                border-left-color: #ff0000;
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
                letter-spacing: 1px;
            }}
            
            h4 {{
                font-size: 1.1rem;
                margin-bottom: 15px;
                line-height: 1.5;
                color: #fff;
            }}
            
            .resumo {{
                color: #aaa;
                font-size: 0.95rem;
                margin-bottom: 20px;
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
            
            .ler-link {{
                color: #ff0000;
                text-decoration: none;
                font-size: 1.1rem;
                transition: all 0.3s;
                padding: 5px 10px;
                border-radius: 5px;
            }}
            
            .ler-link:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            .ler-mais {{
                color: #ff0000;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s;
                padding: 8px 20px;
                border: 1px solid #ff0000;
                border-radius: 25px;
            }}
            
            .ler-mais:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            .mensagem-vazia {{
                text-align: center;
                padding: 80px 20px;
                color: #666;
                font-style: italic;
                background: #111;
                border-radius: 30px;
                border: 2px dashed #333;
            }}
            
            .loading-animation {{
                width: 50px;
                height: 50px;
                border: 3px solid #333;
                border-top-color: #ff0000;
                border-radius: 50%;
                animation: spin 1s infinite linear;
                margin: 20px auto;
            }}
            
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            
            /* AGRADECIMENTO SOFISTICADO */
            .agradecimento {{
                max-width: 900px;
                margin: 80px auto;
                padding: 50px;
                background: linear-gradient(145deg, #111, #1a0000);
                border-radius: 50px;
                border: 1px solid #333;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .agradecimento::before {{
                content: '✊';
                position: absolute;
                bottom: -40px;
                left: -40px;
                font-size: 180px;
                opacity: 0.1;
            }}
            
            .agradecimento::after {{
                content: '⚡';
                position: absolute;
                top: -40px;
                right: -40px;
                font-size: 180px;
                opacity: 0.1;
            }}
            
            .agradecimento p {{
                color: #ccc;
                font-size: 1.3rem;
                line-height: 1.9;
                font-style: italic;
                position: relative;
                z-index: 1;
            }}
            
            .assinatura {{
                color: #ff0000;
                font-weight: bold;
                margin-top: 40px;
                font-size: 1.8rem;
                letter-spacing: 3px;
                position: relative;
                z-index: 1;
            }}
            
            /* FOOTER SOFISTICADO */
            .footer {{
                background: #000;
                border-top: 4px solid #ff0000;
                padding: 70px 20px 40px;
                margin-top: 100px;
                text-align: center;
            }}
            
            .footer-stats {{
                display: flex;
                justify-content: center;
                gap: 40px;
                flex-wrap: wrap;
                margin-bottom: 50px;
                color: #888;
            }}
            
            .footer-stats span {{
                background: #111;
                padding: 10px 30px;
                border-radius: 40px;
                border: 1px solid #333;
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
                text-decoration: none;
                font-size: 0.95rem;
                padding: 8px 25px;
                border: 1px solid #333;
                border-radius: 30px;
                transition: all 0.3s;
            }}
            
            .footer-links a:hover {{
                background: #ff0000;
                color: #000;
                border-color: #ff0000;
            }}
            
            .footer-copyright {{
                color: #444;
                font-size: 0.8rem;
                max-width: 800px;
                margin: 30px auto 0;
            }}
            
            .footer-versao {{
                color: #222;
                font-size: 0.7rem;
                margin-top: 20px;
                letter-spacing: 2px;
            }}
            
            /* RESPONSIVIDADE */
            @media (max-width: 1200px) {{
                .grid-principal {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            @media (max-width: 900px) {{
                .grid-destaques {{
                    grid-template-columns: 1fr;
                }}
                
                .bolas-container {{
                    position: relative;
                    top: 0;
                    right: 0;
                    justify-content: center;
                    margin-bottom: 20px;
                }}
                
                .horario-brasilia-header {{
                    position: relative;
                    bottom: 0;
                    left: 0;
                    display: inline-block;
                    margin-top: 10px;
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
                
                .secao-titulo {{
                    font-size: 1.8rem;
                    flex-direction: column;
                    align-items: flex-start;
                }}
            }}
            
            /* UTILITARIOS */
            .pulse {{
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.7; }}
                100% {{ opacity: 1; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="bolas-container">
                <div class="bola-vermelha" title="Luta e Resistencia"></div>
                <div class="bola-preta" title="Antifascismo"></div>
            </div>
            
            <div class="horario-brasilia-header">
                [BR] {horario_brasilia()}
            </div>
            
            <h1>[Vermelho][Preto] SHARP - FRONT 16 RJ [Preto][Vermelho]</h1>
            <p class="subtitulo">[Info] INFORMACAO ANTIFASCISTA - NACIONAL E INTERNACIONAL</p>
            
            <div class="stats-supremas">
                <span class="stat-supremo">[Noticias] {len(noticias)}</span>
                <span class="stat-supremo">[Continentes] {len(radar.estatisticas['continentes'])}</span>
                <span class="stat-supremo">[Paises] {len(radar.estatisticas['paises'])}</span>
                <span class="stat-supremo">[Fontes] {radar.estatisticas['fontes_funcionando']}</span>
                <span class="stat-supremo">[Antifa] {len(antifa)}</span>
                <span class="stat-supremo">[Geopolitica] {len(geopolitica)}</span>
                <span class="stat-supremo">[Brasil] {len(nacionais)}</span>
                <span class="stat-supremo">[Mundo] {len(internacionais)}</span>
            </div>
            
            <div class="radar-info">
                <span class="radar-badge">[Radar] Ativo: {radar.estatisticas['fontes_funcionando']} fontes</span>
                <span class="radar-badge">[Idiomas] {len(radar.estatisticas['idiomas'])}</span>
                <span class="radar-badge">[Ultima] {hora_brasilia()}</span>
                <span class="radar-badge">[Timer] 5s entre fontes</span>
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
                [Destaques] DO RADAR ANTIFA
                <span class="badge">{len(destaques)} destaques</span>
            </div>
            
            if destaques_html:
    destaques_final = destaques_html
else:
    destaques_final = f'''
    <div class="mensagem-vazia">
        <div class="loading-animation"></div>
        <p>[Radar] em operacao... buscando informacoes antifascistas em {len(FONTES_CONFIAVEIS)} fontes globais</p>
        <p style="font-size: 0.9rem; margin-top: 20px;">[Timer] Aguarde 5 segundos entre cada fonte para maxima eficiencia</p>
    </div>
    '''
        
        <!-- GRID PRINCIPAL DE 4 COLUNAS -->
        <div class="grid-principal">
            <!-- COLUNA GEOPOLITICA -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    [Geopolitica] GUERRA
                    <span class="badge">{len(geopolitica)}</span>
                </div>
                {geo_html if geo_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>[Radar] Escaneando conflitos globais...</p></div>'}
            </div>
            
            <!-- COLUNA ANTIFA -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    [Antifa] MOVIMENTOS SOCIAIS
                    <span class="badge">{len(antifa)}</span>
                </div>
                {antifa_html if antifa_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>[Radar] Buscando movimentos sociais...</p></div>'}
            </div>
            
            <!-- COLUNA NACIONAL -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    [Brasil] NACIONAL
                    <span class="badge">{len(nacionais)}</span>
                </div>
                {nacional_html if nacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>[Radar] Buscando noticias nacionais...</p></div>'}
            </div>
            
            <!-- COLUNA INTERNACIONAL -->
            <div class="coluna-especial">
                <div class="coluna-titulo">
                    [Mundo] INTERNACIONAL
                    <span class="badge">{len(internacionais)}</span>
                </div>
                {internacional_html if internacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>[Radar] Buscando noticias internacionais...</p></div>'}
            </div>
        </div>
        
        <!-- AGRADECIMENTO ANTIFA -->
        <div class="agradecimento">
            <p>"A informacao e nossa arma mais poderosa contra o fascismo. Agradecemos a todos os antifascistas, anarquistas, comunistas e lutadores sociais que constroem um mundo sem opressao. A luta continua!"</p>
            <div class="assinatura">✊ [Preto][Vermelho] SHARP - FRONT 16 RJ [Vermelho][Preto]</div>
            <p style="margin-top: 30px; color: #ff0000; font-size: 1.1rem;">"Enquanto houver fascismo, havera antifascismo."</p>
            <p style="margin-top: 20px; color: #444; font-size: 0.8rem;">[BR] Horario de Brasilia: {horario_brasilia()}</p>
        </div>
        
        <!-- FOOTER -->
        <div class="footer">
            <div class="footer-stats">
                <span>[Radar] a cada {config.TEMPO_ATUALIZACAO} minutos</span>
                <span>[Timer] 5 segundos entre fontes</span>
                <span>[Links] originais</span>
                <span>[Acervo] {len(noticias)} noticias</span>
                <span>[Fontes] {radar.estatisticas['fontes_funcionando']} ativas</span>
            </div>
            
            <div class="footer-links">
                <a href="#">Sobre</a>
                <a href="#">Fontes</a>
                <a href="#">Contato</a>
                <a href="#">Privacidade</a>
                <a href="#">Manifesto</a>
                <a href="#">[BR] Horario Brasilia</a>
            </div>
            
            <div class="footer-copyright">
                [Vermelho][Preto] SHARP - FRONT 16 RJ - Informacao Antifascista - Nacional & Internacional
            </div>
            <div class="footer-copyright" style="color: #555;">
                Todos os links sao das fontes originais - Conteudo sob responsabilidade de cada veiculo
            </div>
            <div class="footer-versao">
                v10.0 - RADAR SUPREMO ANTIFA - Timer 5s - Horario Brasilia - {len(FONTES_CONFIAVEIS)} fontes - {sum(len(p) for p in PALAVRAS_CHAVE.values())} palavras-chave
            </div>
        </div>
    </body>
    </html>
    '''

# ============================================
# API DE ESTATISTICAS
# ============================================

@app.route('/api/stats')
def api_stats():
    noticias = radar._carregar_noticias()
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
        'paises': len(radar.estatisticas['paises']),
        'continentes': len(radar.estatisticas['continentes']),
        'fontes_ativas': radar.estatisticas['fontes_funcionando'],
        'fontes_nacionais': radar.estatisticas['fontes_por_prioridade'][1],
        'idiomas': len(radar.estatisticas['idiomas']),
        'ultima_atualizacao': horario_brasilia(),
        'hora_brasilia': hora_brasilia(),
        'timer_segundos': config.DELAY_ENTRE_REQUISICOES,
    })

# ============================================
# ROTA PARA DIAGNOSTICO (OPCIONAL)
# ============================================

@app.route('/diagnostico')
def diagnostico():
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>[Vermelho][Preto] Diagnostico do Radar</title>
        <style>
            body {{ background: black; color: white; font-family: monospace; padding: 20px; }}
            h1 {{ color: red; }}
            .info {{ background: #111; padding: 15px; margin: 10px 0; border-left: 3px solid red; }}
        </style>
    </head>
    <body>
        <h1>[Vermelho][Preto] RADAR SUPREMO - DIAGNOSTICO</h1>
        <div class="info">[Timer] Horario Brasilia: {horario_brasilia()}</div>
        <div class="info">[Timer] Timer entre fontes: {config.DELAY_ENTRE_REQUISICOES} segundos</div>
        <div class="info">[Fontes] Configuradas: {len(FONTES_CONFIAVEIS)}</div>
        <div class="info">[Palavras] Palavras-chave: {sum(len(p) for p in PALAVRAS_CHAVE.values())}</div>
        <div class="info">[Brasil] Nacionais (prioridade 1): {radar.estatisticas['fontes_por_prioridade'][1]}</div>
        <div class="info">[Mundo] Internacionais (prioridade 2-3): {radar.estatisticas['fontes_por_prioridade'][2] + radar.estatisticas['fontes_por_prioridade'][3]}</div>
        <div class="info">[Dados] Estatisticas do radar: {json.dumps(dict(radar.estatisticas['fontes_por_prioridade']), indent=2)}</div>
    </body>
    </html>
    '''

# ============================================
# INICIALIZACAO SUPREMA
# ============================================

def inicializar_supremo():
    """Inicializa o sistema supremo com radar automatico"""
    logger.info("="*70)
    logger.info("[Vermelho][Preto] SHARP - FRONT 16 RJ - RADAR SUPREMO ANTIFA v10.0 FINAL")
    logger.info("="*70)
    
    # Carrega cache
    cache = {}
    noticias = radar._carregar_noticias()
    logger.info(f"[Dados] Acervo inicial: {len(noticias)} noticias")
    logger.info(f"[Fontes] Configuradas: {len(FONTES_CONFIAVEIS)}")
    logger.info(f"[Palavras] Palavras-chave: {sum(len(p) for p in PALAVRAS_CHAVE.values())} em {len(PALAVRAS_CHAVE)} idiomas")
    logger.info(f"[Timer] Timer entre fontes: {config.DELAY_ENTRE_REQUISICOES} segundos")
    logger.info(f"[BR] Horario de Brasilia: {horario_brasilia()}")
    
    # INICIA O RADAR AUTOMATICAMENTE (SEM BOTAO)
    radar.iniciar_radar_automatico()
    logger.info("[OK] RADAR SUPREMO ATIVADO AUTOMATICAMENTE - 5 SEGUNDOS ENTRE FONTES")
    logger.info("="*70)

inicializar_supremo()

# ============================================
# FIM - NAO COLOQUE app.run() AQUI!
# ============================================
