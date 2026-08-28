# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router  # Importa o roteador que você criou no api.py

# Inicializa o app do FastAPI
app = FastAPI(
    title="SmartParking API",
    description="Backend em FastAPI para gerenciamento inteligente de vagas",
    version="1.0.0",
)

# Configuração obrigatória de CORS para permitir comunicação com o React Native Expo [2, 7]
# Em desenvolvimento, você pode liberar todas as origins. Em produção, limite ao necessário.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite requisições do seu app móvel [2]
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, PATCH [2, 3]
    allow_headers=["*"],
)

# Inclui as rotas do api.py na aplicação principal
app.include_router(api_router)


# Rota simples de verificação de status na raiz (opcional)
@app.get("/")
async def root():
    return {"status": "SmartParking API está rodando perfeitamente!"}


# Inicialização do servidor Uvicorn [6]
if __name__ == "__main__":
    # Rodar em 0.0.0.0 permite que seu celular/emulador na mesma rede Wi-Fi encontre o backend [6]
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

