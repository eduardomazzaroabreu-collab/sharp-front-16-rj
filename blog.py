#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SHARP - FRONT 16 RJ                                        ║
║              SISTEMA SUPREMO ANTIFA - VERSÃO 29.0 - INFINITY                 ║
║         RADAR AUTOMATICO COM 120+ FONTES - NOTÍCIAS EM PT                    ║
║         "Informação com propósito - Sempre atualizado"                       ║
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
# CONTADOR DE VISITANTES
# ============================================

class ContadorVisitantes:
    """Contador de visitas por IP - começa em 176 e vai ao infinito"""
    
    def __init__(self, arquivo='contador_visitas.json'):
        self.arquivo = arquivo
        self.visitas_unicas = set()
        self.total_visitas = 176
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados salvos"""
        if os.path.exists(self.arquivo):
            try:
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.visitas_unicas = set(dados.get('ips', []))
                    self.total_visitas = dados.get('total', 176)
                logger.info(f"[Contador] Carregado: {self.total_visitas} visitas")
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
        except Exception as e:
            logger.error(f"[Contador] Erro ao salvar: {e}")
    
    def get_ip_real(self):
        """Pega o IP real do visitante (funciona no Render)"""
        if request.headers.getlist("X-Forwarded-For"):
            ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
            return ip
        return request.remote_addr
    
    def registrar_visita(self):
        """Registra uma visita única usando IP real"""
        ip = self.get_ip_real()
        if ip and ip not in self.visitas_unicas and ip != '127.0.0.1' and not ip.startswith('10.'):
            self.visitas_unicas.add(ip)
            self.total_visitas += 1
            self.salvar_dados()
            logger.info(f"[Contador] Nova visita! Total: {self.total_visitas}")
            return True
        return False
    
    def get_total(self):
        return self.total_visitas

contador_visitas = ContadorVisitantes()

# ============================================
# TRADUTOR INTEGRADO
# ============================================

class TradutorIntegrado:
    """Tradutor usando Google Translate"""
    
    @staticmethod
    def traduzir(texto, idioma_destino='pt'):
        if not texto or len(texto) < 10:
            return texto
        
        try:
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
# CONFIGURACOES AVANÇADAS
# ============================================

class Config:
    NOME_SITE = "SHARP - FRONT 16 RJ"
    LEMA = "A informacao e nossa arma mais poderosa"
    
    ARQUIVO_NOTICIAS = 'noticias_salvas.json'
    ARQUIVO_CACHE = 'cache_fontes.json'
    ARQUIVO_HISTORICO = 'historico_buscas.json'
    ARQUIVO_LOG = 'radar_antifa.log'
    
    TEMPO_ATUALIZACAO = 10  # minutos
    TIMEOUT_REQUISICAO = 8
    TIMEOUT_TOTAL = 30
    DELAY_ENTRE_REQUISICOES = 3  # Reduzido para 3 segundos
    DELAY_INICIAL = 2
    
    MAX_NOTICIAS_POR_FONTE = 5
    MAX_NOTICIAS_TOTAL = 8000  # Aumentado para 8000
    MAX_TRABALHADORES = 15
    MAX_TENTATIVAS = 2
    
    # NOVO: Expurgo automático
    DIAS_MAXIMO_NOTICIA = 3  # Notícias com mais de 3 dias são removidas
    
    # NOVO: Rodízio de fontes
    FONTES_POR_VARREDURA = 40  # Varrer 40 fontes por ciclo
    TOTAL_FONTES = 120  # 120 fontes no total
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    
    TIMEZONE = -3

config = Config()

# ============================================
# FUNCOES DE HORARIO
# ============================================

def horario_brasilia():
    utc = datetime.utcnow()
    brasilia = utc - timedelta(hours=3)
    return brasilia.strftime('%d/%m/%Y %H:%M:%S')

def hora_brasilia():
    utc = datetime.utcnow()
    brasilia = utc - timedelta(hours=3)
    return brasilia.strftime('%H:%M')

# ============================================
# LOGGING
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
# PALAVRAS PROIBIDAS (FILTRO)
# ============================================

PALAVRAS_PROIBIDAS = [
    'casino', 'cassino', 'bet', 'aposta', 'gambling', 'poker', 'slot',
    'roulette', 'blackjack', 'baccarat', 'vegas', 'lottery', 'sweepstakes',
    'crypto', 'bitcoin', 'investimento', 'renda extra', 'ganhe dinheiro',
    'milagroso', 'segredo', 'fórmula', 'curso', 'download', 'gratis',
    'sexo', 'porn', 'onlyfans', 'hot', 'universitario', 'trabalhe em casa',
    # Conteúdo sem propósito
    'fofoca', 'celebridade', 'bbb', 'big brother', 'reality show',
    'novela', 'famoso', 'famosa', 'lifestyle', 'moda', 'viagem',
    'receita', 'culinária', 'esporte', 'futebol', 'jogador',
]

# ============================================
# SISTEMA DE PROXY
# ============================================

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.blacklist = set()
        self.atualizar_lista()
    
    def atualizar_lista(self):
        try:
            fontes_proxy = [
                'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
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
    def __init__(self):
        self.ativo = True
        self.url_do_site = "https://sharp-front-16-rj.onrender.com"
        self.contador_pings = 0
        
    def iniciar(self):
        thread = threading.Thread(target=self._loop_ping)
        thread.daemon = True
        thread.start()
        logger.info("[Anti-Sono] Sistema ativado")
    
    def _loop_ping(self):
        while self.ativo:
            try:
                requests.get(self.url_do_site, timeout=10)
                self.contador_pings += 1
                logger.info(f"[Anti-Sono] Ping #{self.contador_pings}")
                requests.get(f"{self.url_do_site}/api/stats", timeout=5)
            except:
                pass
            time.sleep(300)

# ============================================
# CLASSIFICADOR AUTOMÁTICO DE NOTÍCIAS
# ============================================

class ClassificadorNoticias:
    """Classifica notícias automaticamente baseado no conteúdo"""
    
    # Palavras-chave para cada categoria
    PALAVRAS_ANTIFA = [
        'protesto', 'greve', 'movimento', 'resistência', 'direitos', 
        'ativismo', 'luta', 'ocupação', 'mst', 'sem terra', 'indígena', 
        'quilombola', 'lgbt', 'feminismo', 'negro', 'racismo', 'fascismo',
        'antifa', 'anarquista', 'comunista', 'socialista', 'manifestação',
        'sindicato', 'trabalhador', 'popular', 'massacre', 'violência policial'
    ]
    
    PALAVRAS_GEOPOLITICA = [
        'guerra', 'conflito', 'rússia', 'ucrânia', 'china', 'eua', 
        'estados unidos', 'otan', 'nato', 'sanções', 'imperialismo', 
        'colonização', 'fronteira', 'geopolítica', 'tensão', 'ataque',
        'bomba', 'míssil', 'exército', 'militar', 'tratado', 'aliança',
        'oriente médio', 'palestina', 'israel', 'faixa de gaza'
    ]
    
    PALAVRAS_NACIONAL = [
        'brasil', 'lula', 'bolsonaro', 'congresso', 'stf', 'brasileiro',
        'brasília', 'são paulo', 'rio de janeiro', 'governo federal',
        'eleição', 'voto', 'política brasileira', 'câmara', 'senado'
    ]
    
    @classmethod
    def classificar(cls, titulo, resumo, fonte_pais, fonte_nome):
        """Classifica notícia baseado em múltiplos fatores"""
        texto = (titulo + " " + resumo).lower()
        
        # PRIORIDADE 1: ANTIFA (lutas sociais)
        if any(p in texto for p in cls.PALAVRAS_ANTIFA):
            return 'antifa'
        
        # PRIORIDADE 2: GEOPOLÍTICA
        if any(p in texto for p in cls.PALAVRAS_GEOPOLITICA):
            return 'geopolitica'
        
        # PRIORIDADE 3: NACIONAL (se for do Brasil)
        if fonte_pais == 'Brasil' or any(p in texto for p in cls.PALAVRAS_NACIONAL):
            return 'nacional'
        
        # PADRÃO: Internacional
        return 'internacional'

classificador = ClassificadorNoticias()

# ============================================
# DETECTOR DE DUPLICATAS
# ============================================

class DetectorDuplicatas:
    """Detecta notícias similares para evitar repetição"""
    
    @staticmethod
    def sao_similares(titulo1, titulo2):
        """Verifica se dois títulos são similares"""
        # Remove pontuação e espaços extras
        t1 = re.sub(r'[^\w\s]', '', titulo1.lower()).strip()
        t2 = re.sub(r'[^\w\s]', '', titulo2.lower()).strip()
        
        # Se são idênticos
        if t1 == t2:
            return True
        
        # Se um contém o outro
        if len(t1) > 10 and len(t2) > 10:
            if t1 in t2 or t2 in t1:
                return True
        
        # Calcula similaridade por palavras
        palavras1 = set(t1.split())
        palavras2 = set(t2.split())
        
        if len(palavras1) > 3 and len(palavras2) > 3:
            intersecao = palavras1.intersection(palavras2)
            similaridade = len(intersecao) / max(len(palavras1), len(palavras2))
            return similaridade > 0.65  # 65% similar
        
        return False

detector = DetectorDuplicatas()

# ============================================
# SISTEMA DE PRIORIDADE
# ============================================

class SistemaPrioridade:
    """Define quanto tempo cada notícia deve ficar"""
    
    PRIORIDADE_ALTA = 5  # dias
    PRIORIDADE_MEDIA = 3  # dias
    PRIORIDADE_BAIXA = 1  # dia
    
    FONTES_PRIORITARIAS = [
        'Brasil de Fato', 'MST', 'Al Jazeera', 'The Intercept',
        'Democracy Now', 'TeleSUR', 'Jacobin', 'Carta Capital'
    ]
    
    @classmethod
    def calcular_prioridade(cls, titulo, fonte):
        """Retorna dias que a notícia deve ficar"""
        titulo_lower = titulo.lower()
        
        # Fontes prioritárias
        if fonte in cls.FONTES_PRIORITARIAS:
            return cls.PRIORIDADE_ALTA
        
        # Conteúdo urgente
        if any(p in titulo_lower for p in ['urgente', 'breaking', 'ao vivo', 'agora']):
            return cls.PRIORIDADE_ALTA
        
        # Conteúdo relevante
        if any(p in titulo_lower for p in ['guerra', 'conflito', 'protesto', 'greve']):
            return cls.PRIORIDADE_MEDIA
        
        # Padrão
        return cls.PRIORIDADE_BAIXA

prioridade = SistemaPrioridade()

# ============================================
# SCRAPER GENÉRICO PARA SITES SEM RSS
# ============================================

class ScraperGenerico:
    """Tenta extrair notícias de qualquer site"""
    
    @staticmethod
    def extrair_noticias(url_base):
        """Tenta encontrar títulos e links em qualquer site"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = requests.get(url_base, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            noticias = []
            
            # Procura por links com textos significativos
            for link in soup.find_all('a', href=True):
                texto = link.get_text().strip()
                href = link['href']
                
                if texto and len(texto) > 20 and len(texto) < 100:
                    # Ignora links de navegação
                    if any(p in texto.lower() for p in ['menu', 'login', 'cadastro', 'home']):
                        continue
                    
                    # Constrói URL completa
                    if href.startswith('/'):
                        href = url_base + href
                    elif not href.startswith('http'):
                        href = url_base + '/' + href
                    
                    noticias.append({
                        'titulo': texto,
                        'link': href
                    })
            
            return noticias[:10]  # Retorna as 10 primeiras
            
        except Exception as e:
            logger.debug(f"Erro no scraper genérico: {e}")
            return []

# ============================================
# FONTES CONFIÁVEIS (120+ FONTES)
# ============================================

FONTES_CONFIAVEIS = [
    # ===== ANTIFA (Lutas sociais) - 35 FONTES =====
    {'nome': 'Brasil de Fato', 'pais': 'Brasil', 'url': 'https://www.brasildefato.com.br/rss', 'categoria_base': 'antifa', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'MST', 'pais': 'Brasil', 'url': 'https://mst.org.br/feed/', 'categoria_base': 'antifa', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Outras Palavras', 'pais': 'Brasil', 'url': 'https://outraspalavras.net/feed/', 'categoria_base': 'antifa', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Esquerda.net', 'pais': 'Portugal', 'url': 'https://www.esquerda.net/rss.xml', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Its Going Down', 'pais': 'USA', 'url': 'https://itsgoingdown.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'CrimethInc', 'pais': 'Global', 'url': 'https://crimethinc.com/feeds/all.atom.xml', 'categoria_base': 'antifa', 'continente': 'Global', 'prioridade': 'alta'},
    {'nome': 'ROAR Magazine', 'pais': 'Global', 'url': 'https://roarmag.org/feed/', 'categoria_base': 'antifa', 'continente': 'Global', 'prioridade': 'alta'},
    {'nome': 'Truthout', 'pais': 'USA', 'url': 'https://truthout.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Novara Media', 'pais': 'UK', 'url': 'https://novaramedia.com/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Open Democracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/en/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Common Dreams', 'pais': 'USA', 'url': 'https://www.commondreams.org/feed', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Black Agenda Report', 'pais': 'USA', 'url': 'https://blackagendareport.com/feed', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'The Canary', 'pais': 'UK', 'url': 'https://www.thecanary.co/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Red Pepper', 'pais': 'UK', 'url': 'https://www.redpepper.org.uk/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Ceasefire Magazine', 'pais': 'UK', 'url': 'https://ceasefiremagazine.co.uk/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Green Left', 'pais': 'Australia', 'url': 'https://www.greenleft.org.au/feed', 'categoria_base': 'antifa', 'continente': 'Oceania', 'prioridade': 'media'},
    {'nome': 'Peoples Dispatch', 'pais': 'India', 'url': 'https://peoplesdispatch.org/feed/', 'categoria_base': 'antifa', 'continente': 'Asia', 'prioridade': 'alta'},
    {'nome': 'Resumen Latinoamericano', 'pais': 'Argentina', 'url': 'https://www.resumenlatinoamericano.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'La Izquierda Diario', 'pais': 'Mexico', 'url': 'https://www.laizquierdadiario.mx/feed', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'ANRed', 'pais': 'Argentina', 'url': 'https://www.anred.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'CounterPunch', 'pais': 'USA', 'url': 'https://www.counterpunch.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'ZNet', 'pais': 'USA', 'url': 'https://znetwork.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Toward Freedom', 'pais': 'USA', 'url': 'https://towardfreedom.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'Waging Nonviolence', 'pais': 'USA', 'url': 'https://wagingnonviolence.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Popular Resistance', 'pais': 'USA', 'url': 'https://popularresistance.org/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Labor Notes', 'pais': 'USA', 'url': 'https://labornotes.org/feed', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Organizing Work', 'pais': 'USA', 'url': 'https://organizing.work/feed/', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'Briarpatch Magazine', 'pais': 'Canada', 'url': 'https://briarpatchmagazine.com/feed', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'Canadian Dimension', 'pais': 'Canada', 'url': 'https://canadiandimension.com/feed', 'categoria_base': 'antifa', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'Peace News', 'pais': 'UK', 'url': 'https://peacenews.info/feed', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'baixa'},
    {'nome': 'SchNEWS', 'pais': 'UK', 'url': 'https://www.schnews.org.uk/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'baixa'},
    {'nome': 'Freedom News', 'pais': 'UK', 'url': 'https://freedomnews.org.uk/feed/', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'baixa'},
    {'nome': 'Libcom.org', 'pais': 'UK', 'url': 'https://libcom.org/feed', 'categoria_base': 'antifa', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Anarkismo.net', 'pais': 'Global', 'url': 'https://www.anarkismo.net/feed', 'categoria_base': 'antifa', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'A-Infos', 'pais': 'Global', 'url': 'https://www.ainfos.ca/feed', 'categoria_base': 'antifa', 'continente': 'Global', 'prioridade': 'baixa'},
    
    # ===== GEOPOLÍTICA - 30 FONTES =====
    {'nome': 'Al Jazeera', 'pais': 'Qatar', 'url': 'https://www.aljazeera.com/xml/rss/all.xml', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'Middle East Eye', 'pais': 'UK', 'url': 'https://www.middleeasteye.net/rss', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'The Palestine Chronicle', 'pais': 'Palestina', 'url': 'https://www.palestinechronicle.com/feed/', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'Mondoweiss', 'pais': 'USA', 'url': 'https://mondoweiss.net/feed/', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'Electronic Intifada', 'pais': 'Palestina', 'url': 'https://electronicintifada.net/rss.xml', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'Le Monde Diplomatique', 'pais': 'França', 'url': 'https://mondediplo.com/feed', 'categoria_base': 'geopolitica', 'continente': 'Europa', 'prioridade': 'alta'},
    {'nome': 'MintPress News', 'pais': 'USA', 'url': 'https://www.mintpressnews.com/feed', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'Antiwar.com', 'pais': 'USA', 'url': 'https://antiwar.com/feed/', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'TeleSUR', 'pais': 'Venezuela', 'url': 'https://www.telesurtv.net/feed', 'categoria_base': 'geopolitica', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Público', 'pais': 'Portugal', 'url': 'https://feeds.feedburner.com/PublicoRSS', 'categoria_base': 'geopolitica', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Foreign Policy', 'pais': 'USA', 'url': 'https://foreignpolicy.com/feed/', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'The Diplomat', 'pais': 'Japão', 'url': 'https://thediplomat.com/feed/', 'categoria_base': 'geopolitica', 'continente': 'Asia', 'prioridade': 'media'},
    {'nome': 'War on the Rocks', 'pais': 'USA', 'url': 'https://warontherocks.com/feed/', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Small Wars Journal', 'pais': 'USA', 'url': 'https://smallwarsjournal.com/feed', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'Council on Hemispheric Affairs', 'pais': 'USA', 'url': 'https://coha.org/feed/', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'NACLA', 'pais': 'USA', 'url': 'https://nacla.org/feed', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'MERIP', 'pais': 'USA', 'url': 'https://merip.org/feed/', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'Jadaliyya', 'pais': 'USA', 'url': 'https://www.jadaliyya.com/feed', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'Al-Shabaka', 'pais': 'Palestina', 'url': 'https://al-shabaka.org/feed/', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},
    {'nome': 'B\'Tselem', 'pais': 'Israel', 'url': 'https://www.btselem.org/feed', 'categoria_base': 'geopolitica', 'continente': 'Oriente Medio', 'prioridade': 'alta'},  # ← CORRIGIDO!
    {'nome': 'IRIN News', 'pais': 'Global', 'url': 'https://www.irinnews.org/feed', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'The New Humanitarian', 'pais': 'Global', 'url': 'https://www.thenewhumanitarian.org/feed', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'Refworld', 'pais': 'Global', 'url': 'https://www.refworld.org/feed', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'baixa'},
    {'nome': 'ICRC News', 'pais': 'Global', 'url': 'https://www.icrc.org/en/rss', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'UN News', 'pais': 'Global', 'url': 'https://news.un.org/feed/view/en', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'ReliefWeb', 'pais': 'Global', 'url': 'https://reliefweb.int/feed', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'Chatham House', 'pais': 'UK', 'url': 'https://www.chathamhouse.org/feed', 'categoria_base': 'geopolitica', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'ICG', 'pais': 'Global', 'url': 'https://www.crisisgroup.org/feed', 'categoria_base': 'geopolitica', 'continente': 'Global', 'prioridade': 'alta'},
    {'nome': 'Stratfor', 'pais': 'USA', 'url': 'https://worldview.stratfor.com/feed', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Geopolitical Monitor', 'pais': 'Canada', 'url': 'https://www.geopoliticalmonitor.com/feed/', 'categoria_base': 'geopolitica', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    
    # ===== NACIONAL (Brasil) - 25 FONTES =====
    {'nome': 'Carta Capital', 'pais': 'Brasil', 'url': 'https://www.cartacapital.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'The Intercept Brasil', 'pais': 'Brasil', 'url': 'https://theintercept.com/brasil/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Brasil 247', 'pais': 'Brasil', 'url': 'https://www.brasil247.com/feed', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Diário do Centro do Mundo', 'pais': 'Brasil', 'url': 'https://www.diariodocentrodomundo.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Revista Fórum', 'pais': 'Brasil', 'url': 'https://revistaforum.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Jornal GGN', 'pais': 'Brasil', 'url': 'https://jornalggn.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Conversa Afiada', 'pais': 'Brasil', 'url': 'https://conversaafiada.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Agência Pública', 'pais': 'Brasil', 'url': 'https://apublica.org/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Repórter Brasil', 'pais': 'Brasil', 'url': 'https://reporterbrasil.org.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'De Olho nos Ruralistas', 'pais': 'Brasil', 'url': 'https://deolhonosruralistas.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Observatório do Clima', 'pais': 'Brasil', 'url': 'https://www.oc.eco.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'InfoAmazônia', 'pais': 'Brasil', 'url': 'https://infoamazonia.org/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Amazonia Real', 'pais': 'Brasil', 'url': 'https://amazoniareal.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Sul21', 'pais': 'Brasil', 'url': 'https://www.sul21.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Brasil de Fato RS', 'pais': 'Brasil', 'url': 'https://www.brasildefators.com.br/feed', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Brasil de Fato MG', 'pais': 'Brasil', 'url': 'https://www.brasildefatomg.com.br/feed', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Brasil de Fato SP', 'pais': 'Brasil', 'url': 'https://www.brasildefatosp.com.br/feed', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Brasil de Fato PE', 'pais': 'Brasil', 'url': 'https://www.brasildefatope.com.br/feed', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Brasil de Fato BA', 'pais': 'Brasil', 'url': 'https://www.brasildefatoba.com.br/feed', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Mídia Ninja', 'pais': 'Brasil', 'url': 'https://midianinja.org/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Jornalistas Livres', 'pais': 'Brasil', 'url': 'https://jornalistaslivres.org/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Ponte Jornalismo', 'pais': 'Brasil', 'url': 'https://ponte.org/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'Agência Mural', 'pais': 'Brasil', 'url': 'https://www.agenciamural.org.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Marco Zero Conteúdo', 'pais': 'Brasil', 'url': 'https://marcozero.org/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Coletivo Bereia', 'pais': 'Brasil', 'url': 'https://coletivobereia.com.br/feed/', 'categoria_base': 'nacional', 'continente': 'America do Sul', 'prioridade': 'baixa'},
    
    # ===== INTERNACIONAL - 30 FONTES =====
    {'nome': 'El País América', 'pais': 'Espanha', 'url': 'https://elpais.com/america/feed/', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'alta'},
    {'nome': 'Pagina 12', 'pais': 'Argentina', 'url': 'https://www.pagina12.com.ar/rss', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'alta'},
    {'nome': 'La Jornada', 'pais': 'Mexico', 'url': 'https://www.jornada.com.mx/rss', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'The Intercept', 'pais': 'USA', 'url': 'https://theintercept.com/feed/?lang=en', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'Jacobin', 'pais': 'USA', 'url': 'https://jacobin.com/feed', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'alta'},
    {'nome': 'The Guardian', 'pais': 'UK', 'url': 'https://www.theguardian.com/world/rss', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Le Monde', 'pais': 'França', 'url': 'https://www.lemonde.fr/rss', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Der Spiegel', 'pais': 'Alemanha', 'url': 'https://www.spiegel.de/international/index.rss', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'El Diario', 'pais': 'Espanha', 'url': 'https://www.eldiario.es/rss', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Clarin', 'pais': 'Argentina', 'url': 'https://www.clarin.com/rss', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'baixa'},
    {'nome': 'La Tercera', 'pais': 'Chile', 'url': 'https://www.latercera.com/feed/', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'baixa'},
    {'nome': 'El Comercio', 'pais': 'Peru', 'url': 'https://elcomercio.pe/feed/', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'baixa'},
    {'nome': 'El Universal', 'pais': 'Mexico', 'url': 'https://www.eluniversal.com.mx/rss', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'La República', 'pais': 'Colombia', 'url': 'https://www.larepublica.co/feed', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'baixa'},
    {'nome': 'Folha de SP', 'pais': 'Brasil', 'url': 'https://feeds.folha.uol.com.br/mundo/rss091.xml', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'O Globo', 'pais': 'Brasil', 'url': 'https://oglobo.globo.com/rss/mundo', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'Estadão', 'pais': 'Brasil', 'url': 'https://www.estadao.com.br/rss/internacional', 'categoria_base': 'internacional', 'continente': 'America do Sul', 'prioridade': 'media'},
    {'nome': 'BBC Brasil', 'pais': 'UK', 'url': 'https://www.bbc.com/portuguese/feed', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'alta'},
    {'nome': 'Deutsche Welle', 'pais': 'Alemanha', 'url': 'https://www.dw.com/feed/portuguese', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'alta'},
    {'nome': 'RFI', 'pais': 'França', 'url': 'https://www.rfi.fr/feed/portuguese', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'alta'},
    {'nome': 'Voice of America', 'pais': 'USA', 'url': 'https://www.voanews.com/feed', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Global Voices', 'pais': 'Global', 'url': 'https://globalvoices.org/feed/', 'categoria_base': 'internacional', 'continente': 'Global', 'prioridade': 'alta'},
    {'nome': 'IPS News', 'pais': 'Global', 'url': 'https://www.ipsnews.net/feed/', 'categoria_base': 'internacional', 'continente': 'Global', 'prioridade': 'alta'},
    {'nome': 'The Conversation', 'pais': 'Global', 'url': 'https://theconversation.com/global/feed', 'categoria_base': 'internacional', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'Equal Times', 'pais': 'Global', 'url': 'https://www.equaltimes.org/feed', 'categoria_base': 'internacional', 'continente': 'Global', 'prioridade': 'media'},
    {'nome': 'openDemocracy', 'pais': 'UK', 'url': 'https://www.opendemocracy.net/feed', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'alta'},
    {'nome': 'New Internationalist', 'pais': 'UK', 'url': 'https://newint.org/feed', 'categoria_base': 'internacional', 'continente': 'Europa', 'prioridade': 'media'},
    {'nome': 'Yes! Magazine', 'pais': 'USA', 'url': 'https://www.yesmagazine.org/feed', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'media'},
    {'nome': 'Resilience', 'pais': 'USA', 'url': 'https://www.resilience.org/feed/', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'baixa'},
    {'nome': 'Shareable', 'pais': 'USA', 'url': 'https://www.shareable.net/feed/', 'categoria_base': 'internacional', 'continente': 'America do Norte', 'prioridade': 'baixa'},
]

# TOTAL: 35 + 30 + 25 + 30 = 120 FONTES!

# ============================================
# SCRAPER DO GLINT.TRADE (ANONIMIZADO)
# ============================================

class GlintTradeScraper:
    def __init__(self):
        self.url_base = "https://glint.trade"
        self.ultima_busca = None
        
    def buscar_noticias(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = requests.get(self.url_base, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            titulos = []
            
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                texto = tag.get_text().strip()
                if texto and len(texto) > 15 and len(texto) < 100:
                    if not any(p in texto.lower() for p in ['menu', 'login', 'sign']):
                        titulos.append(texto)
            
            for link in soup.find_all('a', href=True):
                texto = link.get_text().strip()
                href = link['href']
                if texto and len(texto) > 15 and len(texto) < 80:
                    if href.startswith('/'):
                        href = self.url_base + href
                    elif not href.startswith('http'):
                        href = self.url_base + '/' + href
                    
                    titulos.append({
                        'texto': texto,
                        'link': href
                    })
            
            noticias_glint = []
            for item in titulos[:8]:
                if isinstance(item, str):
                    titulo = item
                    link = self.url_base
                else:
                    titulo = item['texto']
                    link = item['link']
                
                # Usa classificador automático
                categoria = classificador.classificar(titulo, '', 'Global', 'Análise Global')
                
                noticias_glint.append({
                    'titulo': titulo,
                    'titulo_traduzido': tradutor.traduzir(titulo),
                    'link': link,
                    'categoria': categoria,
                })
            
            return noticias_glint
            
        except Exception as e:
            logger.debug(f"[Glint] Erro: {e}")
            return []

glint_scraper = GlintTradeScraper()

# ============================================
# SISTEMA DE RADAR (ATUALIZADO)
# ============================================

@dataclass
class Noticia:
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
    data_coleta: str  # Data em que foi coletada
    dias_para_expirar: int = 3  # Dias que vai ficar
    destaque: bool = False

class RadarAutomatico:
    def __init__(self):
        self.fontes_ativas = []
        self.estatisticas = {
            'fontes_funcionando': 0,
            'continentes': set(),
            'paises': set(),
            'categorias': defaultdict(int),
            'antifa': 0,
            'geopolitica': 0,
            'nacional': 0,
            'internacional': 0,
        }
        self.radar_ativo = False
        self.ultimas_fontes = []  # Para controle do rodízio
        
    def iniciar_radar_automatico(self):
        if self.radar_ativo:
            return
        self.radar_ativo = True
        thread = threading.Thread(target=self._loop_radar)
        thread.daemon = True
        thread.start()
        logger.info("[Radar] Radar automatico iniciado - 120 fontes em rodízio")
    
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
        logger.info(f"[Radar] [{horario_brasilia()}] Iniciando varredura - 120 fontes em rodízio")
        logger.info(f"{'='*60}")
        
        noticias_antigas = self._carregar_noticias()
        
        # ===== EXPURGO AUTOMÁTICO =====
        noticias_antigas = self._expurgar_noticias_antigas(noticias_antigas)
        
        links_antigos = {n.link for n in noticias_antigas}
        todas_noticias_novas = []
        
        # ===== SELECIONA FONTES PARA ESTA VARREDURA (RODÍZIO) =====
        fontes_para_varrer = self._selecionar_fontes_rodizio()
        
        # ===== BUSCA NAS FONTES SELECIONADAS =====
        for fonte in fontes_para_varrer:
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
                            
                            # FILTRO DE CONTEÚDO SEM PROPÓSITO
                            titulo_lower = entrada.title.lower()
                            palavra_proibida = False
                            for palavra in PALAVRAS_PROIBIDAS:
                                if palavra in titulo_lower:
                                    palavra_proibida = True
                                    break
                            if palavra_proibida:
                                continue
                            
                            # VERIFICA DUPLICATA POR SIMILARIDADE
                            duplicata = False
                            for noticia_existente in noticias_antigas:
                                if detector.sao_similares(entrada.title, noticia_existente.titulo_original):
                                    duplicata = True
                                    break
                            if duplicata:
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
                            logger.info(f"  [OK] {fonte['categoria_base'].upper()}: {fonte['nome']} - {len(noticias_fonte)} noticias")
            except Exception as e:
                logger.debug(f"  [Falha] {fonte['nome']}")
        
        # ===== BUSCA NO GLINT.TRADE =====
        try:
            noticias_glint = glint_scraper.buscar_noticias()
            for item in noticias_glint:
                if item['link'] in links_antigos:
                    continue
                
                # Verifica duplicata
                duplicata = False
                for noticia_existente in noticias_antigas:
                    if detector.sao_similares(item['titulo'], noticia_existente.titulo_original):
                        duplicata = True
                        break
                if duplicata:
                    continue
                
                categoria = item['categoria']
                dias_expirar = prioridade.calcular_prioridade(item['titulo'], 'Análise Global')
                
                noticia = Noticia(
                    id=hashlib.md5(item['link'].encode()).hexdigest()[:8],
                    fonte='Análise Global',
                    pais='Global',
                    continente='Global',
                    categoria=categoria,
                    titulo=item['titulo_traduzido'],
                    titulo_original=item['titulo'],
                    resumo=f"Análise sobre {item['titulo_traduzido'][:50]}...",
                    resumo_original=item['titulo'],
                    link=item['link'],
                    data=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    publicada_em=horario_brasilia(),
                    data_coleta=datetime.now().strftime('%Y-%m-%d'),
                    dias_para_expirar=dias_expirar
                )
                todas_noticias_novas.append(noticia)
                self.estatisticas[categoria] += 1
                logger.info(f"  [OK] Análise Global ({categoria}): +1")
        except Exception as e:
            logger.debug(f"  [Falha] Análise Global")
        
        if todas_noticias_novas:
            todas_noticias = todas_noticias_novas + noticias_antigas
            todas_noticias.sort(key=lambda x: x.data, reverse=True)
            todas_noticias = todas_noticias[:config.MAX_NOTICIAS_TOTAL]
            
            # Define destaques (5 mais recentes)
            for i, n in enumerate(todas_noticias[:5]):
                n.destaque = True
            
            self._salvar_noticias(todas_noticias)
            
            # Atualiza estatísticas
            antifa = [n for n in todas_noticias if n.categoria == 'antifa']
            geo = [n for n in todas_noticias if n.categoria == 'geopolitica']
            nac = [n for n in todas_noticias if n.categoria == 'nacional']
            inter = [n for n in todas_noticias if n.categoria == 'internacional']
            
            logger.info(f"\n[OK] Varredura concluida")
            logger.info(f"  ANTIFA: {len(antifa)}")
            logger.info(f"  GEOPOLÍTICA: {len(geo)}")
            logger.info(f"  NACIONAL: {len(nac)}")
            logger.info(f"  INTERNACIONAL: {len(inter)}")
            logger.info(f"  TOTAL: {len(todas_noticias)}")
    
    def _selecionar_fontes_rodizio(self):
        """Seleciona 40 fontes diferentes a cada ciclo"""
        total_fontes = len(FONTES_CONFIAVEIS)
        
        # Se não tem histórico, embaralha
        if not self.ultimas_fontes:
            indices = list(range(total_fontes))
            random.shuffle(indices)
            self.ultimas_fontes = indices[:config.FONTES_POR_VARREDURA]
        else:
            # Pega os próximos índices
            ultimo_indice = (self.ultimas_fontes[-1] + 1) % total_fontes
            novos_indices = []
            for i in range(config.FONTES_POR_VARREDURA):
                idx = (ultimo_indice + i) % total_fontes
                novos_indices.append(idx)
            self.ultimas_fontes = novos_indices
        
        fontes_selecionadas = [FONTES_CONFIAVEIS[i] for i in self.ultimas_fontes]
        logger.info(f"  Rodízio: {len(fontes_selecionadas)} fontes selecionadas")
        return fontes_selecionadas
    
    def _expurgar_noticias_antigas(self, noticias):
        """Remove notícias com mais de 3 dias (ou conforme prioridade)"""
        hoje = datetime.now()
        noticias_recentes = []
        
        for n in noticias:
            try:
                data_coleta = datetime.strptime(n.data_coleta, '%Y-%m-%d')
                dias_passados = (hoje - data_coleta).days
                
                # Se ainda está dentro do prazo, mantém
                if dias_passados <= n.dias_para_expirar:
                    noticias_recentes.append(n)
            except:
                # Se não conseguir parsear a data, mantém por segurança
                noticias_recentes.append(n)
        
        expurgadas = len(noticias) - len(noticias_recentes)
        if expurgadas > 0:
            logger.info(f"  Expurgo: {expurgadas} notícias antigas removidas")
        
        return noticias_recentes
    
    def _criar_noticia(self, fonte, entrada):
        try:
            titulo_original = entrada.title
            titulo_traduzido = tradutor.traduzir(titulo_original)
            
            resumo_original = ""
            if hasattr(entrada, 'summary') and entrada.summary:
                resumo_original = BeautifulSoup(entrada.summary, 'html.parser').get_text()
            elif hasattr(entrada, 'description') and entrada.description:
                resumo_original = BeautifulSoup(entrada.description, 'html.parser').get_text()
            elif hasattr(entrada, 'content') and entrada.content:
                for content in entrada.content:
                    if content.get('type') == 'text/html' and content.value:
                        resumo_original = BeautifulSoup(content.value, 'html.parser').get_text()
                        if resumo_original:
                            break
            
            if not resumo_original or len(resumo_original.strip()) < 20:
                resumo_original = f"Leia o artigo completo sobre: {titulo_original[:100]}..."
            
            resumo_traduzido = tradutor.traduzir(resumo_original) if resumo_original else ""
            
            if resumo_traduzido and len(resumo_traduzido) > 200:
                resumo_traduzido = resumo_traduzido[:200] + "..."
            elif not resumo_traduzido:
                resumo_traduzido = "Clique para ler o artigo completo."
            
            # CLASSIFICAÇÃO AUTOMÁTICA
            categoria = classificador.classificar(
                titulo_original, 
                resumo_original, 
                fonte['pais'], 
                fonte['nome']
            )
            
            # PRIORIDADE (dias para expirar)
            dias_expirar = prioridade.calcular_prioridade(titulo_original, fonte['nome'])
            
            return Noticia(
                id=hashlib.md5(entrada.link.encode()).hexdigest()[:8],
                fonte=fonte['nome'],
                pais=fonte['pais'],
                continente=fonte['continente'],
                categoria=categoria,
                titulo=titulo_traduzido,
                titulo_original=titulo_original,
                resumo=resumo_traduzido,
                resumo_original=resumo_original[:200] + "..." if resumo_original and len(resumo_original) > 200 else resumo_original,
                link=entrada.link,
                data=entrada.get('published', datetime.now().strftime('%Y-%m-%d %H:%M')),
                publicada_em=horario_brasilia(),
                data_coleta=datetime.now().strftime('%Y-%m-%d'),
                dias_para_expirar=dias_expirar
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
                            # Compatibilidade com versões anteriores
                            if 'data_coleta' not in n:
                                n['data_coleta'] = n.get('data', datetime.now().strftime('%Y-%m-%d'))[:10]
                            if 'dias_para_expirar' not in n:
                                n['dias_para_expirar'] = 3
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
        'Alemanha': '🇩🇪',
        'Italia': '🇮🇹',
        'Australia': '🇦🇺',
        'India': '🇮🇳',
        'Japão': '🇯🇵',
        'China': '🇨🇳',
        'Russia': '🇷🇺',
        'Canada': '🇨🇦',
        'Chile': '🇨🇱',
        'Peru': '🇵🇪',
        'Colombia': '🇨🇴',
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
    contador_visitas.registrar_visita()
    total_visitas = contador_visitas.get_total()
    
    noticias = radar._carregar_noticias()
    
    # Separação por categoria
    antifa = [n for n in noticias if n.categoria == 'antifa']
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    nacionais = [n for n in noticias if n.categoria == 'nacional']
    internacionais = [n for n in noticias if n.categoria == 'internacional']
    destaques = [n for n in noticias if n.destaque][:5]
    
    destaques_html = ''
    for n in destaques:
        bandeira = get_bandeira(n.pais)
        destaques_html += f'''
        <div class="destaque-card" data-categoria="{n.categoria}">
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
            <p>🔍 Radar em operacao... buscando informacoes em 120 fontes</p>
        </div>
        '''
    
    antifa_html = ''
    for n in antifa[:12]:
        bandeira = get_bandeira(n.pais)
        antifa_html += f'''
        <div class="noticia antifa" data-categoria="antifa">
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
    
    geo_html = ''
    for n in geopolitica[:12]:
        bandeira = get_bandeira(n.pais)
        geo_html += f'''
        <div class="noticia" data-categoria="geopolitica">
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
        <div class="noticia nacional" data-categoria="nacional">
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
        <div class="noticia internacional" data-categoria="internacional">
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
                <button class="filtro-btn" data-filtro="antifa" onclick="filtrarNoticias('antifa')">🏴 ANTIFA <span class="contador">{len(antifa)}</span></button>
                <button class="filtro-btn" data-filtro="geopolitica" onclick="filtrarNoticias('geopolitica')">⚔️ GEOPOLÍTICA <span class="contador">{len(geopolitica)}</span></button>
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
            <div class="coluna" id="coluna-antifa" data-categoria="antifa">
                <h2>🏴 ANTIFA <span class="badge" id="contador-antifa">{len(antifa)}</span></h2>
                <div id="noticias-antifa">{antifa_html if antifa_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando movimentos de resistência...</p></div>'}</div>
            </div>
            <div class="coluna" id="coluna-geopolitica" data-categoria="geopolitica">
                <h2>⚔️ GEOPOLÍTICA <span class="badge" id="contador-geopolitica">{len(geopolitica)}</span></h2>
                <div id="noticias-geopolitica">{geo_html if geo_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando conflitos e análises...</p></div>'}</div>
            </div>
            <div class="coluna" id="coluna-nacional" data-categoria="nacional">
                <h2>📰 NACIONAL <span class="badge" id="contador-nacional">{len(nacionais)}</span></h2>
                <div id="noticias-nacional">{nacional_html if nacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias do Brasil...</p></div>'}</div>
            </div>
            <div class="coluna" id="coluna-internacional" data-categoria="internacional">
                <h2>🌎 INTERNACIONAL <span class="badge" id="contador-internacional">{len(internacionais)}</span></h2>
                <div id="noticias-internacional">{internacional_html if internacional_html else '<div class="mensagem-vazia"><div class="loading-animation"></div><p>Buscando notícias do mundo...</p></div>'}</div>
            </div>
        </div>
        
        <div class="footer">
            <a href="https://www.instagram.com/sharp.front16.rj?igsh=MXd1cjF2aTI2OGc1eQ==" target="_blank" class="instagram-link">@sharp.front16.rj</a>
            <div class="footer-stats">
                <span>🇧🇷 Horário Brasília</span>
                <span>📰 {len(noticias)} notícias</span>
                <span>👥 {total_visitas} visitas</span>
            </div>
            <div class="footer-stats">
                <span>🏴 {len(antifa)}</span>
                <span>⚔️ {len(geopolitica)}</span>
                <span>🇧🇷 {len(nacionais)}</span>
                <span>🌎 {len(internacionais)}</span>
            </div>
            <div class="footer-copyright">SHARP - FRONT 16 RJ • Informação com propósito</div>
            <div class="footer-copyright" style="color: #555;">120 fontes • Atualizado a cada 10 minutos • Notícias duram até 3 dias</div>
            <div class="footer-versao">v29.0 • 120+ Fontes • Classificador Automático • Expurgo 3 dias</div>
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
                case 'antifa':
                    colunas.forEach(col => col.style.display = col.dataset.categoria === 'antifa' ? 'block' : 'none');
                    destaques.style.display = 'none';
                    break;
                case 'geopolitica':
                    colunas.forEach(col => col.style.display = col.dataset.categoria === 'geopolitica' ? 'block' : 'none');
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
    
    antifa = [n for n in noticias if n.categoria == 'antifa']
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    nacionais = [n for n in noticias if n.categoria == 'nacional']
    internacionais = [n for n in noticias if n.categoria == 'internacional']
    
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
            .categoria-row {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 10px; background: #1a1a1a; border-radius: 5px; }}
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
                <p><strong>Fontes ativas:</strong> {radar.estatisticas['fontes_funcionando']} de 120</p>
                <p><strong>Horário:</strong> {horario_brasilia()}</p>
            </div>
            
            <h2>Distribuição por categoria:</h2>
            <div class="categoria-row">
                <span>🏴 ANTIFA</span> <strong>{len(antifa)} notícias</strong>
            </div>
            <div class="categoria-row">
                <span>⚔️ GEOPOLÍTICA</span> <strong>{len(geopolitica)} notícias</strong>
            </div>
            <div class="categoria-row">
                <span>🇧🇷 NACIONAL</span> <strong>{len(nacionais)} notícias</strong>
            </div>
            <div class="categoria-row">
                <span>🌎 INTERNACIONAL</span> <strong>{len(internacionais)} notícias</strong>
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
    
    antifa = [n for n in noticias if n.categoria == 'antifa']
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    nacionais = [n for n in noticias if n.categoria == 'nacional']
    internacionais = [n for n in noticias if n.categoria == 'internacional']
    
    return jsonify({
        'total_visitas': total_visitas,
        'total_noticias': len(noticias),
        'antifa': len(antifa),
        'geopolitica': len(geopolitica),
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
    logger.info("SHARP - FRONT 16 RJ - RADAR ANTIFA v29.0 - INFINITY")
    logger.info("="*70)
    
    noticias = radar._carregar_noticias()
    total_visitas = contador_visitas.get_total()
    
    antifa = [n for n in noticias if n.categoria == 'antifa']
    geopolitica = [n for n in noticias if n.categoria == 'geopolitica']
    nacionais = [n for n in noticias if n.categoria == 'nacional']
    internacionais = [n for n in noticias if n.categoria == 'internacional']
    
    logger.info(f"Acervo inicial: {len(noticias)} noticias")
    logger.info(f"  ANTIFA: {len(antifa)}")
    logger.info(f"  GEOPOLÍTICA: {len(geopolitica)}")
    logger.info(f"  NACIONAL: {len(nacionais)}")
    logger.info(f"  INTERNACIONAL: {len(internacionais)}")
    logger.info(f"Fontes configuradas: {len(FONTES_CONFIAVEIS)} (120 fontes)")
    logger.info(f"Contador de visitas: iniciando em {total_visitas}")
    
    radar.iniciar_radar_automatico()
    logger.info("Radar automatico ativado - Rodízio de 40 fontes por ciclo")
    
    anti_sono = SistemaAntiSono()
    anti_sono.iniciar()
    logger.info("✅ Sistema Anti-Sono ativado")
    logger.info("✅ Tradutor ativo - Notícias em Português")
    logger.info("✅ 120+ fontes organizadas por categoria")
    logger.info("✅ Classificador automático de notícias")
    logger.info("✅ Detector de duplicatas por similaridade")
    logger.info("✅ Expurgo automático após 3 dias")
    logger.info("✅ Sistema de prioridade (notícias importantes duram mais)")
    logger.info("✅ Rodízio de fontes para não sobrecarregar")
    logger.info("="*70)

inicializar()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
