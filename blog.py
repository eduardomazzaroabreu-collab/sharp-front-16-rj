#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🔴🏴 SHARP - FRONT 16 RJ 🏴🔴                          ║
║              SISTEMA SUPREMO ANTIFA - VERSÃO 11.0 - ULTIMATE                 ║
║         RADAR AUTOMATICO COM TIMER DE 5 SEGUNDOS - HORARIO DE BRASILIA       ║
║              "A informacao e nossa arma mais poderosa"                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from flask import Flask, jsonify, request
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
# PAGINA PRINCIPAL - DESIGN SOFISTICADO
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
            <span class="destaque-tag">⭐ DESTAQUE</span>
            <div class="destaque-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
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
            <p>⏱️ Timer: 5 segundos entre cada fonte</p>
        </div>
        '''
    
    # HTML Geopolitica
    geo_html = ''
    for n in geopolitica[:12]:
        bandeira = get_bandeira(n.pais)
        geo_html += f'''
        <div class="noticia">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
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
        <div class="noticia antifa">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
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
        <div class="noticia nacional">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
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
        <div class="noticia internacional">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">[{n.pais}]</span>
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
        <title>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</title>
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
            
            /* HEADER COM DUAS BOLAS ANIMADAS */
            .header {{
                background: linear-gradient(135deg, #000000 0%, #2a0000 70%, #000000 100%);
                border-bottom: 4px solid #ff0000;
                padding: 40px 20px 50px;
                text-align: center;
                position: relative;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(255,0,0,0.3);
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
            
            .bolas-container {{
                position: absolute;
                top: 25px;
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
                animation: pulsarVermelha 2.5s infinite ease-in-out, flutuar 4s infinite ease-in-out;
            }}
            
            .bola-preta {{
                width: 80px;
                height: 80px;
                background: #000;
                border-radius: 50%;
                border: 3px solid #ff0000;
                box-shadow: 0 0 50px rgba(255,0,0,0.5);
                animation: pulsarPreta 3s infinite ease-in-out, flutuar 4s infinite ease-in-out 0.5s;
            }}
            
            @keyframes pulsarVermelha {{
                0% {{ transform: scale(1); box-shadow: 0 0 50px rgba(255,0,0,0.8); }}
                50% {{ transform: scale(1.1); box-shadow: 0 0 80px rgba(255,0,0,1); }}
                100% {{ transform: scale(1); box-shadow: 0 0 50px rgba(255,0,0,0.8); }}
            }}
            
            @keyframes pulsarPreta {{
                0% {{ transform: scale(1); box-shadow: 0 0 40px rgba(255,0,0,0.4); }}
                50% {{ transform: scale(1.05); box-shadow: 0 0 70px rgba(255,0,0,0.8); }}
                100% {{ transform: scale(1); box-shadow: 0 0 40px rgba(255,0,0,0.4); }}
            }}
            
            @keyframes flutuar {{
                0% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-10px); }}
                100% {{ transform: translateY(0); }}
            }}
            
            h1 {{
                color: #ff0000;
                font-size: clamp(2.5rem, 7vw, 4rem);
                font-weight: 900;
                letter-spacing: 4px;
                margin-bottom: 10px;
                text-shadow: 3px 3px 0px #000, 0 0 30px rgba(255,0,0,0.5);
                position: relative;
                z-index: 1;
            }}
            
            .subtitulo {{
                color: #ccc;
                font-size: 1.2rem;
                margin-bottom: 20px;
                position: relative;
                z-index: 1;
                font-style: italic;
                border-bottom: 1px solid #ff0000;
                display: inline-block;
                padding-bottom: 8px;
            }}
            
            .horario-header {{
                position: absolute;
                bottom: 15px;
                left: 30px;
                color: #888;
                font-size: 0.9rem;
                background: rgba(0,0,0,0.7);
                padding: 5px 15px;
                border-radius: 30px;
                border: 1px solid #ff0000;
                z-index: 10;
            }}
            
            /* STATS BAR */
            .stats-container {{
                display: flex;
                justify-content: center;
                gap: 15px;
                flex-wrap: wrap;
                margin: 25px 0;
                position: relative;
                z-index: 1;
            }}
            
            .stat-item {{
                background: rgba(0,0,0,0.7);
                backdrop-filter: blur(10px);
                border: 1px solid #ff0000;
                padding: 8px 20px;
                border-radius: 40px;
                font-size: 0.95rem;
                font-weight: 500;
                transition: all 0.3s;
                box-shadow: 0 3px 10px rgba(255,0,0,0.2);
            }}
            
            .stat-item:hover {{
                background: #ff0000;
                color: #000;
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(255,0,0,0.4);
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
                padding: 6px 18px;
                border-radius: 30px;
                font-size: 0.9rem;
                border: 1px solid #ff0000;
            }}
            
            .tag-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 20px 0;
                justify-content: center;
            }}
            
            .tag {{
                background: rgba(255,0,0,0.1);
                border: 1px solid #ff0000;
                padding: 5px 15px;
                border-radius: 30px;
                font-size: 0.85rem;
            }}
            
            /* SEÇÃO DE DESTAQUES */
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
            
            .destaques-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 30px;
            }}
            
            .destaque-card {{
                background: linear-gradient(145deg, #111, #1a0000);
                border-radius: 20px;
                padding: 25px;
                position: relative;
                border: 1px solid #333;
                transition: all 0.4s;
                overflow: hidden;
                border-left: 4px solid #ff0000;
                box-shadow: 0 10px 20px rgba(0,0,0,0.3);
            }}
            
            .destaque-card::before {{
                content: '✊';
                position: absolute;
                bottom: -20px;
                right: -20px;
                font-size: 80px;
                opacity: 0.1;
                transform: rotate(-10deg);
            }}
            
            .destaque-card:hover {{
                transform: translateY(-8px);
                box-shadow: 0 20px 30px rgba(255,0,0,0.3);
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
            
            .destaque-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            
            .destaque-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 15px;
                margin-top: 15px;
            }}
            
            /* GRID PRINCIPAL */
            .grid-principal {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 30px;
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
            }}
            
            .coluna {{
                background: rgba(17, 17, 17, 0.9);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 25px;
                border: 1px solid #333;
                border-top: 3px solid #ff0000;
            }}
            
            .coluna h2 {{
                color: #ff0000;
                font-size: 1.8rem;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid #ff0000;
            }}
            
            .coluna h2 .badge {{
                background: #ff0000;
                color: #000;
                padding: 3px 12px;
                border-radius: 20px;
                font-size: 0.9rem;
                margin-left: auto;
            }}
            
            .noticia {{
                background: #111;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                border-left: 4px solid #ff0000;
                transition: all 0.3s;
            }}
            
            .noticia:hover {{
                transform: translateX(5px);
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
                margin-bottom: 10px;
                font-size: 0.9rem;
                flex-wrap: wrap;
                gap: 8px;
            }}
            
            .fonte {{
                color: #ff0000;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 0.85rem;
            }}
            
            .pais {{
                color: #888;
                background: #1a1a1a;
                padding: 2px 10px;
                border-radius: 15px;
                font-size: 0.75rem;
            }}
            
            h4 {{
                font-size: 1rem;
                margin-bottom: 12px;
                line-height: 1.5;
                color: #fff;
            }}
            
            .resumo {{
                color: #aaa;
                font-size: 0.9rem;
                margin-bottom: 15px;
            }}
            
            .noticia-footer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid #333;
                padding-top: 12px;
                margin-top: 12px;
            }}
            
            .data {{
                color: #666;
                font-size: 0.8rem;
            }}
            
            .link, .botao {{
                color: #ff0000;
                text-decoration: none;
                transition: all 0.3s;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            
            .link:hover, .botao:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            .botao {{
                border: 1px solid #ff0000;
                padding: 5px 15px;
                border-radius: 20px;
            }}
            
            .botao:hover {{
                background: #ff0000;
                color: #000;
            }}
            
            .mensagem-vazia {{
                text-align: center;
                padding: 60px 20px;
                color: #666;
                background: #111;
                border-radius: 15px;
                border: 1px dashed #333;
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
            
            /* RODAPÉ */
            .footer {{
                background: #000;
                border-top: 4px solid #ff0000;
                padding: 40px 20px 30px;
                margin-top: 60px;
                text-align: center;
            }}
            
            .footer-stats {{
                display: flex;
                justify-content: center;
                gap: 25px;
                flex-wrap: wrap;
                margin-bottom: 30px;
                color: #888;
            }}
            
            .footer-links {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-bottom: 25px;
                flex-wrap: wrap;
            }}
            
            .footer-links a {{
                color: #666;
                text-decoration: none;
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
            
            .footer-copyright {{
                color: #444;
                font-size: 0.8rem;
            }}
            
            .footer-versao {{
                color: #222;
                font-size: 0.7rem;
                margin-top: 15px;
            }}
            
            /* RESPONSIVIDADE */
            @media (max-width: 1000px) {{
                .grid-principal {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            @media (max-width: 700px) {{
                .bolas-container {{
                    position: relative;
                    top: 0;
                    right: 0;
                    justify-content: center;
                    margin-bottom: 20px;
                }}
                
                .horario-header {{
                    position: relative;
                    bottom: 0;
                    left: 0;
                    display: inline-block;
                    margin-top: 10px;
                }}
            }}
            
            @media (max-width: 500px) {{
                .stats-container {{
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
                <div class="bola-vermelha" title="Luta e Resistência"></div>
                <div class="bola-preta" title="Antifascismo"></div>
            </div>
            
            <div class="horario-header">
                🇧🇷 {horario_brasilia()} | ⏱️ Timer: 5s
            </div>
            
            <h1>🔴🏴 SHARP - FRONT 16 RJ 🏴🔴</h1>
            <p class="subtitulo">Informação Antifascista • Nacional & Internacional</p>
            
            <div class="stats-container">
                <span class="stat-item">📰 {len(noticias)} notícias</span>
                <span class="stat-item">🌍 {len(radar.estatisticas['continentes'])} continentes</span>
                <span class="stat-item">📡 {radar.estatisticas['fontes_funcionando']} fontes</span>
                <span class="stat-item">🇧🇷 {len(nacionais)} nacionais</span>
                <span class="stat-item">🌎 {len(internacionais)} internacionais</span>
                <span class="stat-item">⚔️ {len(geopolitica)} conflitos</span>
                <span class="stat-item">🏴 {len(antifa)} antifa</span>
            </div>
            
            <div class="radar-info">
                <span class="radar-badge">🛸 Radar ativo</span>
                <span class="radar-badge">⏱️ 5s entre fontes</span>
                <span class="radar-badge">🔤 Filtro anti-casino ativo</span>
            </div>
            
            <div class="tag-container">
                {continentes_html}
            </div>
        </div>
        
        <!-- DESTAQUES -->
        <div class="secao">
            <div class="secao-titulo">
                ⭐ DESTAQUES DO RADAR
                <span class="badge">{len(destaques)} destaques</span>
            </div>
            
            <div class="destaques-grid">
                {destaques_conteudo}
            </div>
        </div>
        
        <!-- GRID PRINCIPAL -->
        <div class="grid-principal">
            <!-- COLUNA GEOPOLÍTICA -->
            <div class="coluna">
                <h2>
                    ⚔️ Geopolítica
                    <span class="badge">{len(geopolitica)}</span>
                </h2>
                {geo_html if geo_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando conflitos...</p></div>'}
            </div>
            
            <!-- COLUNA ANTIFA -->
            <div class="coluna">
                <h2>
                    🏴 Antifa
                    <span class="badge">{len(antifa)}</span>
                </h2>
                {antifa_html if antifa_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando movimentos...</p></div>'}
            </div>
            
            <!-- COLUNA NACIONAL -->
            <div class="coluna">
                <h2>
                    🇧🇷 Nacional
                    <span class="badge">{len(nacionais)}</span>
                </h2>
                {nacional_html if nacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias nacionais...</p></div>'}
            </div>
            
            <!-- COLUNA INTERNACIONAL -->
            <div class="coluna">
                <h2>
                    🌎 Internacional
                    <span class="badge">{len(internacionais)}</span>
                </h2>
                {internacional_html if internacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias internacionais...</p></div>'}
            </div>
        </div>
        
        <!-- RODAPÉ -->
        <div class="footer">
            <div class="footer-stats">
                <span>🛸 Radar ativo</span>
                <span>⏱️ Timer 5s</span>
                <span>📡 {radar.estatisticas['fontes_funcionando']} fontes ativas</span>
                <span>🔤 Filtro anti-casino</span>
                <span>🇧🇷 Horário Brasília</span>
            </div>
            
            <div class="footer-links">
                <a href="#">Sobre</a>
                <a href="#">Fontes</a>
                <a href="#">Contato</a>
                <a href="#">Manifesto</a>
                <a href="/stats">📊 Estatísticas</a>
            </div>
            
            <div class="footer-copyright">
                🔴🏴 SHARP - FRONT 16 RJ 🏴🔴 • Informação Antifascista
            </div>
            <div class="footer-copyright" style="color: #555;">
                Todos os links são das fontes originais
            </div>
            <div class="footer-versao">
                v11.0 • Radar Anti-Casino • Timer 5s • {len(FONTES_CONFIAVEIS)} fontes
            </div>
        </div>
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
    logger.info("="*60)
    logger.info("🔴🏴 SHARP - FRONT 16 RJ - RADAR ANTIFA v11.0")
    logger.info("="*60)
    
    noticias = radar._carregar_noticias()
    logger.info(f"Acervo inicial: {len(noticias)} noticias")
    logger.info(f"Fontes configuradas: {len(FONTES_CONFIAVEIS)}")
    logger.info(f"Filtro anti-casino ativo: {len(PALAVRAS_PROIBIDAS)} palavras bloqueadas")
    
    radar.iniciar_radar_automatico()
    logger.info("Radar automatico ativado - 5 segundos entre fontes")
    logger.info("="*60)

inicializar()

# ============================================
# FIM - NÃO COLOQUE app.run() AQUI!
# ============================================
