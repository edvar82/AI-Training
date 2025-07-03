# Verificador Automático de Tarefas de IA

Sistema que automatiza a verificação de tarefas de programação usando inteligência artificial (GPT).

## Como Usar

### Verificar todas as tarefas (modo lote):

```
python verifier.py --batch
```

### Verificar apenas tarefas de uma aula específica:

```
python verifier.py --batch --lecture lecture_1
```

### Verificar uma tarefa específica:

```
python verifier.py --script lecture_1/tasks/emailClassifier.py --output lecture_1/outputs/email_classified.txt
```

## Componentes Principais

1. **Detecção Automática**: Encontra scripts em `tasks/`, arquivos de entrada em `utils/` e saída em `outputs/`
2. **Descrições das Tarefas**: Obtidas do arquivo `task_descriptions.json` ou dos comentários nos scripts
3. **Verificação com IA**: Avalia se a saída atende aos requisitos da tarefa usando GPT
4. **Processamento Paralelo**: Utiliza multithreading para maior eficiência
5. **Relatórios**: Gera relatório individual por tarefa e resumo consolidado em Markdown

## Saídas

- **Relatórios Individuais**: `results/lecture_X/nome_tarefa_verification.txt`
- **Relatório Consolidado**: `verification_summary.md`

## Estrutura de Diretórios Esperada

```
.
├── lecture_1/
│   ├── tasks/        # Scripts Python com as tarefas
│   ├── utils/        # Arquivos de entrada
│   └── outputs/      # Resultados dos scripts
├── lecture_2/
│   ├── tasks/
│   ├── utils/
│   └── outputs/
├── results/          # Relatórios de verificação
├── task_descriptions.json
└── verifier.py
```
