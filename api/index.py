from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
import io
import json

app = FastAPI()

# Permitir que o Front-end aceda à API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simulação de base de dados em memória (No futuro, use um banco real)
# A Vercel limpa a memória entre requisições, por isso o Front-end deve enviar os dados
base_dados = {"chamadas": [], "satisfacao": []}

def converter_tempo_para_segundos(tempo_str):
    try:
        h, m, s = map(int, tempo_str.split(':'))
        return h * 3600 + m * 60 + s
    except:
        return 0

def formatar_segundos(segundos):
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

@app.post("/api/processar")
async def processar_arquivos(files: List[UploadFile] = File(...)):
    global base_dados
    for file in files:
        content = await file.read()
        # Detecta se é o CSV de chamadas ou satisfação baseado nas colunas
        df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding='utf-8')
        
        if 'TMA' in df.columns or 'Fila' in df.columns:
            base_dados["chamadas"] = df.to_dict('records')
        elif 'Nota' in df.columns or 'CSAT' in df.columns:
            base_dados["satisfacao"] = df.to_dict('records')
            
    return {"status": "sucesso", "mensagem": "Arquivos processados com Pandas"}

@app.get("/api/dashboard")
async def get_dashboard(inicio: str, fim: str):
    df = pd.DataFrame(base_dados["chamadas"])
    if df.empty:
        return {"kpis": {"atendidas": 0, "ns": 0, "tma": "00:00:00", "abandono": 0, "csat": 0, "nps": 0}, "performance": []}

    # Lógica de Filtro de Data
    df['Data'] = pd.to_datetime(df['Data'])
    mask = (df['Data'] >= inicio) & (df['Data'] <= fim)
    df_filtrado = df.loc[mask]

    # Cálculos de KPI
    total_atendidas = len(df_filtrado[df_filtrado['Status'] == 'Atendida'])
    total_recebidas = len(df_filtrado)
    tma_medio = df_filtrado['TMA_Segundos'].mean() if 'TMA_Segundos' in df_filtrado else 0
    
    # Cálculo de NS (exemplo: atendidas em até 20s)
    ns_valor = (len(df_filtrado[df_filtrado['Espera'] <= 20]) / total_recebidas * 100) if total_recebidas > 0 else 0

    # Estrutura de Performance Individual
    performance = []
    for nome, grupo in df_filtrado.groupby('Atendente'):
        performance.append({
            "nome": nome,
            "atendidas": len(grupo),
            "ns": round((len(grupo[grupo['Espera'] <= 20]) / len(grupo) * 100), 1),
            "tma": formatar_segundos(grupo['TMA_Segundos'].mean()) if 'TMA_Segundos' in grupo else "00:00:00",
            "tmr": "00:00:00",
            "csat": 0 # Integração com a outra base
        })

    return {
        "kpis": {
            "atendidas": total_atendidas,
            "ns": round(ns_valor, 1),
            "tma": formatar_segundos(tma_medio),
            "abandono": round((len(df_filtrado[df_filtrado['Status'] == 'Abandonada']) / total_recebidas * 100), 1) if total_recebidas > 0 else 0,
            "csat": 85, # Exemplo fixo, pode ser calculado da base_dados["satisfacao"]
            "nps": 75
        },
        "performance": performance
    }
