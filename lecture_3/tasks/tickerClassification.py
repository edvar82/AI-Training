from collections import defaultdict
import re
import os

PRIORITY_KEYWORDS = {
    'High': [
        r'\b(urgent|immediate|critical|crash|error|broken|não funciona|bloqueado|trava|emergency)\b',
        r'\bnão consigo\b.*\b(acessar|logar|entrar|trabalhar)\b',
        r'\bperdendo\b.*\b(dados|clientes|vendas)\b',
        r'\bsegurança\b',
        r'\btempo limite excedido\b'
    ],
    'Medium': [
        r'\b(importante|intermittente|inconsistente|lento|slow|performance|delay|bug|problema)\b',
        r'\bdificuldade\b.*\b(usar|completar|encontrar)\b',
        r'\bfuncionalidade\b.*\b(não está funcionando corretamente|parcialmente)\b'
    ],
    'Low': [
        r'\b(sugestão|suggestion|enhancement|melhoria|feature|recurso|cosmético|visual|typo|erro de digitação)\b',
        r'\bseria bom\b',
        r'\bpoderia\b.*\b(adicionar|melhorar|atualizar)\b'
    ]
}

CATEGORY_KEYWORDS = {
    'Bug': [
        r'\b(bug|erro|crash|falha|defeito|não funciona|incorreto|comportamento inesperado)\b',
        r'\b(exception|stack trace|null pointer|undefined)\b',
        r'\bquebrado\b',
        r'\bdeixou de funcionar\b'
    ],
    'Question': [
        r'\b(como|how|help|ajuda|dúvida|pergunta|question|instruções|instructions)\b',
        r'\b(posso|pode|consegue)\b.*\?',
        r'\bpreciso saber\b',
        r'\bnão sei\b.*\bcomo\b'
    ],
    'Feature Request': [
        r'\b(feature|recurso|função|adicionar|add|implementar|implement|novo|new|enhancement|melhoria)\b',
        r'\b(gostaria|would like|it would be nice|seria bom|sugestão|suggestion)\b',
        r'\bpoderia incluir\b',
        r'\bfalta\b.*\bfuncionalidade\b'
    ],
    'Account': [
        r'\b(conta|account|login|senha|password|acesso|access|perfil|profile|cadastro|register)\b',
        r'\bnão consigo\b.*\b(entrar|logar|acessar)\b',
        r'\besqueci\b.*\b(senha|password)\b'
    ],
    'Performance': [
        r'\b(lento|slow|performance|desempenho|rápido|fast|otimizar|optimize|travando|freezing|delay|atraso)\b',
        r'\btempo de resposta\b',
        r'\bconsumo\b.*\b(memória|cpu|processador|bateria)\b'
    ]
}

def read_tickets(file_path):
    """Lê tickets de suporte de um arquivo"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_entities(ticket_text):
    """Extrai entidades relevantes do texto do ticket"""
    entities = {}
    
    patterns = {
        'username': r'(?:Username|User|Nome de usuário|Usuário):\s*([^\n]+)',
        'os': r'(?:OS|Operating System|Sistema Operacional):\s*([^\n]+)',
        'software_version': r'(?:Version|Versão|Software Version):\s*([^\n]+)',
        'description': r'(?:Description|Descrição|Issue|Problema):\s*([^\n]+(?:\n(?!\s*(?:Username|User|OS|Version|Priority|Category)).*)*)'
    }
    
    for entity, pattern in patterns.items():
        match = re.search(pattern, ticket_text, re.IGNORECASE)
        if match:
            entities[entity] = match.group(1).strip()
        else:
            entities[entity] = "Not specified"
    
    return entities

def classify_priority(description):
    """Classifica a prioridade com base nas palavras-chave"""
    for priority, patterns in PRIORITY_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return priority
    return "Low"  

def classify_category(description):
    """Classifica a categoria com base nas palavras-chave"""
    categories = []
    for category, patterns in CATEGORY_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                categories.append(category)
                break 
    
    if not categories:
        return ["Other"] 
    return list(set(categories))  

def classify_tickets(tickets_text):
    """Processa o texto completo de tickets e classifica cada um"""
    # Dividir o texto em tickets individuais
    ticket_pattern = r'(?:Ticket|Chamado)\s+#\d+\s*\n(.*?)(?=(?:Ticket|Chamado)\s+#\d+|\Z)'
    tickets = re.findall(ticket_pattern, tickets_text, re.DOTALL)
    
    results = []
    for ticket in tickets:
        entities = extract_entities(ticket)
        priority = classify_priority(entities.get('description', ''))
        categories = classify_category(entities.get('description', ''))
        
        result = {
            'username': entities.get('username', 'Not specified'),
            'os': entities.get('os', 'Not specified'),
            'software_version': entities.get('software_version', 'Not specified'),
            'description': entities.get('description', 'Not specified'),
            'priority': priority,
            'categories': categories
        }
        results.append(result)
    
    return results

def save_classification(classified_tickets, output_file):
    """Salva a classificação em um arquivo de texto formatado"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write("# Classificação de Tickets de Suporte\n\n")
        
        file.write("## Resumo\n\n")
        file.write(f"Total de tickets: {len(classified_tickets)}\n\n")
        
        priority_counts = defaultdict(int)
        for ticket in classified_tickets:
            priority_counts[ticket['priority']] += 1
        
        file.write("### Distribuição por Prioridade\n")
        for priority, count in priority_counts.items():
            file.write(f"- {priority}: {count} ({count/len(classified_tickets)*100:.1f}%)\n")
        file.write("\n")
        
        category_counts = defaultdict(int)
        for ticket in classified_tickets:
            for category in ticket['categories']:
                category_counts[category] += 1
        
        file.write("### Distribuição por Categoria\n")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            file.write(f"- {category}: {count}\n")
        file.write("\n")
        
        file.write("## Detalhes dos Tickets\n\n")
        for i, ticket in enumerate(classified_tickets, 1):
            file.write(f"### Ticket #{i}\n")
            file.write(f"**Usuário:** {ticket['username']}\n")
            file.write(f"**Sistema Operacional:** {ticket['os']}\n")
            file.write(f"**Versão do Software:** {ticket['software_version']}\n")
            file.write(f"**Prioridade:** {ticket['priority']}\n")
            file.write(f"**Categorias:** {', '.join(ticket['categories'])}\n")
            file.write(f"**Descrição:** {ticket['description'][:150]}{'...' if len(ticket['description']) > 150 else ''}\n\n")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tickets_path = os.path.join(os.path.dirname(current_dir), "utils", "tickets.txt")
    output_path = os.path.join(os.path.dirname(current_dir), "outputs", "ticketClassification.txt")
    
    tickets_text = read_tickets(tickets_path)
    classified_tickets = classify_tickets(tickets_text)
    save_classification(classified_tickets, output_path)
    
    print(f"Classificação concluída. Resultados salvos em {output_path}")