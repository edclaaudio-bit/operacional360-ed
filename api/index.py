from fastapi import FastAPI, UploadFile, File, Query
from typing import List
import pandas as pd
import io

app = FastAPI()

# Armazenamento temporário (Para produção real, considere um banco como Supabase ou PostgreSQL)
# Na Vercel Serverless, variáveis globais não persistem entre requisições. 
# O processamento será feito sob demanda via upload.

@app.post("/api/processar")
async def processar_dados(files: List[UploadFile] = File(...)):
    combined_data = []
    for file in files:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8')
        combined_data.append(df)
    
    # Exemplo de lógica: Calcular Atendidas Totais
    df_final = pd.concat(combined_data)
    atendidas = len(df_final[df_final['tipo'] == 'Atendida'])
    
    return {
        "status": "sucesso",
        "total_atendidas": atendidas,
        "detalhes": "Processado via Python Backend"
    }

@app.get("/api/saude")
def checar_status():
    return {"status": "online", "versao": "2.0.0"}
