# FieldOps Copilot

POC de um assistente operacional que futuramente poderá receber mensagens de texto e áudio pelo WhatsApp para consultar estoque, vendas e compras.

## Etapa 1

Esta primeira etapa entrega um núcleo HTTP pequeno e determinístico:

- SQLite com dados fictícios;
- consulta de estoque por produto;
- listagem de produtos abaixo do estoque mínimo;
- resumo de vendas por período;
- testes automatizados sem dependência de serviços externos.

O agente, WhatsApp e transcrição de áudio entram nas próximas etapas. A regra é manter o domínio independente do canal de entrada.

## Executando localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn fieldops.api:app --reload
```

Depois, abra `http://127.0.0.1:8000/docs`.

## Testes

```powershell
pytest
```

## Próximas etapas

1. Adicionar ferramentas de negócio tipadas e uma camada de orquestração.
2. Criar adapter de mensagens para a WhatsApp Cloud API.
3. Adicionar confirmação explícita para operações que alteram dados.
4. Adicionar áudio, transcrição local e auditoria das interações.
