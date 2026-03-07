#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SHARP - FRONT 16 RJ                                        ║
║              SISTEMA SUPREMO ANTIFA - VERSÃO 17.0 - FINAL                    ║
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
                # Extrai o texto traduzido do JSON
                if result and len(result) > 0 and len(result[0]) > 0:
                    return result[0][0][0]
        except Exception as e:
            logger.debug(f"Erro na tradução: {e}")
        
        return texto  # Se falhar, retorna original

tradutor = TradutorIntegrado()

# ============================================
# CONFIGURACOES PROFISSIONAIS AVANCADAS
# ============================================

class Config:
    """Configuracoes avancadas do sistema supremo antifa"""
    
    # Identidade
    NOME_SITE = "SHARP - FRONT 16 RJ"
    LEMA = "A informacao e nossa arma mais poderosa"
    
    # Arquivos
    ARQUIVO_NOTICIAS = 'noticias_salvas.json'
    ARQUIVO_CACHE = 'cache_fontes.json'
    ARQUIVO_HISTORICO = 'historico_buscas.json'
    ARQUIVO_LOG = 'radar_antifa.log'
    
    # Tempos
    TEMPO_ATUALIZACAO = 10  # minutos
    TIMEOUT_REQUISICAO = 8  # segundos
    TIMEOUT_TOTAL = 30  # segundos
    DELAY_ENTRE_REQUISICOES = 5  # 5 segundos entre cada site
    DELAY_INICIAL = 2  # segundos antes de comecar
    
    # Limites
    MAX_NOTICIAS_POR_FONTE = 5
    MAX_NOTICIAS_TOTAL = 3000
    MAX_TRABALHADORES = 10
    MAX_TENTATIVAS = 2
    
    # Headers para parecer navegador real
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,es;q=0.7,fr;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
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
# PALAVRAS PROIBIDAS (FILTRO DE CASINO E SPAM)
# ============================================

PALAVRAS_PROIBIDAS = [
    'casino', 'cassino', 'bet', 'aposta', 'gambling', 'poker', 'slot',
    'roulette', 'blackjack', 'baccarat', 'vegas', 'lottery', 'sweepstakes',
    'crypto', 'bitcoin', 'investimento', 'renda extra', 'ganhe dinheiro',
    'milagroso', 'segredo', 'fórmula', 'curso', 'download', 'gratis',
    'sexo', 'porn', 'onlyfans', 'hot', 'universitario', 'trabalhe em casa'
]

# ============================================
# SISTEMA DE PROXY INTELIGENTE
# ============================================

class ProxyManager:
    """Gerencia rotacao de proxies para evitar bloqueios"""
    
    def __init__(self):
        self.proxies = []
        self.blacklist = set()
        self.atualizar_lista()
    
    def atualizar_lista(self):
        """Busca proxies publicos atualizados"""
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
        """Retorna um proxy aleatorio da lista"""
        if self.proxies:
            proxy = random.choice(self.proxies)
            return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        return None

proxy_manager = ProxyManager()

# ============================================
# SISTEMA ANTI-SONO (MANTÉM O SITE ACORDADO 24/7)
# ============================================

class SistemaAntiSono:
    """Sistema que faz ping no próprio site para não dormir"""
    
    def __init__(self):
        self.ativo = True
        self.url_do_site = "https://sharp-front-16-rj.onrender.com"
        self.contador_pings = 0
        
    def iniciar(self):
        """Inicia a thread de ping automático"""
        thread = threading.Thread(target=self._loop_ping)
        thread.daemon = True
        thread.start()
        logger.info("[Anti-Sono] Sistema ativado - Ping a cada 5 minutos")
    
    def _loop_ping(self):
        """Loop que faz ping a cada 5 minutos"""
        while self.ativo:
            try:
                # Faz uma requisição para o próprio site
                response = requests.get(self.url_do_site, timeout=10)
                self.contador_pings += 1
                logger.info(f"[Anti-Sono] Ping #{self.contador_pings} - Status: {response.status_code}")
                
                # Também pinga a API de stats
                requests.get(f"{self.url_do_site}/api/stats", timeout=5)
                
            except Exception as e:
                logger.error(f"[Anti-Sono] Erro no ping: {e}")
            
            # Espera 5 minutos (300 segundos)
            time.sleep(300)

# ============================================
# FONTES CONFIABEIS (NACIONAL E INTERNACIONAL)
# ============================================

FONTES_CONFIAVEIS = [
    # BRASIL
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'The Intercept Brasil', 'pais': 'Brasil', 'url': 'https://theintercept.com/brasil/feed/', 'categoria': 'antifa', 'continente': 'America do Sul'},
    
    # PORTUGAL
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria': 'antifa', 'continente': 'Europa'},
    
    # AMERICA LATINA
    {'nome': 'Pagina 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria': 'antifa', 'continente': 'America do Sul'},
    {'nome': 'La Jornada', 'pais': 'Mexico', 'url': 'https://www.jornada.com.mx/rss', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria': 'antifa', 'continente': 'America do Sul'},
    
    # USA / INTERNACIONAL
    {'nome': 'Its Going Down', 'pais': 'USA', 'url': 'https://itsgoingdown.org/feed/', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'CrimethInc', 'pais': 'Global', 'url': 'https://crimethinc.com/feeds/all.atom.xml', 'categoria': 'anarquista', 'continente': 'Global'},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria': 'antifa', 'continente': 'Global'},
    {'nome': 'Democracy Now', 'pais': 'USA', 'url': 'https://www.democracynow.org/podcast.xml', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria': 'antifa', 'continente': 'America do Norte'},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria': 'comunista', 'continente': 'America do Norte'},
    
    # UK / EUROPA
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria': 'antifa', 'continente': 'Europa'},
    
    # ORIENTE MEDIO
    {'nome': 'Al Jazeera', 'pais': 'Qatar', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
    {'nome': 'Middle East Eye', 'pais': 'UK', 'url': 'https://www.middleeasteye.net/rss', 'categoria': 'geopolitica', 'continente': 'Oriente Medio'},
]

# ============================================
# SISTEMA DE RADAR AUTOMATICO
# ============================================

@dataclass
class Noticia:
    """Estrutura de dados para noticias"""
    id: str
    fonte: str
    pais: str
    continente: str
    categoria: str
    titulo: str          # Título em português
    titulo_original: str  # Título original (inglês/espanhol/etc)
    resumo: str           # Resumo em português
    resumo_original: str  # Resumo original
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
        """Inicia o radar automatico"""
        if self.radar_ativo:
            return
        
        self.radar_ativo = True
        thread = threading.Thread(target=self._loop_radar)
        thread.daemon = True
        thread.start()
        logger.info("[Radar] Radar automatico iniciado")
    
    def _loop_radar(self):
        """Loop principal do radar"""
        time.sleep(config.DELAY_INICIAL)
        
        while self.radar_ativo:
            try:
                self._executar_varredura()
                time.sleep(config.TEMPO_ATUALIZACAO * 60)
            except Exception as e:
                logger.error(f"[Erro] no radar: {e}")
                time.sleep(60)
    
    def _executar_varredura(self):
        """Executa uma varredura completa"""
        logger.info(f"\n{'='*60}")
        logger.info(f"[Radar] [{horario_brasilia()}] Iniciando varredura")
        logger.info(f"{'='*60}")
        
        noticias_antigas = self._carregar_noticias()
        links_antigos = {n.link for n in noticias_antigas}
        todas_noticias_novas = []
        
        for fonte in FONTES_CONFIAVEIS:
            time.sleep(config.DELAY_ENTRE_REQUISICOES)
            
            try:
                response = requests.get(
                    fonte['url'],
                    headers=config.HEADERS,
                    timeout=config.TIMEOUT_REQUISICAO
                )
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    
                    if len(feed.entries) > 0:
                        noticias_fonte = []
                        
                        for entrada in feed.entries[:config.MAX_NOTICIAS_POR_FONTE]:
                            if entrada.link in links_antigos:
                                continue
                            
                            # FILTRO ANTI-CASINO
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
        """Cria objeto de noticia com TRADUÇÃO para português"""
        try:
            # Título original e traduzido
            titulo_original = entrada.title
            titulo_traduzido = tradutor.traduzir(titulo_original)
            
            # Resumo original e traduzido
            resumo_original = ""
            if hasattr(entrada, 'summary'):
                resumo_original = BeautifulSoup(entrada.summary, 'html.parser').get_text()
            elif hasattr(entrada, 'description'):
                resumo_original = BeautifulSoup(entrada.description, 'html.parser').get_text()
            
            resumo_traduzido = tradutor.traduzir(resumo_original) if resumo_original else ""
            resumo_traduzido = resumo_traduzido[:200] + "..." if resumo_traduzido and len(resumo_traduzido) > 200 else resumo_traduzido or "Leia o artigo completo..."
            
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
        """Carrega noticias do arquivo"""
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
        """Salva noticias no arquivo"""
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
    """Retorna a bandeira do pais"""
    bandeiras = {
        'Brasil': '🇧🇷',
        'Portugal': '🇵🇹',
        'Argentina': '🇦🇷',
        'Mexico': '🇲🇽',
        'Venezuela': '🇻🇪',
        'USA': '🇺🇸',
        'UK': '🇬🇧',
        'Qatar': '🇶🇦',
        'Global': '🌍',
        'Oriente Medio': '🕌',
        'Europa': '🇪🇺',
        'America do Sul': '🌎',
        'America do Norte': '🌎',
    }
    return bandeiras.get(pais, '🏴')

app = Flask(__name__)

# ============================================
# ROTA PARA SERVIR O QR CODE
# ============================================

@app.route('/qr-code.png')
def serve_qr_code():
    return send_from_directory('.', 'qr-code.png')

# ============================================
# ROTA DE PING (PARA O SISTEMA ANTI-SONO)
# ============================================

@app.route('/ping')
def ping():
    """Rota simples para manter o site acordado"""
    return jsonify({
        'status': 'ok',
        'horario': horario_brasilia(),
        'mensagem': 'Sistema anti-sono ativo'
    })

# ============================================
# PAGINA PRINCIPAL - VERSÃO FINAL COM NOTÍCIAS EM PT
# ============================================

@app.route('/')
def home():
    noticias = radar._carregar_noticias()
    
    # Separa por categoria
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    antifa = [n for n in noticias if n.categoria in ['antifa', 'anarquista', 'comunista']]
    nacionais = [n for n in noticias if n.pais == 'Brasil']
    internacionais = [n for n in noticias if n.pais != 'Brasil']
    destaques = [n for n in noticias if n.destaque][:5]
    
    # HTML dos destaques
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
    
    # Processa destaques vazios
    if destaques_html:
        destaques_conteudo = destaques_html
    else:
        destaques_conteudo = f'''
        <div class="mensagem-vazia">
            <div class="loading-animation"></div>
            <p>🔍 Radar em operacao... buscando informacoes em {len(FONTES_CONFIAVEIS)} fontes</p>
        </div>
        '''
    
    # HTML Geopolitica
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
    
    # HTML Antifa
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
    
    # HTML Nacionais
    nacional_html = ''
    for n in nacionais[:12]:
        bandeira = get_bandeira(n.pais)
        nacional_html += f'''
        <div class="noticia nacional" data-categoria="{n.categoria}" data-pais="Brasil">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[BR]</span>
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
    
    # HTML Internacionais
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
    
    # HTML do mapa de continentes
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
            /* RESET E ESTILOS GLOBAIS */
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
            
            /* HEADER COM QR CODE */
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
            
            /* QR CODE NO CANTO ESQUERDO */
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
            
            /* TÍTULO COM SIMBOLOS */
            .titulo-container {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 5px;
                margin-bottom: 5px;
                flex-wrap: wrap;
            }}
            
            .simbolo-anarquista {{
                color: #ff0000;
                font-size: 1.8rem;
                filter: drop-shadow(0 0 5px rgba(255,0,0,0.5));
            }}
            
            .simbolo-comunista {{
                color: #ff0000;
                font-size: 1.8rem;
                filter: drop-shadow(0 0 5px rgba(255,0,0,0.5));
            }}
            
            .titulo-vermelho {{
                color: #ff0000;
                font-size: clamp(1.5rem, 4vw, 2.5rem);
                font-weight: 900;
                letter-spacing: 2px;
                text-shadow: 2px 2px 0px #000;
            }}
            
            .separador {{
                color: #ff0000;
                font-size: clamp(1.5rem, 4vw, 2.5rem);
                font-weight: 900;
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
            
            /* TOOLTIP PARA TÍTULO ORIGINAL */
            .tooltip {{
                cursor: help;
                font-size: 0.8rem;
                opacity: 0.7;
                transition: opacity 0.3s;
            }}
            
            .tooltip:hover {{
                opacity: 1;
            }}
            
            /* FILTROS - BOTÕES CLICÁVEIS */
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
                background: #ff0000;
                color: #000;
                border-color: #fff;
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
            
            /* SEÇÃO DE DESTAQUES */
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
            
            /* GRID PRINCIPAL */
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
            
            /* RODAPÉ COM INSTAGRAM VERMELHO */
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
            
            @media (max-width: 500px) {{
                .qr-code-container {{
                    max-width: 120px;
                }}
                
                .qr-code-container img {{
                    width: 70px;
                    height: 70px;
                }}
                
                .titulo-container {{
                    flex-direction: column;
                    gap: 2px;
                }}
                
                .simbolo-anarquista, .simbolo-comunista {{
                    font-size: 1.5rem;
                }}
                
                .coluna h2 {{
                    font-size: 1.3rem;
                }}
                
                h4 {{
                    font-size: 0.9rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <!-- QR CODE NO CANTO ESQUERDO -->
            <div class="qr-code-container">
                <img src="/qr-code.png" alt="QR Code" onerror="this.style.display='none'">
                <p>
                    Ajude o coletivo<br>
                    <small>Aponte a câmera</small>
                </p>
            </div>
            
            <div class="horario-header">
                🇧🇷 {horario_brasilia()}
            </div>
            
            <div class="titulo-container">
                <span class="simbolo-anarquista">Ⓐ</span>
                <span class="titulo-vermelho">SHARP - FRONT 16</span>
                <span class="separador">/</span>
                <span class="titulo-vermelho">RJ</span>
                <span class="simbolo-comunista">☭</span>
            </div>
            <div class="titulo-branco">Informação Antifascista</div>
            
            <!-- FILTROS CLICÁVEIS -->
            <div class="filtros-container" id="filtros">
                <button class="filtro-btn ativo" data-filtro="todos" onclick="filtrarNoticias('todos')">
                    📰 TODAS <span class="contador">{len(noticias)}</span>
                </button>
                <button class="filtro-btn" data-filtro="destaques" onclick="filtrarNoticias('destaques')">
                    ⭐ DESTAQUES <span class="contador">{len(destaques)}</span>
                </button>
                <button class="filtro-btn" data-filtro="geopolitica" onclick="filtrarNoticias('geopolitica')">
                    ⚔️ GEOPOLÍTICA <span class="contador">{len(geopolitica)}</span>
                </button>
                <button class="filtro-btn" data-filtro="antifa" onclick="filtrarNoticias('antifa')">
                    🏴 ANTIFA <span class="contador">{len(antifa)}</span>
                </button>
                <button class="filtro-btn" data-filtro="nacional" onclick="filtrarNoticias('nacional')">
                    🇧🇷 BR NACIONAL <span class="contador">{len(nacionais)}</span>
                </button>
                <button class="filtro-btn" data-filtro="internacional" onclick="filtrarNoticias('internacional')">
                    🌎 INTERNACIONAL <span class="contador">{len(internacionais)}</span>
                </button>
            </div>
            
            <div class="tag-container">
                {continentes_html}
            </div>
        </div>
        
        <!-- DESTAQUES -->
        <div class="secao" id="secao-destaques">
            <div class="secao-titulo">
                ⭐ DESTAQUES DO RADAR
                <span class="badge" id="contador-destaques">{len(destaques)}</span>
            </div>
            
            <div class="destaques-grid" id="destaques-grid">
                {destaques_conteudo}
            </div>
        </div>
        
        <!-- GRID PRINCIPAL -->
        <div class="grid-principal" id="grid-noticias">
            <!-- COLUNA GEOPOLÍTICA -->
            <div class="coluna" id="coluna-geopolitica" data-categoria="geopolitica">
                <h2>
                    ⚔️ Geopolítica
                    <span class="badge" id="contador-geopolitica">{len(geopolitica)}</span>
                </h2>
                <div id="noticias-geopolitica">
                    {geo_html if geo_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando conflitos...</p></div>'}
                </div>
            </div>
            
            <!-- COLUNA ANTIFA -->
            <div class="coluna" id="coluna-antifa" data-categoria="antifa">
                <h2>
                    🏴 Antifa
                    <span class="badge" id="contador-antifa">{len(antifa)}</span>
                </h2>
                <div id="noticias-antifa">
                    {antifa_html if antifa_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando movimentos...</p></div>'}
                </div>
            </div>
            
            <!-- COLUNA NACIONAL -->
            <div class="coluna" id="coluna-nacional" data-categoria="nacional">
                <h2>
                    🇧🇷 BR NACIONAL
                    <span class="badge" id="contador-nacional">{len(nacionais)}</span>
                </h2>
                <div id="noticias-nacional">
                    {nacional_html if nacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias nacionais...</p></div>'}
                </div>
            </div>
            
            <!-- COLUNA INTERNACIONAL -->
            <div class="coluna" id="coluna-internacional" data-categoria="internacional">
                <h2>
                    🌎 Internacional
                    <span class="badge" id="contador-internacional">{len(internacionais)}</span>
                </h2>
                <div id="noticias-internacional">
                    {internacional_html if internacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias internacionais...</p></div>'}
                </div>
            </div>
        </div>
        
        <!-- RODAPÉ -->
        <div class="footer">
            <!-- LINK DO INSTAGRAM VERMELHO -->
            <a href="https://www.instagram.com/sharp.front16.rj?igsh=MXd1cjF2aTI2OGc1eQ==" target="_blank" class="instagram-link">
                @sharp.front16.rj
            </a>
            
            <div class="footer-stats">
                <span>📡 {radar.estatisticas['fontes_funcionando']} fontes</span>
                <span>🇧🇷 Horário Brasília</span>
                <span>📰 {len(noticias)} notícias</span>
            </div>
            
            <div class="footer-copyright">
                SHARP - FRONT 16 RJ • Informação Antifascista
            </div>
            <div class="footer-copyright" style="color: #555;">
                Links originais preservados
            </div>
            <div class="footer-versao">
                v17.0 • Notícias em Português
            </div>
        </div>

        <!-- SCRIPT DE FILTROS -->
        <script>
        // Função principal de filtro
        function filtrarNoticias(filtro) {{
            // Atualiza botões ativos
            document.querySelectorAll('.filtro-btn').forEach(btn => {{
                btn.classList.remove('ativo');
                if (btn.dataset.filtro === filtro) {{
                    btn.classList.add('ativo');
                }}
            }});
            
            // Mostra/esconde seções baseado no filtro
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
                    colunas.forEach(col => {{
                        col.style.display = col.dataset.categoria === 'geopolitica' ? 'block' : 'none';
                    }});
                    destaques.style.display = 'none';
                    break;
                    
                case 'antifa':
                    colunas.forEach(col => {{
                        col.style.display = col.dataset.categoria === 'antifa' ? 'block' : 'none';
                    }});
                    destaques.style.display = 'none';
                    break;
                    
                case 'nacional':
                    colunas.forEach(col => {{
                        col.style.display = col.dataset.categoria === 'nacional' ? 'block' : 'none';
                    }});
                    destaques.style.display = 'none';
                    break;
                    
                case 'internacional':
                    colunas.forEach(col => {{
                        col.style.display = col.dataset.categoria === 'internacional' ? 'block' : 'none';
                    }});
                    destaques.style.display = 'none';
                    break;
            }}
        }}
        
        // Inicializa com filtro "todos" ativo
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
    
    # Conta por fonte
    fontes_count = {}
    for n in noticias:
        fontes_count[n.fonte] = fontes_count.get(n.fonte, 0) + 1
    
    # Ordena por quantidade
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
            ul {{ list-style: none; padding: 0; }}
            li {{ background: #1a1a1a; margin: 5px 0; padding: 8px 15px; border-radius: 5px; }}
            a {{ color: red; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Estatísticas do Radar</h1>
            <div class="stat-box">
                <p><strong>Total de notícias:</strong> {len(noticias)}</p>
                <p><strong>Fontes ativas:</strong> {radar.estatisticas['fontes_funcionando']}</p>
                <p><strong>Continentes:</strong> {', '.join(radar.estatisticas['continentes'])}</p>
                <p><strong>Horário:</strong> {horario_brasilia()}</p>
            </div>
            
            <h2>Notícias por fonte:</h2>
            <ul>
                {html_fontes}
            </ul>
            
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
        'ultima_atualizacao': horario_brasilia(),
        'hora_brasilia': hora_brasilia(),
    })

# ============================================
# INICIALIZAÇÃO
# ============================================

def inicializar():
    """Inicializa o sistema"""
    logger.info("="*70)
    logger.info("SHARP - FRONT 16 RJ - RADAR ANTIFA v17.0")
    logger.info("="*70)
    
    noticias = radar._carregar_noticias()
    logger.info(f"Acervo inicial: {len(noticias)} noticias")
    logger.info(f"Fontes configuradas: {len(FONTES_CONFIAVEIS)}")
    logger.info(f"Filtro anti-casino ativo: {len(PALAVRAS_PROIBIDAS)} palavras bloqueadas")
    
    radar.iniciar_radar_automatico()
    logger.info("Radar automatico ativado - Busca global")
    
    # INICIA O SISTEMA ANTI-SONO
    anti_sono = SistemaAntiSono()
    anti_sono.iniciar()
    logger.info("✅ Sistema Anti-Sono ativado - Site acordado 24/7")
    logger.info("✅ Tradutor ativo - Notícias em Português")
    logger.info("="*70)

inicializar()

# ============================================
# FIM - NÃO COLOQUE app.run() AQUI!
# ============================================
