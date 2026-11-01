# FieldOps Copilot

POC de um assistente operacional que futuramente poderá receber mensagens de texto e áudio pelo WhatsApp para consultar estoque, vendas e compras.

## Etapas 1 e 2

Esta primeira etapa entrega um núcleo HTTP pequeno e determinístico:

- SQLite com dados fictícios;
- consulta de estoque por produto;
- listagem de produtos abaixo do estoque mínimo;
- resumo de vendas por período;
- testes automatizados sem dependência de serviços externos.
- catálogo de ferramentas tipadas para o agente;
- orquestrador determinístico para perguntas em português;
- endpoint `POST /chat` com registro da ferramenta e dos argumentos usados.
- integração opcional com um modelo local via Ollama para melhorar a redação da resposta.

O modelo de linguagem, WhatsApp e transcrição de áudio entram nas próximas etapas. A regra é manter o domínio independente do canal de entrada.

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

### Modelo local opcional

Instale o [Ollama](https://ollama.com), inicie o serviço e baixe um modelo:

```powershell
ollama pull qwen2.5:3b
```

Para usar o modelo na resposta, envie `use_local_model: true`:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/chat -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"Quais produtos estão com baixo estoque?","use_local_model":true}'
```

Sem esse campo, nenhuma chamada externa é feita e o agente determinístico continua sendo usado.

## Testes

```powershell
pytest
```

## Próximas etapas

1. Integrar um modelo local via Ollama mantendo as mesmas ferramentas.
2. Criar adapter de mensagens para a WhatsApp Cloud API.
3. Adicionar confirmação explícita para operações que alteram dados.
4. Adicionar áudio, transcrição local e auditoria das interações.
