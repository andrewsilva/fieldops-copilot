# FieldOps Copilot

POC de um assistente operacional que futuramente poderá receber mensagens de texto e áudio pelo WhatsApp para consultar estoque, vendas e compras.

## Etapas 1 a 5

Esta primeira etapa entrega um núcleo HTTP pequeno e determinístico:

- SQLite com dados fictícios;
- consulta de estoque por produto;
- listagem de produtos abaixo do estoque mínimo;
- resumo de vendas por período;
- testes automatizados sem dependência de serviços externos.
- catálogo de ferramentas tipadas para o agente;
- orquestrador determinístico para perguntas em português;
- endpoint `POST /chat` com registro da ferramenta e dos argumentos usados.
- integração opcional com o Groq para melhorar a redação da resposta.
- adapter inicial da WhatsApp Cloud API para verificação, recebimento e envio de mensagens.

Sem credenciais da Meta, o adapter apenas devolve a resposta calculada. Com as
credenciais configuradas, ele envia a resposta pela Cloud API.

## Executando localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn fieldops.api:app --reload
```

Depois, abra `http://127.0.0.1:8000/docs`.

Exemplo de chamada:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/chat -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"Quais produtos estão com baixo estoque?"}'
```

### Groq opcional

Crie uma chave no [Groq Console](https://console.groq.com/keys) e configure-a
somente no ambiente local:

```powershell
$env:GROQ_API_KEY = "sua-chave-aqui"
```

O modelo padrão é `llama-3.1-8b-instant`. Para usar o Groq na resposta:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/chat -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"Quais produtos estão com baixo estoque?","use_groq":true}'
```

Sem `GROQ_API_KEY`, o modo Groq retorna erro explicitamente. Sem `use_groq`,
nenhuma chamada externa é feita e o agente determinístico continua sendo usado.

## Testes

```powershell
pytest
```

## Webhook da WhatsApp Cloud API

Configure o token usado pela verificação da Meta:

```powershell
$env:WHATSAPP_VERIFY_TOKEN = "fieldops-dev"
$env:WHATSAPP_ACCESS_TOKEN = "seu-token-da-meta"
$env:WHATSAPP_PHONE_NUMBER_ID = "id-do-numero-de-teste"
```

Cadastre `https://seu-host/webhooks/whatsapp` como callback URL. O `GET` responde
ao desafio da Meta e o `POST` processa mensagens de texto. Quando as credenciais
estão configuradas, a resposta também é enviada ao remetente. Mensagens de áudio
são reconhecidas, mas ainda aguardam a etapa de transcrição.

## Próximas etapas

1. Adicionar áudio, download de mídia e transcrição.
2. Adicionar confirmação explícita para operações que alteram dados.
3. Adicionar auditoria persistente das interações.
