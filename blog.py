#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SHARP - FRONT 16 RJ                                        ║
║              SISTEMA SUPREMO ANTIFA - VERSÃO 18.0 - FINAL                    ║
║         RADAR AUTOMATICO COM FILTROS POR CATEGORIA - NOTÍCIAS EM PT          ║
║              "A informacao e nossa arma mais poderosa"                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# [Toda a parte inicial do código permanece IGUAL até a função home]
# ...

# ============================================
# PAGINA PRINCIPAL - VERSÃO FINAL
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
    
    # HTML dos destaques (igual)
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
    
    # HTML Nacionais - CORRIGIDO: apenas "BR NACIONAL" (sem bandeira)
    nacional_html = ''
    for n in nacionais[:12]:
        bandeira = get_bandeira(n.pais)
        nacional_html += f'''
        <div class="noticia nacional" data-categoria="{n.categoria}" data-pais="Brasil">
            <div class="noticia-header">
                <span class="fonte">{bandeira} {n.fonte}</span>
                <span class="pais">BR NACIONAL</span>
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
            
            /* TÍTULO COM SIMBOLOS - COMUNISMO DO MESMO TAMANHO */
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
                line-height: 1;
            }}
            
            .simbolo-comunista {{
                color: #ff0000;
                font-size: 1.8rem;
                filter: drop-shadow(0 0 5px rgba(255,0,0,0.5));
                line-height: 1;
                transform: translateY(2px);
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
            
            /* RODAPÉ COM INSTAGRAM VERMELHO - SEM "fontes" */
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
            
            <!-- COLUNA NACIONAL - CORRIGIDA: "BR NACIONAL" sem bandeira -->
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
        
        <!-- RODAPÉ - SEM "fontes" -->
        <div class="footer">
            <!-- LINK DO INSTAGRAM VERMELHO -->
            <a href="https://www.instagram.com/sharp.front16.rj?igsh=MXd1cjF2aTI2OGc1eQ==" target="_blank" class="instagram-link">
                @sharp.front16.rj
            </a>
            
            <div class="footer-stats">
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
                v18.0 • Notícias em Português
            </div>
        </div>

        <!-- SCRIPT DE FILTROS (igual) -->
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
# RESTO DO CÓDIGO PERMANECE IGUAL
# ============================================
