# Especificações de Overlay UI/UX - FrontEmu-Tools

## 1. Visão Geral

O FrontEmu-Tools utiliza um sistema de overlay avançado para fornecer informações em tempo real e controles contextuais durante a emulação, mantendo uma experiência de usuário fluida e não intrusiva.

## 2. Tipos de Overlay

### 2.1 Overlay de Status do Sistema
**Propósito**: Monitoramento em tempo real do desempenho do sistema
**Posição**: Canto superior direito
**Transparência**: 85%

#### Elementos:
- **CPU Usage**: Gráfico de barras horizontal
- **RAM Usage**: Indicador circular
- **GPU Usage**: Gráfico de linha mini
- **Temperature**: Indicador de cor (verde/amarelo/vermelho)
- **FPS Counter**: Número grande e legível

#### Comportamento:
- Auto-hide após 3 segundos de inatividade
- Reaparece com movimento do mouse
- Clique para expandir detalhes

### 2.2 Overlay de Controles de Emulação
**Propósito**: Acesso rápido a funções de emulação
**Posição**: Borda inferior, centro
**Transparência**: 90%

#### Elementos:
- **Play/Pause**: Botão principal
- **Save State**: Ícone de disquete
- **Load State**: Ícone de pasta
- **Screenshot**: Ícone de câmera
- **Settings**: Ícone de engrenagem
- **Exit**: Ícone de X

#### Comportamento:
- Slide-up animation ao aparecer
- Fade-out após 5 segundos
- Hover para manter visível

### 2.3 Overlay de Notificações
**Propósito**: Feedback visual para ações do usuário
**Posição**: Canto superior esquerdo
**Transparência**: 80%

#### Tipos de Notificação:
- **Success**: Verde limão (#32CD32)
- **Warning**: Amarelo (#FFD700)
- **Error**: Vermelho (#FF4444)
- **Info**: Azul (#4A90E2)

#### Comportamento:
- Toast animation (slide-in from left)
- Auto-dismiss após 4 segundos
- Stack múltiplas notificações

### 2.4 Overlay de Debug/Desenvolvimento
**Propósito**: Informações técnicas para desenvolvedores
**Posição**: Canto inferior esquerdo
**Transparência**: 95%

#### Elementos:
- **Frame Time**: Gráfico de linha
- **Memory Allocation**: Lista de objetos
- **API Calls**: Contador de chamadas
- **Error Log**: Últimos 5 erros

## 3. Design System

### 3.1 Cores
```css
/* Cores Primárias */
--overlay-primary: rgba(50, 205, 50, 0.9);     /* Verde Limão */
--overlay-secondary: rgba(40, 40, 40, 0.95);   /* Cinza Escuro */
--overlay-accent: rgba(255, 255, 255, 0.1);    /* Branco Transparente */

/* Estados */
--overlay-success: rgba(50, 205, 50, 0.8);
--overlay-warning: rgba(255, 215, 0, 0.8);
--overlay-error: rgba(255, 68, 68, 0.8);
--overlay-info: rgba(74, 144, 226, 0.8);
```

### 3.2 Tipografia
```css
/* Fontes */
--overlay-font-primary: 'Segoe UI', sans-serif;
--overlay-font-mono: 'Consolas', monospace;

/* Tamanhos */
--overlay-text-xs: 10px;
--overlay-text-sm: 12px;
--overlay-text-md: 14px;
--overlay-text-lg: 16px;
--overlay-text-xl: 18px;
```

### 3.3 Espaçamento
```css
/* Padding/Margin */
--overlay-space-xs: 4px;
--overlay-space-sm: 8px;
--overlay-space-md: 12px;
--overlay-space-lg: 16px;
--overlay-space-xl: 24px;
```

## 4. Animações

### 4.1 Fade In/Out
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}
```

### 4.2 Slide Animations
```css
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes slideLeft {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}
```

### 4.3 Scale Animation
```css
@keyframes scaleIn {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
```

## 5. Responsividade

### 5.1 Breakpoints
- **Small**: < 1280px
- **Medium**: 1280px - 1920px
- **Large**: > 1920px

### 5.2 Adaptações por Tamanho
```css
/* Small Screens */
@media (max-width: 1279px) {
  .overlay-element {
    font-size: var(--overlay-text-sm);
    padding: var(--overlay-space-sm);
  }
}

/* Large Screens */
@media (min-width: 1921px) {
  .overlay-element {
    font-size: var(--overlay-text-lg);
    padding: var(--overlay-space-lg);
  }
}
```

## 6. Interatividade

### 6.1 Estados de Hover
```css
.overlay-button:hover {
  background-color: var(--overlay-primary);
  transform: scale(1.05);
  transition: all 0.2s ease;
}
```

### 6.2 Estados de Foco
```css
.overlay-button:focus {
  outline: 2px solid var(--overlay-primary);
  outline-offset: 2px;
}
```

### 6.3 Estados Ativos
```css
.overlay-button:active {
  transform: scale(0.95);
  background-color: var(--overlay-secondary);
}
```

## 7. Acessibilidade

### 7.1 Contraste
- Mínimo 4.5:1 para texto normal
- Mínimo 3:1 para texto grande
- Verificação automática de contraste

### 7.2 Navegação por Teclado
- Tab order lógico
- Escape para fechar overlays
- Enter/Space para ativar botões

### 7.3 Screen Readers
```html
<!-- Exemplo de markup acessível -->
<div class="overlay-status" role="region" aria-label="System Status">
  <div class="cpu-usage" aria-label="CPU Usage: 45%">
    <span aria-hidden="true">CPU: 45%</span>
  </div>
</div>
```

## 8. Performance

### 8.1 Otimizações
- GPU acceleration para animações
- Debounce para eventos de mouse
- Lazy loading para overlays complexos
- Memory pooling para elementos reutilizáveis

### 8.2 Métricas de Performance
```css
.overlay-element {
  will-change: transform, opacity;
  transform: translateZ(0); /* Force GPU layer */
}
```

## 9. Configurabilidade

### 9.1 Opções do Usuário
- **Posição**: Customizável por overlay
- **Transparência**: Slider 0-100%
- **Auto-hide Timer**: 1-10 segundos
- **Tamanho**: Pequeno/Médio/Grande

### 9.2 Temas
```json
{
  "themes": {
    "default": {
      "primary": "#32CD32",
      "background": "rgba(40, 40, 40, 0.95)"
    },
    "dark": {
      "primary": "#00FF00",
      "background": "rgba(0, 0, 0, 0.9)"
    },
    "light": {
      "primary": "#228B22",
      "background": "rgba(255, 255, 255, 0.9)"
    }
  }
}
```

## 10. Implementação Técnica

### 10.1 Estrutura de Classes
```python
class OverlayManager:
    def __init__(self):
        self.overlays = {}
        self.config = OverlayConfig()
    
    def register_overlay(self, name: str, overlay: BaseOverlay):
        """Registra um novo overlay"""
        pass
    
    def show_overlay(self, name: str, duration: int = None):
        """Exibe um overlay específico"""
        pass
    
    def hide_overlay(self, name: str):
        """Oculta um overlay específico"""
        pass

class BaseOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_animations()
    
    def setup_ui(self):
        """Configura a interface do overlay"""
        pass
    
    def setup_animations(self):
        """Configura as animações"""
        pass
```

### 10.2 Sistema de Eventos
```python
class OverlayEventSystem:
    def __init__(self):
        self.subscribers = defaultdict(list)
    
    def subscribe(self, event_type: str, callback: callable):
        """Inscreve um callback para um tipo de evento"""
        self.subscribers[event_type].append(callback)
    
    def emit(self, event_type: str, data: dict):
        """Emite um evento para todos os subscribers"""
        for callback in self.subscribers[event_type]:
            callback(data)
```

## 11. Testes

### 11.1 Testes de Usabilidade
- Tempo de resposta < 100ms
- Visibilidade em diferentes resoluções
- Acessibilidade com screen readers

### 11.2 Testes de Performance
- FPS impact < 5%
- Memory usage < 50MB
- CPU overhead < 2%

## 12. Documentação para Desenvolvedores

### 12.1 API de Overlay
```python
# Exemplo de uso
overlay_manager = OverlayManager()

# Criar overlay customizado
custom_overlay = CustomOverlay()
overlay_manager.register_overlay("custom", custom_overlay)

# Exibir overlay
overlay_manager.show_overlay("custom", duration=5000)

# Configurar posição
overlay_manager.set_position("custom", Position.TOP_RIGHT)
```

### 12.2 Extensibilidade
- Plugin system para overlays customizados
- API para desenvolvedores terceiros
- Documentação de hooks e eventos

## 13. Roadmap

### 13.1 Versão 1.0
- ✅ Overlay básico de status
- ✅ Sistema de notificações
- ✅ Controles de emulação

### 13.2 Versão 1.1
- 🔄 Overlay de debug
- 🔄 Configurabilidade avançada
- 🔄 Temas customizáveis

### 13.3 Versão 1.2
- ⏳ Plugin system
- ⏳ API para terceiros
- ⏳ Overlay de rede/multiplayer

---

**Nota**: Este documento deve ser atualizado conforme a evolução do projeto e feedback dos usuários.