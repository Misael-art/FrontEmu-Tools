# Comandos Git para Upload - FrontEmu-Tools

## 📋 Guia Completo para Upload no GitHub

Este documento contém todos os comandos necessários para fazer o upload do projeto FrontEmu-Tools para o repositório GitHub.

## 🔧 Pré-requisitos

1. **Git instalado** no sistema
2. **Conta GitHub** configurada
3. **Acesso ao repositório**: https://github.com/Misael-art/FrontEmu-Tools.git
4. **Autenticação configurada** (SSH ou Token)

## 📁 Estrutura Atual do Projeto

```
F:\tools\FrontEmu-Tools\
├── docs/
│   ├── DRS-FrontEmu-Tools.md
│   ├── Technical-Design-Document.md
│   ├── Visual-Identity-Specifications.md
│   ├── UI-UX-Overlay-Specifications.md
│   └── uml/
│       ├── Use-Case-Diagram.md
│       ├── Class-Diagram.md
│       ├── Sequence-Diagram.md
│       └── Component-Diagram.md
├── src/                    # (vazio - para código futuro)
├── assets/                 # (vazio - para recursos visuais)
├── README.md
└── GIT-COMMANDS.md        # (este arquivo)
```

## 🚀 Comandos para Upload

### 1. Navegue até o diretório do projeto
```bash
cd F:\tools\FrontEmu-Tools
```

### 2. Inicialize o repositório Git local
```bash
git init
```

### 3. Configure o repositório remoto
```bash
git remote add origin https://github.com/Misael-art/FrontEmu-Tools.git
```

### 4. Configure informações do usuário (se necessário)
```bash
git config user.name "Seu Nome"
git config user.email "seu.email@exemplo.com"
```

### 5. Adicione todos os arquivos ao staging
```bash
git add .
```

### 6. Verifique os arquivos que serão commitados
```bash
git status
```

### 7. Faça o commit inicial
```bash
git commit -m "feat: Documentação completa do projeto FrontEmu-Tools

- Adiciona DRS (Documento de Requisitos de Software)
- Adiciona Documento de Design Técnico detalhado
- Adiciona Especificações de Identidade Visual (verde limão)
- Adiciona Especificações de Overlay UI/UX
- Adiciona Diagramas UML completos (Use Case, Classes, Sequência, Componentes)
- Adiciona README.md com visão geral do projeto
- Estabelece estrutura de diretórios para desenvolvimento futuro

Arquitetura baseada em Clean Architecture
Tecnologias: Python 3.9+, PySide6/Qt6
Foco em emulação frontend moderna e profissional"
```

### 8. Verifique se há um branch main remoto
```bash
git branch -r
```

### 9. Configure o branch principal
```bash
git branch -M main
```

### 10. Faça o push inicial
```bash
git push -u origin main
```

## 🔄 Comandos para Atualizações Futuras

### Para adicionar novos arquivos ou modificações:
```bash
# Adicionar arquivos específicos
git add nome_do_arquivo.md

# Ou adicionar todas as modificações
git add .

# Commit com mensagem descritiva
git commit -m "tipo: descrição da modificação"

# Push para o repositório
git push origin main
```

### Tipos de commit recomendados:
- `feat:` - Nova funcionalidade
- `docs:` - Documentação
- `fix:` - Correção de bug
- `refactor:` - Refatoração de código
- `style:` - Mudanças de estilo/formatação
- `test:` - Adição de testes
- `chore:` - Tarefas de manutenção

## 🔍 Comandos de Verificação

### Verificar status do repositório
```bash
git status
```

### Verificar histórico de commits
```bash
git log --oneline
```

### Verificar branches
```bash
git branch -a
```

### Verificar repositórios remotos
```bash
git remote -v
```

## 🛠️ Comandos de Troubleshooting

### Se houver conflitos com o repositório remoto:
```bash
# Baixar mudanças do remoto
git fetch origin

# Fazer merge das mudanças
git merge origin/main

# Ou fazer rebase (alternativa)
git rebase origin/main
```

### Se precisar forçar o push (use com cuidado):
```bash
git push --force-with-lease origin main
```

### Para desfazer o último commit (mantendo as mudanças):
```bash
git reset --soft HEAD~1
```

### Para desfazer mudanças não commitadas:
```bash
git checkout -- nome_do_arquivo.md
```

## 📝 Exemplo de Workflow Completo

```bash
# 1. Navegue para o diretório
cd F:\tools\FrontEmu-Tools

# 2. Inicialize o Git
git init

# 3. Adicione o repositório remoto
git remote add origin https://github.com/Misael-art/FrontEmu-Tools.git

# 4. Configure usuário (se necessário)
git config user.name "Misael"
git config user.email "misael@exemplo.com"

# 5. Adicione todos os arquivos
git add .

# 6. Verifique o status
git status

# 7. Faça o commit inicial
git commit -m "feat: Documentação completa do projeto FrontEmu-Tools"

# 8. Configure o branch principal
git branch -M main

# 9. Faça o push inicial
git push -u origin main
```

## 🔐 Autenticação

### Usando Token de Acesso Pessoal (Recomendado)
1. Gere um token em: GitHub → Settings → Developer settings → Personal access tokens
2. Use o token como senha quando solicitado

### Usando SSH (Alternativo)
```bash
# Gere uma chave SSH
ssh-keygen -t ed25519 -C "seu.email@exemplo.com"

# Adicione a chave ao ssh-agent
ssh-add ~/.ssh/id_ed25519

# Configure o repositório para usar SSH
git remote set-url origin git@github.com:Misael-art/FrontEmu-Tools.git
```

## ✅ Verificação Final

Após o upload, verifique se:
- [ ] Todos os arquivos foram enviados corretamente
- [ ] A estrutura de diretórios está preservada
- [ ] O README.md está sendo exibido na página principal
- [ ] Os diagramas Mermaid estão renderizando corretamente
- [ ] Não há arquivos sensíveis ou desnecessários

## 🎯 Próximos Passos

1. **Configurar Issues**: Criar templates para bugs e features
2. **Configurar Actions**: CI/CD para testes automatizados
3. **Configurar Releases**: Versionamento semântico
4. **Configurar Wiki**: Documentação adicional
5. **Configurar Projects**: Kanban para gerenciamento

---

**Nota**: Mantenha este arquivo atualizado conforme o projeto evolui e novos workflows são estabelecidos.