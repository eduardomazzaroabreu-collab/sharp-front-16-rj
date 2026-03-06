#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🔴🏴 SHARP - FRONT 16 RJ 🏴🔴                          ║
║              SISTEMA SUPREMO ANTIFA - VERSÃO 10.0 - FINAL                    ║
║         RADAR AUTOMATICO COM TIMER DE 5 SEGUNDOS - HORARIO DE BRASILIA       ║
║              "A informacao e nossa arma mais poderosa"                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from flask import Flask, jsonify
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
    MAX_PALAVRAS_POR_BUSCA = 8
    
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
    titulo: str
    resumo: str
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
        """Cria objeto de noticia"""
        try:
            resumo = ""
            if hasattr(entrada, 'summary'):
                resumo = BeautifulSoup(entrada.summary, 'html.parser').get_text()
            elif hasattr(entrada, 'description'):
                resumo = BeautifulSoup(entrada.description, 'html.parser').get_text()
            
            resumo = resumo[:200] + "..." if resumo and len(resumo) > 200 else resumo or "Leia o artigo completo..."
            
            return Noticia(
                id=hashlib.md5(entrada.link.encode()).hexdigest()[:8],
                fonte=fonte['nome'],
                pais=fonte['pais'],
                continente=fonte['continente'],
                categoria=fonte['categoria'],
                titulo=html.unescape(entrada.title),
                resumo=html.unescape(resumo),
                link=entrada.link,
                data=entrada.get('published', datetime.now().strftime('%Y-%m-%d %H:%M')),
                publicada_em=horario_brasilia()
            )
        except:
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
# FUNCAO PARA BANDEIRA EM TEXTO
# ============================================

def get_bandeira(pais):
    """Retorna texto representando o pais"""
    bandeiras = {
        'Brasil': '[BR]',
        'Portugal': '[PT]',
        'Argentina': '[AR]',
        'Mexico': '[MX]',
        'Venezuela': '[VE]',
        'USA': '[US]',
        'UK': '[UK]',
        'Qatar': '[QA]',
        'Global': '[GL]',
    }
    return bandeiras.get(pais, '[?]')

app = Flask(__name__)

# ============================================
# PAGINA PRINCIPAL - COM DUAS BOLAS
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
        <div class="destaque-card">
            <span class="destaque-tag">[Destaque]</span>
            <span class="fonte">{bandeira} {n.fonte}</span>
            <h3>{n.titulo}</h3>
            <p>{n.resumo[:150]}...</p>
            <div class="destaque-footer">
                <span class="data">[Hora] {n.data[:16]}</span>
                <a href="{n.link}" target="_blank">Ler mais</a>
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
            <p>[Radar] em operacao... buscando informacoes em {len(FONTES_CONFIAVEIS)} fontes</p>
            <p>[Timer] 5 segundos entre cada fonte</p>
        </div>
        '''
    
    # HTML Geopolitica
    geo_html = ''
    for n in geopolitica[:10]:
        bandeira = get_bandeira(n.pais)
        geo_html += f'''
        <div class="noticia">
            <span class="fonte">{bandeira} {n.fonte}</span>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:100]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank">Link</a>
            </div>
        </div>
        '''
    
    # HTML Antifa
    antifa_html = ''
    for n in antifa[:10]:
        bandeira = get_bandeira(n.pais)
        antifa_html += f'''
        <div class="noticia">
            <span class="fonte">{bandeira} {n.fonte}</span>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:100]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank">Link</a>
            </div>
        </div>
        '''
    
    # HTML Nacionais
    nacional_html = ''
    for n in nacionais[:10]:
        bandeira = get_bandeira(n.pais)
        nacional_html += f'''
        <div class="noticia nacional">
            <span class="fonte">{bandeira} {n.fonte}</span>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:100]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank">Link</a>
            </div>
        </div>
        '''
    
    # HTML Internacionais
    internacional_html = ''
    for n in internacionais[:10]:
        bandeira = get_bandeira(n.pais)
        internacional_html += f'''
        <div class="noticia internacional">
            <span class="fonte">{bandeira} {n.fonte}</span>
            <h4>{n.titulo}</h4>
            <p class="resumo">{n.resumo[:100]}...</p>
            <div class="noticia-footer">
                <span class="data">{n.data[:10]}</span>
                <a href="{n.link}" target="_blank">Link</a>
            </div>
        </div>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: Arial, sans-serif;
                background: #0a0a0a;
                color: #e0e0e0;
                line-height: 1.6;
            }}
            
            /* HEADER COM DUAS BOLAS */
            .header {{
                background: linear-gradient(135deg, #000 0%, #1a0000 100%);
                border-bottom: 4px solid #ff0000;
                padding: 30px 20px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .bolas-container {{
                position: absolute;
                top: 20px;
                right: 30px;
                display: flex;
                gap: 20px;
            }}
            
            .bola-vermelha {{
                width: 70px;
                height: 70px;
                background: #ff0000;
                border-radius: 50%;
                box-shadow: 0 0 40px rgba(255,0,0,0.8);
                animation: pulsar 2s infinite;
            }}
            
            .bola-preta {{
                width: 70px;
                height: 70px;
                background: #000;
                border-radius: 50%;
                border: 3px solid #ff0000;
                box-shadow: 0 0 40px rgba(255,0,0,0.5);
                animation: pulsar 2.5s infinite;
            }}
            
            @keyframes pulsar {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.1); }}
                100% {{ transform: scale(1); }}
            }}
            
            h1 {{
                color: #ff0000;
                font-size: 2.5rem;
                margin-bottom: 10px;
                text-shadow: 2px 2px 0 #000;
            }}
            
            .horario {{
                color: #888;
                font-size: 0.9rem;
                margin-top: 10px;
            }}
            
            .stats {{
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
                margin: 20px 0;
            }}
            
            .stat {{
                background: #111;
                border: 1px solid #ff0000;
                padding: 8px 20px;
                border-radius: 30px;
                font-size: 0.9rem;
            }}
            
            .grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 30px;
                max-width: 1400px;
                margin: 30px auto;
                padding: 0 20px;
            }}
            
            .coluna {{
                background: #111;
                border-radius: 15px;
                padding: 25px;
                border-top: 3px solid #ff0000;
            }}
            
            .coluna h2 {{
                color: #ff0000;
                font-size: 1.5rem;
                margin-bottom: 20px;
                border-bottom: 1px solid #333;
                padding-bottom: 10px;
            }}
            
            .destaques {{
                max-width: 1400px;
                margin: 30px auto;
                padding: 0 20px;
            }}
            
            .destaques h2 {{
                color: #ff0000;
                font-size: 2rem;
                margin-bottom: 20px;
            }}
            
            .destaques-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}
            
            .destaque-card {{
                background: #1a1a1a;
                border-left: 4px solid #ff0000;
                padding: 20px;
                border-radius: 10px;
            }}
            
            .destaque-tag {{
                background: #ff0000;
                color: #000;
                padding: 3px 10px;
                border-radius: 15px;
                font-size: 0.8rem;
                display: inline-block;
                margin-bottom: 10px;
            }}
            
            .noticia {{
                background: #1a1a1a;
                border-left: 3px solid #ff0000;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 5px;
            }}
            
            .noticia.nacional {{
                border-left-color: #00ff00;
            }}
            
            .noticia.internacional {{
                border-left-color: #ffaa00;
            }}
            
            .fonte {{
                color: #ff0000;
                font-weight: bold;
                font-size: 0.9rem;
            }}
            
            h4 {{
                margin: 10px 0;
                font-size: 1rem;
            }}
            
            .resumo {{
                color: #aaa;
                font-size: 0.9rem;
                margin: 10px 0;
            }}
            
            .noticia-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 10px;
                margin-top: 10px;
                font-size: 0.8rem;
            }}
            
            a {{
                color: #ff0000;
                text-decoration: none;
            }}
            
            a:hover {{
                text-decoration: underline;
            }}
            
            .mensagem-vazia {{
                text-align: center;
                padding: 50px;
                color: #666;
                background: #111;
                border-radius: 10px;
            }}
            
            .loading-animation {{
                width: 40px;
                height: 40px;
                border: 3px solid #333;
                border-top-color: #ff0000;
                border-radius: 50%;
                animation: spin 1s infinite linear;
                margin: 20px auto;
            }}
            
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            
            .footer {{
                background: #000;
                border-top: 3px solid #ff0000;
                padding: 30px;
                text-align: center;
                margin-top: 50px;
                color: #666;
            }}
            
            @media (max-width: 900px) {{
                .grid {{
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
        </style>
    </head>
    <body>
        <div class="header">
            <div class="bolas-container">
                <div class="bola-vermelha"></div>
                <div class="bola-preta"></div>
            </div>
            
            <h1>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</h1>
            <p>Informação Antifascista • Nacional & Internacional</p>
            
            <div class="stats">
                <span class="stat">📰 {len(noticias)} notícias</span>
                <span class="stat">🌍 {len(radar.estatisticas['continentes'])} continentes</span>
                <span class="stat">📡 {radar.estatisticas['fontes_funcionando']} fontes</span>
                <span class="stat">🇧🇷 {len(nacionais)} nacionais</span>
                <span class="stat">🌎 {len(internacionais)} internacionais</span>
            </div>
            
            <div class="horario">[BR] {horario_brasilia()} | Timer: 5s entre fontes</div>
        </div>
        
        <div class="destaques">
            <h2>[Destaques]</h2>
            <div class="destaques-grid">
                {destaques_conteudo}
            </div>
        </div>
        
        <div class="grid">
            <div class="coluna">
                <h2>⚔️ Geopolítica</h2>
                {geo_html if geo_html else '<div class="mensagem-vazia">Buscando...</div>'}
            </div>
            <div class="coluna">
                <h2>🏴 Antifa</h2>
                {antifa_html if antifa_html else '<div class="mensagem-vazia">Buscando...</div>'}
            </div>
            <div class="coluna">
                <h2>🇧🇷 Nacional</h2>
                {nacional_html if nacional_html else '<div class="mensagem-vazia">Buscando...</div>'}
            </div>
            <div class="coluna">
                <h2>🌎 Internacional</h2>
                {internacional_html if internacional_html else '<div class="mensagem-vazia">Buscando...</div>'}
            </div>
        </div>
        
        <div class="footer">
            <p>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</p>
            <p style="font-size: 0.8rem; margin-top: 10px;">Radar ativo • Timer 5s • Horário Brasília</p>
        </div>
    </body>
    </html>
    '''

# ============================================
# INICIALIZACAO
# ============================================

def inicializar():
    """Inicializa o sistema"""
    logger.info("="*60)
    logger.info("🔴🏴 SHARP - FRONT 16 RJ - RADAR ANTIFA")
    logger.info("="*60)
    
    noticias = radar._carregar_noticias()
    logger.info(f"Acervo inicial: {len(noticias)} noticias")
    logger.info(f"Fontes configuradas: {len(FONTES_CONFIAVEIS)}")
    
    radar.iniciar_radar_automatico()
    logger.info("Radar automatico ativado - 5 segundos entre fontes")

inicializar()

# ============================================
# FIM - NAO COLOQUE app.run() AQUI!
# ============================================
