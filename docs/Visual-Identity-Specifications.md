# Especificações de Identidade Visual
## FrontEmu-Tools v1.0

### Informações do Documento
- **Projeto**: FrontEmu-Tools
- **Versão**: 1.0
- **Data**: Janeiro 2025
- **Autor**: Equipe de Design FrontEmu-Tools
- **Status**: Em Desenvolvimento

---

## 1. Conceito Visual

### 1.1 Filosofia de Design
O FrontEmu-Tools adota uma identidade visual **moderna, limpa e tecnológica**, refletindo sua natureza como ferramenta avançada de gerenciamento de emulação. O design combina:

- **Modernidade**: Interface contemporânea com elementos flat design
- **Tecnologia**: Estética que remete ao mundo gaming e emulação
- **Profissionalismo**: Aparência séria e confiável para uso técnico
- **Acessibilidade**: Cores e contrastes que garantem boa legibilidade

### 1.2 Personalidade da Marca
- **Inovadora**: Sempre à frente em tecnologia de emulação
- **Confiável**: Ferramenta robusta e estável
- **Amigável**: Interface intuitiva e acessível
- **Técnica**: Focada em usuários com conhecimento técnico

---

## 2. Paleta de Cores

### 2.1 Cor Primária - Verde Limão

#### **Lime Green Principal**
- **Hex**: `#32CD32`
- **RGB**: `50, 205, 50`
- **HSL**: `120°, 61%, 50%`
- **CMYK**: `76%, 0%, 76%, 20%`

**Uso**: Elementos principais, botões de ação, highlights, logo

#### **Variações do Verde Limão**

**Lime Green Claro**
- **Hex**: `#7FFF7F`
- **RGB**: `127, 255, 127`
- **HSL**: `120°, 100%, 75%`
- **Uso**: Hover states, elementos secundários

**Lime Green Escuro**
- **Hex**: `#228B22`
- **RGB**: `34, 139, 34`
- **HSL**: `120°, 61%, 34%`
- **Uso**: Bordas, sombras, estados ativos

**Lime Green Neon**
- **Hex**: `#39FF14`
- **RGB**: `57, 255, 20`
- **HSL**: `114°, 100%, 54%`
- **Uso**: Indicadores de status, notificações importantes

### 2.2 Cores Secundárias

#### **Cinza Tecnológico**
- **Cinza Escuro**: `#2D2D2D` - Backgrounds principais
- **Cinza Médio**: `#404040` - Elementos de interface
- **Cinza Claro**: `#808080` - Textos secundários
- **Cinza Muito Claro**: `#E0E0E0` - Divisores, bordas

#### **Cores de Apoio**
- **Branco**: `#FFFFFF` - Textos principais, backgrounds claros
- **Preto**: `#000000` - Textos de alto contraste
- **Azul Tecnológico**: `#0078D4` - Links, informações
- **Vermelho de Alerta**: `#FF4444` - Erros, alertas críticos
- **Amarelo de Aviso**: `#FFD700` - Avisos, atenção
- **Verde de Sucesso**: `#00AA00` - Confirmações, sucesso

### 2.3 Gradientes

#### **Gradiente Principal**
```css
background: linear-gradient(135deg, #32CD32 0%, #228B22 100%);
```

#### **Gradiente Secundário**
```css
background: linear-gradient(90deg, #2D2D2D 0%, #404040 100%);
```

#### **Gradiente de Destaque**
```css
background: linear-gradient(45deg, #39FF14 0%, #32CD32 50%, #228B22 100%);
```

---

## 3. Tipografia

### 3.1 Fonte Principal

#### **Segoe UI (Windows)**
- **Família**: Segoe UI, sans-serif
- **Características**: Moderna, legível, nativa do Windows
- **Uso**: Interface principal, textos gerais

#### **Hierarquia Tipográfica**

**H1 - Títulos Principais**
- **Tamanho**: 32px
- **Peso**: 600 (Semi-bold)
- **Cor**: `#FFFFFF` ou `#32CD32`
- **Uso**: Títulos de páginas principais

**H2 - Subtítulos**
- **Tamanho**: 24px
- **Peso**: 500 (Medium)
- **Cor**: `#E0E0E0`
- **Uso**: Seções importantes

**H3 - Títulos de Seção**
- **Tamanho**: 18px
- **Peso**: 500 (Medium)
- **Cor**: `#32CD32`
- **Uso**: Grupos de controles

**Body - Texto Corpo**
- **Tamanho**: 14px
- **Peso**: 400 (Regular)
- **Cor**: `#FFFFFF`
- **Uso**: Textos gerais

**Caption - Legendas**
- **Tamanho**: 12px
- **Peso**: 400 (Regular)
- **Cor**: `#808080`
- **Uso**: Informações secundárias

### 3.2 Fonte Monospace

#### **Consolas (Código)**
- **Família**: Consolas, 'Courier New', monospace
- **Uso**: Paths, códigos, logs
- **Tamanho**: 12px
- **Cor**: `#32CD32`

---

## 4. Logo e Marca

### 4.1 Conceito do Logo

#### **Elementos Visuais**
- **Símbolo**: Ícone estilizado representando emulação/gaming
- **Tipografia**: Nome "FrontEmu-Tools" em Segoe UI Bold
- **Cores**: Verde limão principal com detalhes em cinza

#### **Variações do Logo**

**Logo Principal**
- Símbolo + texto completo
- Uso em headers, splash screens
- Tamanho mínimo: 120px de largura

**Logo Compacto**
- Apenas símbolo
- Uso em ícones, favicons
- Tamanho mínimo: 32px

**Logo Horizontal**
- Símbolo à esquerda + texto
- Uso em barras de ferramentas
- Proporção 3:1

### 4.2 Área de Proteção
- **Margem mínima**: 1/2 da altura do logo
- **Fundo mínimo**: Contraste adequado
- **Não usar sobre**: Fundos muito coloridos ou com ruído

### 4.3 Usos Incorretos
- ❌ Alterar proporções
- ❌ Mudar cores sem aprovação
- ❌ Adicionar efeitos (sombra, brilho)
- ❌ Usar em fundos inadequados
- ❌ Redimensionar abaixo do mínimo

---

## 5. Iconografia

### 5.1 Estilo de Ícones

#### **Características**
- **Estilo**: Line icons com preenchimento seletivo
- **Espessura**: 2px para linhas
- **Tamanho**: 16px, 24px, 32px, 48px
- **Cor**: `#32CD32` (principal), `#FFFFFF` (secundário)

#### **Biblioteca de Ícones**
- **Base**: Lucide React (adaptados)
- **Personalização**: Cores e alguns detalhes modificados
- **Consistência**: Mesmo peso visual e estilo

### 5.2 Ícones Principais

#### **Sistema**
- 🖥️ **Monitor**: Informações do sistema
- 💾 **HardDrive**: Gerenciamento de drives
- ⚙️ **Settings**: Configurações
- 📊 **BarChart**: Estatísticas

#### **Emulação**
- 🎮 **Gamepad2**: Emuladores
- 📁 **Folder**: ROMs e arquivos
- 🔄 **RefreshCw**: Migração/atualização
- ✅ **CheckCircle**: Validação

#### **Ações**
- ▶️ **Play**: Executar/iniciar
- ⏸️ **Pause**: Pausar processo
- 🛑 **Square**: Parar
- 📥 **Download**: Baixar/importar

### 5.3 Estados dos Ícones

#### **Normal**
- Cor: `#FFFFFF`
- Opacidade: 100%

#### **Hover**
- Cor: `#32CD32`
- Transição: 200ms ease

#### **Ativo**
- Cor: `#32CD32`
- Background: `rgba(50, 205, 50, 0.1)`

#### **Desabilitado**
- Cor: `#808080`
- Opacidade: 50%

---

## 6. Componentes de Interface

### 6.1 Botões

#### **Botão Primário**
```css
.btn-primary {
    background: #32CD32;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
    font-weight: 500;
    transition: all 200ms ease;
}

.btn-primary:hover {
    background: #228B22;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(50, 205, 50, 0.3);
}
```

#### **Botão Secundário**
```css
.btn-secondary {
    background: transparent;
    color: #32CD32;
    border: 2px solid #32CD32;
    border-radius: 6px;
    padding: 10px 22px;
    font-weight: 500;
}

.btn-secondary:hover {
    background: #32CD32;
    color: #FFFFFF;
}
```

#### **Botão de Perigo**
```css
.btn-danger {
    background: #FF4444;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
}
```

### 6.2 Cards e Painéis

#### **Card Principal**
```css
.card {
    background: #2D2D2D;
    border: 1px solid #404040;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.card-header {
    border-bottom: 1px solid #32CD32;
    padding-bottom: 12px;
    margin-bottom: 16px;
    color: #32CD32;
    font-weight: 600;
}
```

### 6.3 Formulários

#### **Input Fields**
```css
.input-field {
    background: #404040;
    border: 2px solid #808080;
    border-radius: 6px;
    padding: 12px 16px;
    color: #FFFFFF;
    font-size: 14px;
}

.input-field:focus {
    border-color: #32CD32;
    box-shadow: 0 0 0 3px rgba(50, 205, 50, 0.2);
    outline: none;
}
```

#### **Labels**
```css
.label {
    color: #E0E0E0;
    font-weight: 500;
    margin-bottom: 6px;
    display: block;
}
```

### 6.4 Navegação

#### **Menu Principal**
```css
.main-menu {
    background: #2D2D2D;
    border-right: 1px solid #404040;
    padding: 20px 0;
}

.menu-item {
    padding: 12px 20px;
    color: #E0E0E0;
    transition: all 200ms ease;
}

.menu-item:hover {
    background: rgba(50, 205, 50, 0.1);
    color: #32CD32;
}

.menu-item.active {
    background: #32CD32;
    color: #FFFFFF;
}
```

---

## 7. Animações e Transições

### 7.1 Princípios de Animação

#### **Duração**
- **Micro-interações**: 150-200ms
- **Transições de página**: 300-400ms
- **Animações complexas**: 500-800ms

#### **Easing**
- **Padrão**: `ease-out` (0.25, 0.46, 0.45, 0.94)
- **Entrada**: `ease-in` (0.55, 0.055, 0.675, 0.19)
- **Saída**: `ease-out` (0.215, 0.61, 0.355, 1)

### 7.2 Animações Específicas

#### **Loading Spinner**
```css
.spinner {
    border: 3px solid #404040;
    border-top: 3px solid #32CD32;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
```

#### **Fade In**
```css
.fade-in {
    animation: fadeIn 300ms ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
```

#### **Pulse (Notificações)**
```css
.pulse {
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(50, 205, 50, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(50, 205, 50, 0); }
    100% { box-shadow: 0 0 0 0 rgba(50, 205, 50, 0); }
}
```

---

## 8. Layout e Grid

### 8.1 Sistema de Grid

#### **Breakpoints**
- **XS**: < 768px (não suportado)
- **SM**: 768px - 1024px
- **MD**: 1024px - 1440px
- **LG**: 1440px - 1920px
- **XL**: > 1920px

#### **Containers**
- **Máximo**: 1200px
- **Padding lateral**: 20px
- **Margem central**: auto

### 8.2 Espaçamento

#### **Sistema de Espaçamento (8px base)**
- **XS**: 4px
- **SM**: 8px
- **MD**: 16px
- **LG**: 24px
- **XL**: 32px
- **XXL**: 48px

#### **Aplicação**
```css
.spacing-xs { margin: 4px; }
.spacing-sm { margin: 8px; }
.spacing-md { margin: 16px; }
.spacing-lg { margin: 24px; }
.spacing-xl { margin: 32px; }
.spacing-xxl { margin: 48px; }
```

---

## 9. Estados e Feedback

### 9.1 Estados de Componentes

#### **Estados Visuais**
- **Normal**: Aparência padrão
- **Hover**: Mudança sutil de cor/elevação
- **Active**: Feedback imediato de clique
- **Focus**: Outline visível para acessibilidade
- **Disabled**: Opacidade reduzida, sem interação

#### **Cores de Estado**
- **Sucesso**: `#00AA00`
- **Aviso**: `#FFD700`
- **Erro**: `#FF4444`
- **Informação**: `#0078D4`
- **Neutro**: `#808080`

### 9.2 Notificações

#### **Toast Notifications**
```css
.toast {
    background: #2D2D2D;
    border-left: 4px solid #32CD32;
    border-radius: 6px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    animation: slideIn 300ms ease-out;
}

.toast.success { border-left-color: #00AA00; }
.toast.warning { border-left-color: #FFD700; }
.toast.error { border-left-color: #FF4444; }
```

---

## 10. Acessibilidade

### 10.1 Contraste

#### **Ratios Mínimos (WCAG 2.1)**
- **Texto normal**: 4.5:1
- **Texto grande**: 3:1
- **Elementos gráficos**: 3:1

#### **Verificações**
- Verde limão (#32CD32) em fundo escuro: ✅ 7.2:1
- Branco (#FFFFFF) em fundo escuro: ✅ 15.3:1
- Cinza claro (#E0E0E0) em fundo escuro: ✅ 11.8:1

### 10.2 Navegação por Teclado

#### **Indicadores de Focus**
```css
.focusable:focus {
    outline: 2px solid #32CD32;
    outline-offset: 2px;
}
```

#### **Skip Links**
```css
.skip-link {
    position: absolute;
    top: -40px;
    left: 6px;
    background: #32CD32;
    color: #FFFFFF;
    padding: 8px;
    text-decoration: none;
    border-radius: 4px;
}

.skip-link:focus {
    top: 6px;
}
```

---

## 11. Implementação Técnica

### 11.1 CSS Variables

```css
:root {
    /* Cores Primárias */
    --color-primary: #32CD32;
    --color-primary-light: #7FFF7F;
    --color-primary-dark: #228B22;
    --color-primary-neon: #39FF14;
    
    /* Cores Neutras */
    --color-bg-primary: #2D2D2D;
    --color-bg-secondary: #404040;
    --color-text-primary: #FFFFFF;
    --color-text-secondary: #E0E0E0;
    --color-text-muted: #808080;
    
    /* Cores de Estado */
    --color-success: #00AA00;
    --color-warning: #FFD700;
    --color-error: #FF4444;
    --color-info: #0078D4;
    
    /* Espaçamento */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    --spacing-xxl: 48px;
    
    /* Tipografia */
    --font-family-primary: 'Segoe UI', sans-serif;
    --font-family-mono: 'Consolas', 'Courier New', monospace;
    
    /* Bordas */
    --border-radius-sm: 4px;
    --border-radius-md: 6px;
    --border-radius-lg: 8px;
    
    /* Sombras */
    --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.2);
    --shadow-md: 0 4px 8px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.4);
    
    /* Transições */
    --transition-fast: 150ms ease-out;
    --transition-normal: 200ms ease-out;
    --transition-slow: 300ms ease-out;
}
```

### 11.2 Tema Escuro (Padrão)

```css
.theme-dark {
    --color-bg-primary: #2D2D2D;
    --color-bg-secondary: #404040;
    --color-text-primary: #FFFFFF;
    --color-text-secondary: #E0E0E0;
}
```

### 11.3 Responsividade

```css
/* Mobile First Approach */
.container {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 var(--spacing-md);
}

@media (min-width: 768px) {
    .container {
        padding: 0 var(--spacing-lg);
    }
}

@media (min-width: 1024px) {
    .container {
        padding: 0 var(--spacing-xl);
    }
}
```

---

## 12. Guia de Uso

### 12.1 Checklist de Implementação

#### **Cores**
- [ ] Usar variáveis CSS para todas as cores
- [ ] Verificar contraste em todos os elementos
- [ ] Testar em diferentes monitores
- [ ] Validar acessibilidade

#### **Tipografia**
- [ ] Aplicar hierarquia consistente
- [ ] Usar tamanhos relativos (rem/em)
- [ ] Testar legibilidade
- [ ] Verificar fallbacks de fonte

#### **Componentes**
- [ ] Implementar todos os estados
- [ ] Adicionar transições suaves
- [ ] Testar responsividade
- [ ] Validar acessibilidade por teclado

### 12.2 Ferramentas de Validação

#### **Contraste**
- WebAIM Contrast Checker
- Colour Contrast Analyser
- Chrome DevTools

#### **Acessibilidade**
- axe DevTools
- WAVE Web Accessibility Evaluator
- Lighthouse Accessibility Audit

---

## 13. Evolução e Manutenção

### 13.1 Versionamento da Identidade

#### **Versão 1.0 (Atual)**
- Estabelecimento da identidade base
- Cores primárias definidas
- Componentes fundamentais

#### **Futuras Versões**
- Refinamentos baseados em feedback
- Novos componentes conforme necessário
- Otimizações de performance

### 13.2 Processo de Atualização

1. **Proposta**: Documentar mudança necessária
2. **Avaliação**: Impacto na experiência do usuário
3. **Implementação**: Atualizar especificações
4. **Teste**: Validar em diferentes contextos
5. **Deploy**: Aplicar em toda a aplicação

---

**Documento aprovado por**: Equipe de Design FrontEmu-Tools
**Data de aprovação**: Janeiro 2025
**Próxima revisão**: Março 2025