# Diagrama de Componentes - FrontEmu-Tools

## Visão Geral
Este diagrama representa a arquitetura de componentes do FrontEmu-Tools, mostrando como os diferentes módulos interagem entre si seguindo os princípios da Clean Architecture.

## Diagrama de Componentes

```mermaid
graph TB
    %% External Systems
    subgraph "🌐 Sistemas Externos"
        OS[🖥️ Sistema Operacional]
        FS[📁 Sistema de Arquivos]
        PROC[⚙️ Gerenciador de Processos]
        HW[🔧 Hardware]
    end

    %% Presentation Layer
    subgraph "🎨 Camada de Apresentação"
        subgraph "GUI Components"
            MW[🏠 MainWindow]
            CD[⚙️ ConfigDialog]
            OW[📱 OverlayWidget]
            ND[🔔 NotificationDialog]
        end
        
        subgraph "Controllers"
            EC[🎮 EmulatorController]
            SC[📊 SystemController]
            CC[📋 ConfigController]
        end
    end

    %% Application Layer
    subgraph "🔧 Camada de Aplicação"
        subgraph "Use Cases"
            EMU[🎮 EmulatorManagementUseCase]
            SMU[📊 SystemMonitoringUseCase]
            CMU[📋 ConfigManagementUseCase]
            LDU[🔍 LegacyDetectionUseCase]
        end
        
        subgraph "Application Services"
            VS[✅ ValidationService]
            NS[🔔 NotificationService]
            BS[💾 BackupService]
            LS[📝 LoggingService]
        end
    end

    %% Domain Layer
    subgraph "🏛️ Camada de Domínio"
        subgraph "Entities"
            EE[🎮 EmulatorEntity]
            RE[💿 ROMEntity]
            SSE[📊 SystemStatsEntity]
            CE[⚙️ ConfigurationEntity]
        end
        
        subgraph "Value Objects"
            PC[📂 PathConfig]
            PM[📈 PerformanceMetrics]
            VR[✅ ValidationResult]
        end
        
        subgraph "Domain Services"
            DS[🔧 DomainService]
        end
    end

    %% Infrastructure Layer
    subgraph "🏗️ Camada de Infraestrutura"
        subgraph "Repositories"
            ER[📁 EmulatorRepository]
            RR[💿 ROMRepository]
            SSR[📊 SystemStatsRepository]
            CR[⚙️ ConfigRepository]
        end
        
        subgraph "External Adapters"
            SIA[🖥️ SystemInfoAdapter]
            PMA[⚙️ ProcessManagerAdapter]
            FMA[📁 FileManagerAdapter]
            LA[📝 LoggingAdapter]
        end
        
        subgraph "Data Storage"
            JSON[📄 JSON Files]
            XML[📄 XML Files]
            CACHE[💾 Memory Cache]
            LOGS[📝 Log Files]
        end
    end

    %% Cross-Cutting Concerns
    subgraph "🔄 Aspectos Transversais"
        SEC[🔒 Security]
        PERF[⚡ Performance]
        ERR[❌ Error Handling]
        AUDIT[📋 Audit]
    end

    %% Presentation Layer Connections
    MW --> EC
    MW --> SC
    MW --> CC
    MW --> OW
    MW --> ND
    
    CD --> CC
    OW --> SC
    
    %% Controller to Use Case Connections
    EC --> EMU
    SC --> SMU
    CC --> CMU
    
    %% Use Case Connections
    EMU --> VS
    EMU --> NS
    EMU --> LS
    SMU --> NS
    SMU --> LS
    CMU --> BS
    CMU --> VS
    CMU --> NS
    LDU --> VS
    LDU --> NS

    %% Use Cases to Repositories
    EMU --> ER
    EMU --> RR
    SMU --> SSR
    CMU --> CR
    LDU --> ER

    %% Domain Layer Connections
    EMU --> EE
    EMU --> RE
    SMU --> SSE
    CMU --> CE
    
    EE --> PC
    SSE --> PM
    VS --> VR

    %% Repository to Adapter Connections
    ER --> FMA
    RR --> FMA
    SSR --> FMA
    CR --> FMA

    %% Adapter to External System Connections
    SIA --> OS
    SIA --> HW
    PMA --> PROC
    FMA --> FS
    LA --> LOGS

    %% Storage Connections
    ER --> JSON
    CR --> XML
    SSR --> CACHE
    LS --> LOGS

    %% Cross-cutting Concerns
    SEC -.-> EMU
    SEC -.-> CMU
    PERF -.-> SMU
    PERF -.-> SSR
    ERR -.-> VS
    ERR -.-> NS
    AUDIT -.-> LS

    %% Component Interfaces
    subgraph "🔌 Interfaces"
        IER[📁 IEmulatorRepository]
        IRR[💿 IROMRepository]
        ISSR[📊 ISystemStatsRepository]
        ICR[⚙️ IConfigRepository]
        ISIA[🖥️ ISystemInfoAdapter]
        IPMA[⚙️ IProcessManagerAdapter]
        IFMA[📁 IFileManagerAdapter]
    end

    %% Interface Implementations
    ER ..|> IER
    RR ..|> IRR
    SSR ..|> ISSR
    CR ..|> ICR
    SIA ..|> ISIA
    PMA ..|> IPMA
    FMA ..|> IFMA

    %% Use Cases depend on Interfaces
    EMU --> IER
    EMU --> IRR
    SMU --> ISSR
    CMU --> ICR
    SMU --> ISIA
    EMU --> IPMA
    BS --> IFMA

    %% Styling
    classDef presentationClass fill:#FF6B6B,stroke:#E55555,stroke-width:2px,color:#fff
    classDef applicationClass fill:#FFD700,stroke:#DAA520,stroke-width:2px,color:#000
    classDef domainClass fill:#32CD32,stroke:#228B22,stroke-width:2px,color:#000
    classDef infrastructureClass fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    classDef externalClass fill:#DDA0DD,stroke:#9370DB,stroke-width:2px,color:#000
    classDef crossCuttingClass fill:#FFA500,stroke:#FF8C00,stroke-width:2px,color:#000
    classDef interfaceClass fill:#F0F8FF,stroke:#4682B4,stroke-width:2px,color:#000

    class MW,CD,OW,ND,EC,SC,CC presentationClass
    class EMU,SMU,CMU,LDU,VS,NS,BS,LS applicationClass
    class EE,RE,SSE,CE,PC,PM,VR,DS domainClass
    class ER,RR,SSR,CR,SIA,PMA,FMA,LA,JSON,XML,CACHE,LOGS infrastructureClass
    class OS,FS,PROC,HW externalClass
    class SEC,PERF,ERR,AUDIT crossCuttingClass
    class IER,IRR,ISSR,ICR,ISIA,IPMA,IFMA interfaceClass
```

## Descrição dos Componentes

### 🎨 Camada de Apresentação

#### GUI Components
- **MainWindow**: Janela principal da aplicação
- **ConfigDialog**: Diálogo de configurações
- **OverlayWidget**: Widget de overlay para informações em tempo real
- **NotificationDialog**: Sistema de notificações visuais

#### Controllers
- **EmulatorController**: Controla operações relacionadas a emuladores
- **SystemController**: Controla monitoramento do sistema
- **ConfigController**: Controla gerenciamento de configurações

### 🔧 Camada de Aplicação

#### Use Cases
- **EmulatorManagementUseCase**: Gerenciamento de emuladores
- **SystemMonitoringUseCase**: Monitoramento de performance
- **ConfigManagementUseCase**: Gerenciamento de configurações
- **LegacyDetectionUseCase**: Detecção de sistemas legacy

#### Application Services
- **ValidationService**: Validação de dados e configurações
- **NotificationService**: Sistema de notificações
- **BackupService**: Backup e restauração
- **LoggingService**: Sistema de logs

### 🏛️ Camada de Domínio

#### Entities
- **EmulatorEntity**: Entidade de emulador
- **ROMEntity**: Entidade de ROM
- **SystemStatsEntity**: Entidade de estatísticas do sistema
- **ConfigurationEntity**: Entidade de configuração

#### Value Objects
- **PathConfig**: Configurações de caminhos
- **PerformanceMetrics**: Métricas de performance
- **ValidationResult**: Resultado de validação

### 🏗️ Camada de Infraestrutura

#### Repositories
- **EmulatorRepository**: Persistência de emuladores
- **ROMRepository**: Persistência de ROMs
- **SystemStatsRepository**: Persistência de estatísticas
- **ConfigRepository**: Persistência de configurações

#### External Adapters
- **SystemInfoAdapter**: Acesso a informações do sistema
- **ProcessManagerAdapter**: Gerenciamento de processos
- **FileManagerAdapter**: Operações de arquivo
- **LoggingAdapter**: Adaptador de logging

#### Data Storage
- **JSON Files**: Armazenamento em JSON
- **XML Files**: Armazenamento em XML
- **Memory Cache**: Cache em memória
- **Log Files**: Arquivos de log

## Fluxo de Dados

### 1. Fluxo de Configuração
```
User → MainWindow → ConfigController → ConfigManagementUseCase → ConfigRepository → JSON Files
```

### 2. Fluxo de Monitoramento
```
Timer → SystemMonitoringUseCase → SystemInfoAdapter → Hardware → OverlayWidget
```

### 3. Fluxo de Execução
```
User → MainWindow → EmulatorController → EmulatorManagementUseCase → ProcessManagerAdapter → OS
```

## Padrões Arquiteturais

### 1. Clean Architecture
- **Separação de responsabilidades** em camadas bem definidas
- **Inversão de dependências** através de interfaces
- **Independência de frameworks** externos

### 2. Repository Pattern
- **Abstração de persistência** de dados
- **Facilita testes** com implementações mock
- **Permite múltiplas fontes** de dados

### 3. Adapter Pattern
- **Integração com sistemas externos**
- **Abstração de APIs** do sistema operacional
- **Facilita substituição** de dependências

### 4. Observer Pattern
- **Sistema de notificações** assíncronas
- **Atualizações de UI** em tempo real
- **Desacoplamento** entre componentes

## Interfaces e Contratos

### IEmulatorRepository
```python
class IEmulatorRepository:
    def save(self, emulator: EmulatorEntity) -> bool
    def find_by_id(self, id: str) -> EmulatorEntity
    def find_all(self) -> List[EmulatorEntity]
    def delete(self, id: str) -> bool
```

### ISystemInfoAdapter
```python
class ISystemInfoAdapter:
    def get_cpu_usage(self) -> float
    def get_memory_usage(self) -> float
    def get_gpu_usage(self) -> float
    def get_temperature(self) -> float
```

### IProcessManagerAdapter
```python
class IProcessManagerAdapter:
    def start_process(self, executable: str, args: List[str]) -> Process
    def kill_process(self, pid: int) -> bool
    def is_process_running(self, pid: int) -> bool
```

## Aspectos Transversais

### 🔒 Security
- **Validação de entrada** em todos os pontos
- **Sanitização de dados** antes da persistência
- **Controle de acesso** a recursos do sistema

### ⚡ Performance
- **Caching** de dados frequentemente acessados
- **Lazy loading** de componentes pesados
- **Pooling** de recursos quando apropriado

### ❌ Error Handling
- **Tratamento consistente** de erros
- **Logging detalhado** para debugging
- **Recuperação graceful** de falhas

### 📋 Audit
- **Rastreamento de operações** críticas
- **Logs de auditoria** para compliance
- **Métricas de uso** para otimização

## Configuração e Deployment

### Configuração de Dependências
```python
# dependency_injection.py
container = Container()
container.register(IEmulatorRepository, FileSystemEmulatorRepository)
container.register(ISystemInfoAdapter, WindowsSystemInfoAdapter)
container.register(IProcessManagerAdapter, WindowsProcessManagerAdapter)
```

### Estrutura de Diretórios
```
FrontEmu-Tools/
├── src/
│   ├── presentation/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
├── tests/
├── docs/
└── config/
```

## Escalabilidade e Manutenibilidade

### 1. Modularidade
- Componentes independentes e testáveis
- Baixo acoplamento entre módulos
- Alta coesão dentro dos módulos

### 2. Extensibilidade
- Fácil adição de novos emuladores
- Plugin system para funcionalidades customizadas
- API para integrações externas

### 3. Testabilidade
- Interfaces bem definidas para mocking
- Separação clara de responsabilidades
- Testes unitários e de integração

### 4. Performance
- Arquitetura assíncrona onde apropriado
- Caching inteligente
- Monitoramento de performance integrado