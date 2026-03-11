#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SHARP - FRONT 16 RJ                                        ║
║              SISTEMA SUPREMO ANTIFA - VERSÃO 27.1 - INFINITY                 ║
║         RADAR AUTOMATICO COM FILTROS POR CATEGORIA - NOTÍCIAS EM PT          ║
║              "A informacao e nossa arma mais poderosa"                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from flask import Flask, jsonify, request, send_from_directory
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import queue
from urllib.parse import urlparse, quote_plus
import html
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CRIAÇÃO DO APP FLASK
# ============================================
app = Flask(__name__)

# ============================================
# CONTADOR DE VISITANTES (CORRIGIDO PARA RENDER)
# ============================================

class ContadorVisitantes:
    """Contador de visitas por IP - começa em 176 e vai ao infinito"""
    
    def __init__(self, arquivo='contador_visitas.json'):
        self.arquivo = arquivo
        self.visitas_unicas = set()
        self.total_visitas = 176  # COMEÇA EM 176 (conforme solicitado)
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados salvos"""
        if os.path.exists(self.arquivo):
            try:
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.visitas_unicas = set(dados.get('ips', []))
                    self.total_visitas = dados.get('total', 176)
                logger.info(f"[Contador] Carregado: {self.total_visitas} visitas, {len(self.visitas_unicas)} IPs únicos")
            except Exception as e:
                logger.error(f"[Contador] Erro ao carregar: {e}")
    
    def salvar_dados(self):
        """Salva dados no arquivo"""
        try:
            with open(self.arquivo, 'w', encoding='utf-8') as f:
                json.dump({
                    'ips': list(self.visitas_unicas),
                    'total': self.total_visitas,
                    'ultima_atualizacao': horario_brasilia()
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"[Contador] Salvo: {self.total_visitas} visitas")
        except Exception as e:
            logger.error(f"[Contador] Erro ao salvar: {e}")
    
    def get_ip_real(self):
        """Pega o IP real do visitante (funciona no Render)"""
        # Tenta pegar do cabeçalho X-Forwarded-For (usado em proxies)
        if request.headers.getlist("X-Forwarded-For"):
            # Pega o primeiro IP da lista (é o IP real do cliente)
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
            return ip
        # Fallback para remote_addr
        return request.remote_addr
    
    def registrar_visita(self):
        """Registra uma visita única usando IP real"""
        ip = self.get_ip_real()
        if ip and ip not in self.visitas_unicas and ip != '127.0.0.1' and not ip.startswith('10.'):
            self.visitas_unicas.add(ip)
            self.total_visitas += 1
            self.salvar_dados()
            logger.info(f"[Contador] Nova visita! Total: {self.total_visitas}")  # IP removido do log
            return True
        return False
    
    def get_total(self):
        """Retorna total de visitas"""
        return self.total_visitas

contador_visitas = ContadorVisitantes()

# ============================================
# TRADUTOR INTEGRADO (GOOGLE TRANSLATE)
# ============================================

class TradutorIntegrado:
    """Tradutor usando Google Translate (gratuito)"""
    
    @staticmethod
    def traduzir(texto, idioma_destino='pt'):
        """Traduz texto para português usando Google Translate"""
        if not texto or len(texto) < 10:
            return texto
        
        try:
            # URL do Google Translate (versão simples)
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': 'auto',
                'tl': idioma_destino,
                'dt': 't',
                'q': texto
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0 and len(result[0]) > 0:
                    return result[0][0][0]
        except Exception as e:
            logger.debug(f"Erro na tradução: {e}")
        
        return texto

tradutor = TradutorIntegrado()

# ============================================
# CONFIGURACOES
# ============================================

class Config:
    """Configuracoes avancadas do sistema"""
    
    NOME_SITE = "SHARP - FRONT 16 RJ"
    LEMA = "A informacao e nossa arma mais poderosa"
    
    ARQUIVO_NOTICIAS = 'noticias_salvas.json'
    ARQUIVO_CACHE = 'cache_fontes.json'
    ARQUIVO_HISTORICO = 'historico_buscas.json'
    ARQUIVO_LOG = 'radar_antifa.log'
    
    TEMPO_ATUALIZACAO = 10  # minutos
    TIMEOUT_REQUISICAO = 8  # segundos
    TIMEOUT_TOTAL = 30  # segundos
    DELAY_ENTRE_REQUISICOES = 5  # 5 segundos entre cada site
    DELAY_INICIAL = 2  # segundos antes de comecar
    
    MAX_NOTICIAS_POR_FONTE = 5
    MAX_NOTICIAS_TOTAL = 5000
    MAX_TRABALHADORES = 10
    MAX_TENTATIVAS = 2
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7,fr;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    TIMEZONE = -3  # Brasilia (UTC-3)

config = Config()

# ============================================
# FUNCAO PARA HORARIO DE BRASILIA
# ============================================

def horario_brasilia():
    """Retorna o horario atual de Brasilia"""
    utc = datetime.utcnow()
    brasilia = utc - timedelta(hours=3)
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
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(config.ARQUIVO_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ANTIFA-RADAR')

# ============================================
# PALAVRAS PROIBIDAS (FILTRO DE CASINO)
# ============================================

PALAVRAS_PROIBIDAS = [
    'casino', 'cassino', 'bet', 'aposta', 'gambling', 'poker', 'slot',
    'roulette', 'blackjack', 'baccarat', 'vegas', 'lottery', 'sweepstakes',
    'crypto', 'bitcoin', 'investimento', 'renda extra', 'ganhe dinheiro',
    'milagroso', 'segredo', 'fórmula', 'curso', 'download', 'gratis',
    'sexo', 'porn', 'onlyfans', 'hot', 'universitario', 'trabalhe em casa'
]

# ============================================
# SISTEMA DE PROXY
# ============================================

class ProxyManager:
    """Gerencia rotacao de proxies para evitar bloqueios"""
    
    def __init__(self):
        self.proxies = []
        self.blacklist = set()
        self.atualizar_lista()
    
    def atualizar_lista(self):
        try:
            fontes_proxy = [
                'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            ]
            
            for url in fontes_proxy:
                try:
                    response = requests.get(url, timeout=5, headers=config.HEADERS)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        for proxy in proxies:
                            proxy = proxy.strip()
                            if proxy and ':' in proxy and proxy not in self.blacklist:
                                self.proxies.append(proxy)
                except:
                    continue
            
            self.proxies = list(set(self.proxies))
            logger.info(f"[OK] Proxys carregados: {len(self.proxies)}")
            
        except Exception as e:
            logger.error(f"[Erro] ao carregar proxies: {e}")
    
    def obter_proxy(self):
        if self.proxies:
            proxy = random.choice(self.proxies)
            return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        return None

proxy_manager = ProxyManager()

# ============================================
# SISTEMA ANTI-SONO
# ============================================

class SistemaAntiSono:
    """Sistema que faz ping no próprio site para não dormir"""
    
    def __init__(self):
        self.ativo = True
        self.url_do_site = "https://sharp-front-16-rj.onrender.com"
        self.contador_pings = 0
        
    def iniciar(self):
        thread = threading.Thread(target=self._loop_ping)
        thread.daemon = True
        thread.start()
        logger.info("[Anti-Sono] Sistema ativado - Ping a cada 5 minutos")
    
    def _loop_ping(self):
        while self.ativo:
            try:
                response = requests.get(self.url_do_site, timeout=10)
                self.contador_pings += 1
                logger.info(f"[Anti-Sono] Ping #{self.contador_pings} - Status: {response.status_code}")
                requests.get(f"{self.url_do_site}/api/stats", timeout=5)
            except Exception as e:
                logger.error(f"[Anti-Sono] Erro no ping: {e}")
            time.sleep(300)

# ============================================
# FONTES CONFIÁVEIS (EXPANDIDO - 44 FONTES)
# ============================================

FONTES_CONFIAVEIS = [
    # BRASIL (EXPANDIDO)
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'The Intercept Brasil', 'pais': 'Brasil', 'url': 'https://theintercept.com/brasil/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Brasil 247', 'pais': 'Brasil', 'url': 'https://www.brasil247.com/feed', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Diário do Centro do Mundo', 'pais': 'Brasil', 'url': 'https://www.diariodocentrodomundo.com.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Revista Fórum', 'pais': 'Brasil', 'url': 'https://revistaforum.com.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Jornal GGN', 'pais': 'Brasil', 'url': 'https://jornalggn.com.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Conversa Afiada', 'pais': 'Brasil', 'url': 'https://conversaafiada.com.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    
    # PORTUGAL
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria': 'antifa', 'continente': 'Europa'},
    {'nome': 'Público', 'pais': 'Portugal', 'url': 'https://feeds.feedburner.com/PublicoRSS', 'categoria': 'geopolitica', 'continente': 'Europa'},
    
    # AMÉRICA LATINA
    {'nome': 'Pagina 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'La Jornada', 'pais': 'Mexico', 'url': 'https://www.jornada.com.mx/rss', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria': 'geopolitica', 'continente': 'America do Sul'},
    {'nome': 'El País América', 'pais': 'Espanha', 'url': 'https://elpais.com/america/feed/', 'categoria': 'geopolitica', 'continente': 'Europa'},
    {'nome': 'Resumen Latinoamericano', 'pais': 'Argentina', 'url': 'https://www.resumenlatinoamericano.org/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'La Izquierda Diario', 'pais': 'Mexico', 'url': 'https://www.laizquierdadiario.mx/feed', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'ANRed', 'pais': 'Argentina', 'url': 'https://www.anred.org/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    
    # USA / INTERNACIONAL
    {'nome': 'Its Going Down', 'pais': 'USA', 'url': 'https://itsgoingdown.org/feed/', 'categoria': 'anarquista', 'continente': 'America do Norte'},
    {'nome': 'CrimethInc', 'pais': 'Global', 'url': 'https://crimethinc.com/feeds/all.atom.xml', 'categoria': 'anarquista', 'continente': 'Global'},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria': 'antifa', 'continente': 'Global'},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria': 'comunista', 'continente': 'America do Norte'},
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    {'nome': 'Common Dreams', 'pais': 'USA', 'url': 'https://www.commondreams.org/feed', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'MintPress News', 'pais': 'USA', 'url': 'https://www.mintpressnews.com/feed', 'categoria': 'geopolitica', 'continente': 'America do Norte'},
    {'nome': 'Antiwar.com', 'pais': 'USA', 'url': 'https://antiwar.com/feed/', 'categoria': 'geopolitica', 'continente': 'America do Norte'},
    {'nome': 'Black Agenda Report', 'pais': 'USA', 'url': 'https://blackagendareport.com/feed', 'categoria': 'antifa', 'continente': 'America do Norte'},
    
    # ORIENTE MÉDIO / ÁFRICA
    {'nome': 'Al Jazeera', 'pais': 'Qatar', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
    {'nome': 'Middle East Eye', 'pais': 'UK', 'url': 'https://www.middleeasteye.net/rss', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
    {'nome': 'The Palestine Chronicle', 'pais': 'Palestina', 'url': 'https://www.palestinechronicle.com/feed/', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
    {'nome': 'Mondoweiss', 'pais': 'USA', 'url': 'https://mondoweiss.net/feed/', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
    {'nome': 'Electronic Intifada', 'pais': 'Palestina', 'url': 'https://electronicintifada.net/rss.xml', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
    
    # EUROPA
    {'nome': 'Le Monde Diplomatique', 'pais': 'França', 'url': 'https://mondediplo.com/feed', 'categoria': 'geopolitica', 'continente': 'Europa'},
    {'nome': 'The Canary', 'pais': 'UK', 'url': 'https://www.thecanary.co/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    {'nome': 'Red Pepper', 'pais': 'UK', 'url': 'https://www.redpepper.org.uk/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    {'nome': 'Ceasefire Magazine', 'pais': 'UK', 'url': 'https://ceasefiremagazine.co.uk/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    
    # ÁSIA / OCEANIA
    {'nome': 'Green Left', 'pais': 'Australia', 'url': 'https://www.greenleft.org.au/feed', 'categoria': 'antifa', 'continente': 'Oceania'},
    {'nome': 'Peoples Dispatch', 'pais': 'India', 'url': 'https://peoplesdispatch.org/feed/', 'categoria': 'antifa', 'continente': 'Asia'},
]

# TOTAL: 44 FONTES

# ============================================
# SCRAPER DO GLINT.TRADE (SEM CITAR)
# ============================================

class GlintTradeScraper:
    """Scraper do Glint Trade - aparece como 'Análise Global' sem mencionar a fonte"""
    
    def __init__(self):
        self.url_base = "https://glint.trade"
        self.ultima_busca = None
        
    def buscar_noticias(self):
        """Busca notícias do Glint Trade e transforma"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'pt-BR,pt;q=0.9'
            }
            
            response = requests.get(self.url_base, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tenta encontrar notícias/títulos
            titulos = []
            
            # Procura por tags comuns de título
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                texto = tag.get_text().strip()
                if texto and len(texto) > 15 and len(texto) < 100:
                    # Filtra palavras genéricas
                    palavras_proibidas = ['menu', 'login', 'sign', 'register', 'cookie']
                    if not any(p in texto.lower() for p in palavras_proibidas):
                        titulos.append(texto)
            
            # Procura por links
            for link in soup.find_all('a', href=True):
                texto = link.get_text().strip()
                href = link['href']
                if texto and len(texto) > 15 and len(texto) < 80:
                    if not texto.lower().startswith(('login', 'sign', 'menu')):
                        # Constrói URL completa
                        if href.startswith('/'):
                            href = self.url_base + href
                        elif not href.startswith('http'):
                            href = self.url_base + '/' + href
                        
                        titulos.append({
                            'texto': texto,
                            'link': href
                        })
            
            # Se encontrou títulos, transforma em notícias
            noticias_glint = []
            for item in titulos[:10]:  # Pega os 10 primeiros
                if isinstance(item, str):
                    titulo = item
                    link = self.url_base
                else:
                    titulo = item['texto']
                    link = item['link']
                
                # Categoriza automaticamente
                categoria = self._categorizar_titulo(titulo)
                
                noticias_glint.append({
                    'titulo': titulo,
                    'titulo_traduzido': tradutor.traduzir(titulo),
                    'link': link,
                    'categoria': categoria,
                    'fonte_original': 'Análise Global'  # NÃO MENCIONA GLINT
                })
            
            logger.info(f"[Glint] Encontradas {len(noticias_glint)} notícias (anonimizado)")
            return noticias_glint
            
        except Exception as e:
            logger.debug(f"[Glint] Erro na busca: {e}")
            return []
    
    def _categorizar_titulo(self, titulo):
        """Categoriza o título automaticamente"""
        titulo_lower = titulo.lower()
        
        if any(p in titulo_lower for p in ['rússia', 'russia', 'ucrânia', 'ukraine', 'guerra', 'war', 'conflito']):
            return 'geopolitica'
        elif any(p in titulo_lower for p in ['economia', 'economy', 'mercado', 'market', 'finance']):
            return 'economia'
        elif any(p in titulo_lower for p in ['brasil', 'brazil', 'lula', 'bolsonaro', 'congresso']):
            return 'nacional'
        elif any(p in titulo_lower for p in ['china', 'eua', 'us', 'estados unidos', 'europa', 'europe']):
            return 'geopolitica'
        else:
            return 'internacional'

glint_scraper = GlintTradeScraper()

# ============================================
# SISTEMA DE RADAR
# ============================================

@dataclass
class Noticia:
    """Estrutura de dados para noticias"""
    id: str
    fonte: str
    pais: str
    continente: str
    categoria: str
    titulo: str
    titulo_original: str
    resumo: str
    resumo_original: str
    link: str
    data: str
    publicada_em: str
    destaque: bool = False

class RadarAutomatico:
    """Sistema de radar automatico"""
    
    def __init__(self):
        self.fontes_ativas = []
        self.estatisticas = {
            'fontes_funcionando': 0,
            'continentes': set(),
            'paises': set(),
            'categorias': defaultdict(int),
        }
        self.radar_ativo = False
        
    def iniciar_radar_automatico(self):
        if self.radar_ativo:
            return
        self.radar_ativo = True
        thread = threading.Thread(target=self._loop_radar)
        thread.daemon = True
        thread.start()
        logger.info("[Radar] Radar automatico iniciado")
    
    def _loop_radar(self):
        time.sleep(config.DELAY_INICIAL)
        while self.radar_ativo:
            try:
                self._executar_varredura()
                time.sleep(config.TEMPO_ATUALIZACAO * 60)
            except Exception as e:
                logger.error(f"[Erro] no radar: {e}")
                time.sleep(60)
    
    def _executar_varredura(self):
        logger.info(f"\n{'='*60}")
        logger.info(f"[Radar] [{horario_brasilia()}] Iniciando varredura em 44 fontes + Glint")
        logger.info(f"{'='*60}")
        
        noticias_antigas = self._carregar_noticias()
        links_antigos = {n.link for n in noticias_antigas}
        todas_noticias_novas = []
        
        # ===== BUSCA NAS FONTES RSS =====
        for fonte in FONTES_CONFIAVEIS:
            time.sleep(config.DELAY_ENTRE_REQUISICOES)
            try:
                response = requests.get(fonte['url'], headers=config.HEADERS, timeout=config.TIMEOUT_REQUISICAO)
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    if len(feed.entries) > 0:
                        noticias_fonte = []
                        for entrada in feed.entries[:config.MAX_NOTICIAS_POR_FONTE]:
                            if entrada.link in links_antigos:
                                continue
                            titulo_lower = entrada.title.lower()
                            palavra_proibida = False
                            for palavra in PALAVRAS_PROIBIDAS:
                                if palavra in titulo_lower:
                                    palavra_proibida = True
                                    break
                            if palavra_proibida:
                                continue
                            noticia = self._criar_noticia(fonte, entrada)
                            if noticia:
                                noticias_fonte.append(noticia)
                        
                        if noticias_fonte:
                            todas_noticias_novas.extend(noticias_fonte)
                            self.fontes_ativas.append(fonte['nome'])
                            self.estatisticas['fontes_funcionando'] += 1
                            self.estatisticas['continentes'].add(fonte['continente'])
                            self.estatisticas['paises'].add(fonte['pais'])
                            self.estatisticas['categorias'][fonte['categoria']] += 1
                            logger.info(f"  [OK] {fonte['nome']}: {len(noticias_fonte)} noticias")
            except Exception as e:
                logger.debug(f"  [Falha] {fonte['nome']}")
        
        # ===== BUSCA NO GLINT.TRADE (ANONIMIZADO) =====
        try:
            noticias_glint = glint_scraper.buscar_noticias()
            for item in noticias_glint:
                if item['link'] in links_antigos:
                    continue
                
                # Cria noticia a partir do Glint
                noticia = Noticia(
                    id=hashlib.md5(item['link'].encode()).hexdigest()[:8],
                    fonte='Análise Global',  # NÃO MENCIONA GLINT
                    pais='Global',
                    continente='Global',
                    categoria=item['categoria'],
                    titulo=item['titulo_traduzido'],
                    titulo_original=item['titulo'],
                    resumo=f"Análise aprofundada sobre {item['titulo_traduzido'][:50]}... Clique para ler o conteúdo completo.",
                    resumo_original=item['titulo'],
                    link=item['link'],
                    data=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    publicada_em=horario_brasilia()
                )
                todas_noticias_novas.append(noticia)
                logger.info(f"  [OK] Análise Global: +1 notícia")
        except Exception as e:
            logger.debug(f"  [Falha] Análise Global")
        
        if todas_noticias_novas:
            todas_noticias = todas_noticias_novas + noticias_antigas
            todas_noticias.sort(key=lambda x: x.data, reverse=True)
            todas_noticias = todas_noticias[:config.MAX_NOTICIAS_TOTAL]
            for i, n in enumerate(todas_noticias[:5]):
                n.destaque = True
            self._salvar_noticias(todas_noticias)
            logger.info(f"\n[OK] Varredura concluida")
            logger.info(f"  Fontes ativas: {self.estatisticas['fontes_funcionando']}")
            logger.info(f"  Noticias novas: {len(todas_noticias_novas)}")
            logger.info(f"  Total: {len(todas_noticias)}")
    
    def _criar_noticia(self, fonte, entrada):
        try:
            titulo_original = entrada.title
            titulo_traduzido = tradutor.traduzir(titulo_original)
            
            # ===== EXTRAIR RESUMO DE MÚLTIPLAS FONTES =====
            resumo_original = ""
            
            # Tenta extrair de summary
            if hasattr(entrada, 'summary') and entrada.summary:
                resumo_original = BeautifulSoup(entrada.summary, 'html.parser').get_text()
            
            # Se não tem summary, tenta description
            elif hasattr(entrada, 'description') and entrada.description:
                resumo_original = BeautifulSoup(entrada.description, 'html.parser').get_text()
            
            # Se não tem description, tenta content
            elif hasattr(entrada, 'content') and entrada.content:
                for content in entrada.content:
                    if content.get('type') == 'text/html' and content.value:
                        resumo_original = BeautifulSoup(content.value, 'html.parser').get_text()
                        if resumo_original:
                            break
            
            # Se ainda não tem resumo, usa o título ou uma mensagem padrão
            if not resumo_original or len(resumo_original.strip()) < 20:
                resumo_original = f"Leia o artigo completo sobre: {titulo_original[:100]}..."
            
            # Traduz o resumo
            resumo_traduzido = tradutor.traduzir(resumo_original) if resumo_original else ""
            
            # Limita o tamanho e adiciona reticências
            if resumo_traduzido and len(resumo_traduzido) > 200:
                resumo_traduzido = resumo_traduzido[:200] + "..."
            elif not resumo_traduzido:
                resumo_traduzido = "Clique para ler o artigo completo sobre esta notícia."
            
            return Noticia(
                id=hashlib.md5(entrada.link.encode()).hexdigest()[:8],
                fonte=fonte['nome'],
                pais=fonte['pais'],
                continente=fonte['continente'],
                categoria=fonte['categoria'],
                titulo=titulo_traduzido,
                titulo_original=titulo_original,
                resumo=resumo_traduzido,
                resumo_original=resumo_original[:200] + "..." if resumo_original and len(resumo_original) > 200 else resumo_original,
                link=entrada.link,
                data=entrada.get('published', datetime.now().strftime('%Y-%m-%d %H:%M')),
                publicada_em=horario_brasilia()
            )
        except Exception as e:
            logger.debug(f"Erro ao criar noticia: {e}")
            return None
    
    def _carregar_noticias(self):
        if os.path.exists(config.ARQUIVO_NOTICIAS):
            try:
                with open(config.ARQUIVO_NOTICIAS, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    noticias_dict = dados.get('noticias', [])
                    noticias = []
                    for n in noticias_dict:
                        try:
                            noticias.append(Noticia(**n))
                        except:
                            pass
                    return noticias
            except:
                return []
        return []
    
    def _salvar_noticias(self, noticias):
        try:
            noticias_dict = [asdict(n) for n in noticias]
            with open(config.ARQUIVO_NOTICIAS, 'w', encoding='utf-8') as f:
                json.dump({
                    'noticias': noticias_dict,
                    'ultima_atualizacao': horario_brasilia(),
                    'total': len(noticias_dict)
                }, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"[Erro] ao salvar: {e}")
            return False

radar = RadarAutomatico()

# ============================================
# FUNCAO PARA BANDEIRA
# ============================================

def get_bandeira(pais):
    bandeiras = {
        'Brasil': '🇧🇷',
        'Portugal': '🇵🇹',
        'Argentina': '🇦🇷',
        'Mexico': '🇲🇽',
        'Venezuela': '🇻🇪',
        'USA': '🇺🇸',
        'UK': '🇬🇧',
        'Qatar': '🇶🇦',
        'Palestina': '🇵🇸',
        'França': '🇫🇷',
        'Espanha': '🇪🇸',
        'Australia': '🇦🇺',
        'India': '🇮🇳',
        'Global': '🌍',
        'Oriente Medio': '🕌',
        'Europa': '🇪🇺',
        'Asia': '🌏',
        'Oceania': '🌏',
        'America do Sul': '🌎',
        'America do Norte': '🌎',
    }
    return bandeiras.get(pais, '🏴')

# ============================================
# ROTAS
# ============================================

@app.route('/qr-code.png')
def serve_qr_code():
    return send_from_directory('.', 'qr-code.png')

@app.route('/ping')
def ping():
    return jsonify({
        'status': 'ok',
        'horario': horario_brasilia(),
        'mensagem': 'Sistema anti-sono ativo'
    })

# ============================================
# PAGINA PRINCIPAL
# ============================================

@app.route('/')
def home():
    # Registra a visita (agora funcionando no Render)
    contador_visitas.registrar_visita()
    total_visitas = contador_visitas.get_total()
    
    noticias = radar._carregar_noticias()
    
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    antifa = [n for n in noticias if n.categoria in ['antifa', 'anarquista', 'comunista']]
    nacionais = [n for n in noticias if n.pais == 'Brasil']
    internacionais = [n for n in noticias if n.pais != 'Brasil']
    destaques = [n for n in noticias if n.destaque][:5]
    
    destaques_html = ''
    for n in destaques:
        bandeira = get_bandeira(n.pais)
        destaques_html += f'''
        <div class="destaque-card" data-categoria="{n.categoria}" data-pais="{n.pais}">
            <span class="destaque-tag">⭐ DESTAQUE</span>
            <div class="destaque-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="tooltip" title="Original: {html.escape(n.titulo_original)}">🔤</span>
            </div>
            <h3>{n.titulo}</h3>
            <p class="resumo">{n.resumo[:150]}...</p>
            <div class="destaque-footer">
                <span class="data">🕒 {n.data[:16]}</span>
                <a href="{n.link}" target="_blank" class="botao">Ler mais →</a>
            </div>
        </div>
        '''
    
    if destaques_html:
        destaques_conteudo = destaques_html
    else:
        destaques_conteudo = f'''
        <div class="mensagem-vazia">
            <div class="loading-animation"></div>
            <p>🔍 Radar em operacao... buscando informacoes em {len(FONTES_CONFIAVEIS)} fontes</p>
        </div>
        '''
    
    geo_html = ''
    for n in geopolitica[:12]:
        bandeira = get_bandeira(n.pais)
        geo_html += f'''
        <div class="noticia" data-categoria="geopolitica" data-pais="{n.pais}">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
                <span class="tooltip" title="Original: {html.escape(n.titulo_original)}">🔤</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="link">🔗</a>
            </div>
        </div>
        '''
    
    antifa_html = ''
    for n in antifa[:12]:
        bandeira = get_bandeira(n.pais)
        antifa_html += f'''
        <div class="noticia antifa" data-categoria="antifa" data-pais="{n.pais}">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
                <span class="tooltip" title="Original: {html.escape(n.titulo_original)}">🔤</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="link">🔗</a>
            </div>
        </div>
        '''
    
    nacional_html = ''
    for n in nacionais[:12]:
        bandeira = get_bandeira(n.pais)
        nacional_html += f'''
        <div class="noticia nacional" data-categoria="{n.categoria}" data-pais="Brasil">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">NACIONAL</span>
                <span class="tooltip" title="Original: {html.escape(n.titulo_original)}">🔤</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="link">🔗</a>
            </div>
        </div>
        '''
    
    internacional_html = ''
    for n in internacionais[:12]:
        bandeira = get_bandeira(n.pais)
        internacional_html += f'''
        <div class="noticia internacional" data-categoria="{n.categoria}" data-pais="{n.pais}">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
                <span class="tooltip" title="Original: {html.escape(n.titulo_original)}">🔤</span>
            </div>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:120]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank" class="link">🔗</a>
            </div>
        </div>
        '''
    
    continentes_html = ''
    for cont in radar.estatisticas['continentes']:
        continentes_html += f'<span class="tag">{cont}</span>'
    
    return f'''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="Informação antifascista - Nacional e Internacional">
        <meta name="keywords" content="antifa, antifascista, notícias, brasil, mundo, geopolítica">
        <meta name="author" content="SHARP - FRONT 16 RJ">
        <title>SHARP - FRONT 16 RJ</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Roboto, Arial, sans-serif;
                background: #0a0a0a;
                color: #e0e0e0;
                line-height: 1.6;
            }}
            
            .header {{
                background: linear-gradient(135deg, #000000 0%, #2a0000 70%, #000000 100%);
                border-bottom: 4px solid #ff0000;
                padding: 30px 20px 40px;
                text-align: center;
                position: relative;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(255,0,0,0.3);
                min-height: 180px;
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
                    transparent 15px,
                    rgba(255,0,0,0.03) 15px,
                    rgba(255,0,0,0.03) 30px
                );
                animation: moveStripes 30s linear infinite;
            }}
            
            @keyframes moveStripes {{
                0% {{ transform: translateX(0) translateY(0); }}
                100% {{ transform: translateX(50%) translateY(50%); }}
            }}
            
            .qr-code-container {{
                position: absolute;
                top: 20px;
                left: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
                z-index: 20;
                background: rgba(0,0,0,0.7);
                padding: 10px;
                border-radius: 12px;
                border: 1px solid #ff0000;
                max-width: 140px;
                backdrop-filter: blur(5px);
            }}
            
            .qr-code-container img {{
                width: 80px;
                height: 80px;
                display: block;
                border-radius: 8px;
                margin-bottom: 6px;
                border: 2px solid #ff0000;
            }}
            
            .qr-code-container p {{
                color: #ff0000;
                font-size: 0.7rem;
                text-align: center;
                line-height: 1.2;
                margin: 0;
            }}
            
            .qr-code-container p small {{
                color: #fff;
                font-size: 0.6rem;
                display: block;
                margin-top: 3px;
            }}
            
            .contador-header {{
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(0,0,0,0.5);
                backdrop-filter: blur(5px);
                padding: 5px 12px;
                border-radius: 20px;
                border: 1px solid #ff0000;
                z-index: 20;
                font-size: 0.85rem;
                color: #ccc;
            }}
            
            .numero-contador {{
                color: #ff0000;
                font-weight: bold;
                margin-left: 3px;
            }}
            
            .titulo-container {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 5px;
                margin-bottom: 5px;
                flex-wrap: nowrap;
                white-space: nowrap;
            }}
            
            .simbolo-anarquista {{
                color: #ff0000;
                font-size: 2.2rem;
                filter: drop-shadow(0 0 5px rgba(255,0,0,0.5));
                line-height: 1;
                display: inline-block;
                flex-shrink: 0;
            }}
            
            .simbolo-comunista {{
                color: #ff0000;
                font-size: 2.8rem;
                filter: drop-shadow(0 0 5px rgba(255,0,0,0.5));
                line-height: 1;
                display: inline-block;
                transform: translateY(2px);
                flex-shrink: 0;
                margin-left: -5px;
            }}
            
            .titulo-vermelho {{
                color: #ff0000;
                font-size: clamp(1.5rem, 4vw, 2.5rem);
                font-weight: 900;
                letter-spacing: 2px;
                text-shadow: 2px 2px 0px #000;
                white-space: nowrap;
            }}
            
            .separador {{
                color: #ff0000;
                font-size: clamp(1.5rem, 4vw, 2.5rem);
                font-weight: 900;
                flex-shrink: 0;
            }}
            
            .titulo-branco {{
                color: #ffffff;
                font-size: clamp(1.2rem, 3.5vw, 2rem);
                font-weight: 700;
                margin-top: 5px;
                text-shadow: 1px 1px 0px #ff0000;
            }}
            
            .horario-header {{
                position: absolute;
                bottom: 10px;
                right: 20px;
                color: #888;
                font-size: 0.8rem;
                background: rgba(0,0,0,0.7);
                padding: 4px 12px;
                border-radius: 20px;
                border: 1px solid #ff0000;
                z-index: 10;
            }}
            
            .tooltip {{
                cursor: help;
                font-size: 0.8rem;
                opacity: 0.7;
                transition: opacity 0.3s;
            }}
            
            .tooltip:hover {{
                opacity: 1;
            }}
            
            .filtros-container {{
                display: flex;
                justify-content: center;
                gap: 10px;
                flex-wrap: wrap;
                margin: 20px 0 15px;
                position: relative;
                z-index: 1;
            }}
            
            .filtro-btn {{
                background: rgba(0,0,0,0.7);
                backdrop-filter: blur(10px);
                border: 1px solid #ff0000;
                padding: 6px 15px;
                border-radius: 30px;
                font-size: 0.85rem;
                font-weight: 500;
                transition: all 0.3s;
                box-shadow: 0 3px 8px rgba(255,0,0,0.2);
                cursor: pointer;
                color: #e0e0e0;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }}
            
            .filtro-btn:hover {{
                background: #ff0000;
                color: #000;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(255,0,0,0.4);
            }}
            
            .filtro-btn.ativo {{
                background: transparent;
                color: #ffffff;
                border-color: #ff0000;
            }}
            
            .filtro-btn .contador {{
                background: rgba(0,0,0,0.3);
                border-radius: 15px;
                padding: 2px 6px;
                font-size: 0.7rem;
            }}
            
            .filtro-btn.ativo .contador {{
                background: rgba(0,0,0,0.5);
                color: #fff;
            }}
            
            .tag-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin: 15px 0;
                justify-content: center;
            }}
            
            .tag {{
                background: rgba(255,0,0,0.1);
                border: 1px solid #ff0000;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.75rem;
            }}
            
            .secao {{
                max-width: 1400px;
                margin: 40px auto;
                padding: 0 15px;
            }}
            
            .secao-titulo {{
                color: #ff0000;
                font-size: 1.8rem;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                border-left: 4px solid #ff0000;
                padding-left: 15px;
            }}
            
            .secao-titulo .badge {{
                background: #ff0000;
                color: #000;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.9rem;
            }}
            
            .destaques-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            
            .destaque-card {{
                background: linear-gradient(145deg, #111, #1a0000);
                border-radius: 15px;
                padding: 20px;
                position: relative;
                border: 1px solid #333;
                transition: all 0.4s;
                overflow: hidden;
                border-left: 4px solid #ff0000;
                box-shadow: 0 8px 15px rgba(0,0,0,0.3);
            }}
            
            .destaque-card::before {{
                content: '✊';
                position: absolute;
                bottom: -15px;
                right: -15px;
                font-size: 60px;
                opacity: 0.1;
                transform: rotate(-10deg);
            }}
            
            .destaque-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 25px rgba(255,0,0,0.2);
            }}
            
            .destaque-tag {{
                background: #ff0000;
                color: #000;
                padding: 3px 10px;
                border-radius: 15px;
                font-size: 0.7rem;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 12px;
            }}
            
            .destaque-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                font-size: 0.8rem;
            }}
            
            .destaque-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 12px;
                margin-top: 12px;
            }}
            
            .grid-principal {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 15px;
            }}
            
            .coluna {{
                background: rgba(17, 17, 17, 0.9);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid #333;
                border-top: 3px solid #ff0000;
            }}
            
            .coluna h2 {{
                color: #ff0000;
                font-size: 1.5rem;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 8px;
                padding-bottom: 8px;
                border-bottom: 1px solid #ff0000;
            }}
            
            .coluna h2 .badge {{
                background: #ff0000;
                color: #000;
                padding: 2px 10px;
                border-radius: 15px;
                font-size: 0.8rem;
                margin-left: auto;
            }}
            
            .noticia {{
                background: #111;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
                border-left: 3px solid #ff0000;
                transition: all 0.3s;
            }}
            
            .noticia:hover {{
                transform: translateX(3px);
                background: #1a1a1a;
            }}
            
            .noticia.nacional {{
                border-left-color: #00cc00;
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
                margin-bottom: 8px;
                font-size: 0.8rem;
                flex-wrap: wrap;
                gap: 5px;
            }}
            
            .fonte {{
                color: #ff0000;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 0.75rem;
            }}
            
            .pais {{
                color: #888;
                background: #1a1a1a;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
            }}
            
            h4 {{
                font-size: 0.95rem;
                margin-bottom: 10px;
                line-height: 1.4;
                color: #fff;
            }}
            
            .resumo {{
                color: #aaa;
                font-size: 0.85rem;
                margin-bottom: 12px;
            }}
            
            .noticia-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 8px;
                margin-top: 8px;
            }}
            
            .data {{
                color: #666;
                font-size: 0.7rem;
            }}
            
            .link, .botao {{
                color: #ff0000;
                text-decoration: none;
                transition: all 0.3s;
                padding: 3px 6px;
                border-radius: 4px;
                font-size: 0.8rem;
            }}
            
            .link:hover, .botao:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            .botao {{
                border: 1px solid #ff0000;
                padding: 4px 12px;
                border-radius: 15px;
            }}
            
            .botao:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            .mensagem-vazia {{
                text-align: center;
                padding: 40px 15px;
                color: #666;
                background: #111;
                border-radius: 12px;
                border: 1px dashed #333;
            }}
            
            .loading-animation {{
                width: 35px;
                height: 35px;
                border: 3px solid #333;
                border-top-color: #ff0000;
                border-radius: 50%;
                animation: spin 1s infinite linear;
                margin: 15px auto;
            }}
            
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            
            .footer {{
                background: #000;
                border-top: 4px solid #ff0000;
                padding: 30px 15px 20px;
                margin-top: 50px;
                text-align: center;
            }}
            
            .instagram-link {{
                display: inline-block;
                margin: 15px 0;
                padding: 10px 25px;
                background: #ff0000;
                color: #000;
                text-decoration: none;
                border-radius: 40px;
                font-weight: bold;
                font-size: 1rem;
                transition: all 0.3s;
                border: 2px solid #ff0000;
            }}
            
            .instagram-link:hover {{
                background: #000;
                color: #ff0000;
                transform: scale(1.05);
                box-shadow: 0 0 20px rgba(255,0,0,0.5);
            }}
            
            .footer-stats {{
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
                margin: 15px 0;
                color: #888;
                font-size: 0.8rem;
            }}
            
            .footer-copyright {{
                color: #444;
                font-size: 0.75rem;
            }}
            
            .footer-versao {{
                color: #222;
                font-size: 0.65rem;
                margin-top: 10px;
            }}
            
            /* RESPONSIVIDADE */
            @media (max-width: 600px) {{
                .titulo-container {{
                    gap: 3px;
                    transform: scale(0.9);
                }}
                
                .simbolo-anarquista {{
                    font-size: 1.5rem;
                }}
                
                .simbolo-comunista {{
                    font-size: 2.0rem;
                    margin-left: -5px;
                }}
                
                .titulo-vermelho {{
                    font-size: 1.1rem;
                }}
                
                .separador {{
                    font-size: 1.1rem;
                }}
                
                .qr-code-container {{
                    max-width: 100px;
                }}
                
                .qr-code-container img {{
                    width: 60px;
                    height: 60px;
                }}
                
                .contador-header {{
                    top: 10px;
                    right: 10px;
                    padding: 3px 8px;
                    font-size: 0.7rem;
                }}
            }}
            
            @media (max-width: 800px) {{
                .grid-principal {{
                    grid-template-columns: 1fr;
                }}
                .qr-code-container {{
                    position: relative;
                    top: 0;
                    left: 0;
                    margin: 0 auto 15px;
                }}
                .contador-header {{
                    position: relative;
                    top: 0;
                    right: 0;
                    margin: 10px auto;
                    display: inline-block;
                }}
                .horario-header {{
                    position: relative;
                    bottom: 0;
                    right: 0;
                    display: inline-block;
                    margin: 10px 0 0;
                }}
                .filtros-container {{
                    flex-direction: column;
                    align-items: center;
                }}
                .filtro-btn {{
                    width: 100%;
                    max-width: 250px;
                    justify-content: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="qr-code-container">
                <img src="/qr-code.png" alt="QR Code" onerror="this.style.display='none'">
                <p>Ajude o coletivo<br><small>Aponte a câmera</small></p>
            </div>
            
            <div class="contador-header">
                Visitas <span class="numero-contador" id="contador-visitas">{total_visitas}</span>
            </div>
            
            <div class="horario-header">🇧🇷 {horario_brasilia()}</div>
            
            <div class="titulo-container">
                <span class="simbolo-anarquista">Ⓐ</span>
                <span class="titulo-vermelho">SHARP - FRONT 16</span>
                <span class="separador">/</span>
                <span class="titulo-vermelho">RJ</span>
                <span class="simbolo-comunista">☭</span>
            </div>
            <div class="titulo-branco">Informação Antifascista</div>
            
            <div class="filtros-container" id="filtros">
                <button class="filtro-btn ativo" data-filtro="todos" onclick="filtrarNoticias('todos')">📰 TODAS <span class="contador">{len(noticias)}</span></button>
                <button class="filtro-btn" data-filtro="destaques" onclick="filtrarNoticias('destaques')">⭐ DESTAQUES <span class="contador">{len(destaques)}</span></button>
                <button class="filtro-btn" data-filtro="geopolitica" onclick="filtrarNoticias('geopolitica')">⚔️ GEOPOLÍTICA <span class="contador">{len(geopolitica)}</span></button>
                <button class="filtro-btn" data-filtro="antifa" onclick="filtrarNoticias('antifa')">🏴 ANTIFA <span class="contador">{len(antifa)}</span></button>
                <button class="filtro-btn" data-filtro="nacional" onclick="filtrarNoticias('nacional')">📰 NACIONAL <span class="contador">{len(nacionais)}</span></button>
                <button class="filtro-btn" data-filtro="internacional" onclick="filtrarNoticias('internacional')">🌎 INTERNACIONAL <span class="contador">{len(internacionais)}</span></button>
            </div>
            
            <div class="tag-container">{continentes_html}</div>
        </div>
        
        <div class="secao" id="secao-destaques">
            <div class="secao-titulo">⭐ DESTAQUES DO RADAR <span class="badge" id="contador-destaques">{len(destaques)}</span></div>
            <div class="destaques-grid" id="destaques-grid">{destaques_conteudo}</div>
        </div>
        
        <div class="grid-principal" id="grid-noticias">
            <div class="coluna" id="coluna-geopolitica" data-categoria="geopolitica">
                <h2>⚔️ Geopolítica <span class="badge" id="contador-geopolitica">{len(geopolitica)}</span></h2>
                <div id="noticias-geopolitica">{geo_html if geo_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando conflitos...</p></div>'}</div>
            </div>
            <div class="coluna" id="coluna-antifa" data-categoria="antifa">
                <h2>🏴 Antifa <span class="badge" id="contador-antifa">{len(antifa)}</span></h2>
                <div id="noticias-antifa">{antifa_html if antifa_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando movimentos...</p></div>'}</div>
            </div>
            <div class="coluna" id="coluna-nacional" data-categoria="nacional">
                <h2>📰 NACIONAL <span class="badge" id="contador-nacional">{len(nacionais)}</span></h2>
                <div id="noticias-nacional">{nacional_html if nacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias nacionais...</p></div>'}</div>
            </div>
            <div class="coluna" id="coluna-internacional" data-categoria="internacional">
                <h2>🌎 Internacional <span class="badge" id="contador-internacional">{len(internacionais)}</span></h2>
                <div id="noticias-internacional">{internacional_html if internacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias internacionais...</p></div>'}</div>
            </div>
        </div>
        
        <div class="footer">
            <a href="https://www.instagram.com/sharp.front16.rj?igsh=MXd1cjF2aTI2OGc1eQ==" target="_blank" class="instagram-link">@sharp.front16.rj</a>
            <div class="footer-stats">
                <span>🇧🇷 Horário Brasília</span>
                <span>📰 {len(noticias)} notícias</span>
                <span>Visitas {total_visitas}</span>
            </div>
            <div class="footer-copyright">SHARP - FRONT 16 RJ • Informação Antifascista</div>
            <div class="footer-copyright" style="color: #555;">Links originais preservados</div>
            <div class="footer-versao">v27.1 • 44 Fontes + Análise Global</div>
        </div>

        <script>
        function filtrarNoticias(filtro) {{
            document.querySelectorAll('.filtro-btn').forEach(btn => {{
                btn.classList.remove('ativo');
                if (btn.dataset.filtro === filtro) {{
                    btn.classList.add('ativo');
                }}
            }});
            
            const colunas = document.querySelectorAll('.coluna');
            const destaques = document.getElementById('secao-destaques');
            
            switch(filtro) {{
                case 'todos':
                    colunas.forEach(col => col.style.display = 'block');
                    destaques.style.display = 'block';
                    break;
                case 'destaques':
                    colunas.forEach(col => col.style.display = 'none');
                    destaques.style.display = 'block';
                    break;
                case 'geopolitica':
                    colunas.forEach(col => col.style.display = col.dataset.categoria === 'geopolitica' ? 'block' : 'none');
                    destaques.style.display = 'none';
                    break;
                case 'antifa':
                    colunas.forEach(col => col.style.display = col.dataset.categoria === 'antifa' ? 'block' : 'none');
                    destaques.style.display = 'none';
                    break;
                case 'nacional':
                    colunas.forEach(col => col.style.display = col.dataset.categoria === 'nacional' ? 'block' : 'none');
                    destaques.style.display = 'none';
                    break;
                case 'internacional':
                    colunas.forEach(col => col.style.display = col.dataset.categoria === 'internacional' ? 'block' : 'none');
                    destaques.style.display = 'none';
                    break;
            }}
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            filtrarNoticias('todos');
        }});
        </script>
    </body>
    </html>
    '''

# ============================================
# ROTA DE ESTATÍSTICAS
# ============================================

@app.route('/stats')
def stats_page():
    noticias = radar._carregar_noticias()
    total_visitas = contador_visitas.get_total()
    
    fontes_count = {}
    for n in noticias:
        fontes_count[n.fonte] = fontes_count.get(n.fonte, 0) + 1
    fontes_ordenadas = sorted(fontes_count.items(), key=lambda x: x[1], reverse=True)
    
    html_fontes = ''
    for fonte, count in fontes_ordenadas[:20]:
        html_fontes += f'<li>{fonte}: {count} notícias</li>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>📊 Estatísticas - SHARP FRONT 16 RJ</title>
        <style>
            body {{ background: #0a0a0a; color: white; font-family: Arial; padding: 30px; }}
            h1 {{ color: red; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .stat-box {{ background: #111; border-left: 4px solid red; padding: 20px; margin: 20px 0; border-radius: 10px; }}
            .numero-grande {{ font-size: 2.5rem; color: red; font-weight: bold; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ background: #1a1a1a; margin: 5px 0; padding: 8px 15px; border-radius: 5px; }}
            a {{ color: red; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Estatísticas do Radar</h1>
            <div class="stat-box">
                <p><strong>Total de visitas:</strong> <span class="numero-grande">{total_visitas}</span></p>
                <p><strong>Total de notícias:</strong> {len(noticias)}</p>
                <p><strong>Fontes ativas:</strong> {radar.estatisticas['fontes_funcionando']} de 44</p>
                <p><strong>Continentes:</strong> {', '.join(radar.estatisticas['continentes'])}</p>
                <p><strong>Horário:</strong> {horario_brasilia()}</p>
            </div>
            <h2>Notícias por fonte:</h2>
            <ul>{html_fontes}</ul>
            <p style="margin-top: 30px;"><a href="/">← Voltar</a></p>
        </div>
    </body>
    </html>
    '''

# ============================================
# API DE ESTATÍSTICAS
# ============================================

@app.route('/api/stats')
def api_stats():
    noticias = radar._carregar_noticias()
    total_visitas = contador_visitas.get_total()
    
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    antifa = [n for n in noticias if n.categoria in ['antifa', 'anarquista', 'comunista']]
    nacionais = [n for n in noticias if n.pais == 'Brasil']
    internacionais = [n for n in noticias if n.pais != 'Brasil']
    
    return jsonify({
        'total_visitas': total_visitas,
        'total_noticias': len(noticias),
        'geopolitica': len(geopolitica),
        'antifa': len(antifa),
        'nacional': len(nacionais),
        'internacional': len(internacionais),
        'paises': len(radar.estatisticas['paises']),
        'continentes': len(radar.estatisticas['continentes']),
        'fontes_ativas': radar.estatisticas['fontes_funcionando'],
        'ultima_atualizacao': horario_brasilia(),
        'hora_brasilia': hora_brasilia(),
    })

# ============================================
# INICIALIZAÇÃO
# ============================================

def inicializar():
    logger.info("="*70)
    logger.info("SHARP - FRONT 16 RJ - RADAR ANTIFA v27.1 - INFINITY")
    logger.info("="*70)
    
    noticias = radar._carregar_noticias()
    total_visitas = contador_visitas.get_total()
    
    logger.info(f"Acervo inicial: {len(noticias)} noticias")
    logger.info(f"Fontes configuradas: {len(FONTES_CONFIAVEIS)} (44 fontes)")
    logger.info(f"Filtro anti-casino ativo: {len(PALAVRAS_PROIBIDAS)} palavras bloqueadas")
    logger.info(f"Contador de visitas: iniciando em {total_visitas}")
    
    radar.iniciar_radar_automatico()
    logger.info("Radar automatico ativado - Busca global")
    
    anti_sono = SistemaAntiSono()
    anti_sono.iniciar()
    logger.info("✅ Sistema Anti-Sono ativado - Site acordado 24/7")
    logger.info("✅ Tradutor ativo - Notícias em Português")
    logger.info("✅ Contador de visitas discreto - 'Visitas X'")
    logger.info("✅ 44 fontes de notícias + Glint Trade anonimizado")
    logger.info("✅ Democracy Now removido conforme solicitado")
    logger.info("✅ CORRIGIDO: IP real capturado no Render (não exibido)")
    logger.info("="*70)

inicializar()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
