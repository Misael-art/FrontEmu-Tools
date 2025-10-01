# Diagrama de Classes - FrontEmu-Tools

## Visão Geral
Este diagrama representa a estrutura de classes do FrontEmu-Tools seguindo os princípios da Clean Architecture.

## Diagrama de Classes

```mermaid
classDiagram
    %% Domain Layer - Entities
    class EmulatorEntity {
        +id: str
        +name: str
        +version: str
        +executable_path: str
        +config_path: str
        +supported_formats: List[str]
        +is_active: bool
        +validate() bool
        +get_config() dict
        +set_config(config: dict) void
    }

    class ROMEntity {
        +id: str
        +name: str
        +file_path: str
        +file_size: int
        +checksum: str
        +emulator_id: str
        +last_played: datetime
        +play_count: int
        +validate_integrity() bool
        +get_metadata() dict
    }

    class SystemStatsEntity {
        +timestamp: datetime
        +cpu_usage: float
        +memory_usage: float
        +gpu_usage: float
        +temperature: float
        +fps: int
        +is_valid() bool
        +to_dict() dict
    }

    class ConfigurationEntity {
        +id: str
        +name: str
        +type: ConfigType
        +data: dict
        +created_at: datetime
        +updated_at: datetime
        +validate() bool
        +merge(other: ConfigurationEntity) ConfigurationEntity
    }

    %% Domain Layer - Value Objects
    class PathConfig {
        +base_path: str
        +emulators_root: str
        +roms_root: str
        +config_directory: str
        +validate_paths() bool
        +get_absolute_path(relative: str) str
    }

    class PerformanceMetrics {
        +cpu_percent: float
        +memory_percent: float
        +gpu_percent: float
        +temperature: float
        +fps: int
        +frame_time: float
        +is_healthy() bool
    }

    %% Application Layer - Use Cases
    class EmulatorManagementUseCase {
        -emulator_repository: EmulatorRepository
        -config_service: ConfigurationService
        +configure_emulator(config: dict) EmulatorEntity
        +execute_game(rom_id: str, emulator_id: str) bool
        +get_available_emulators() List[EmulatorEntity]
        +validate_emulator_config(emulator_id: str) bool
    }

    class SystemMonitoringUseCase {
        -stats_repository: SystemStatsRepository
        -notification_service: NotificationService
        +collect_current_metrics() PerformanceMetrics
        +get_historical_stats(period: str) List[SystemStatsEntity]
        +configure_alerts(thresholds: dict) void
        +generate_performance_report() dict
    }

    class ConfigurationManagementUseCase {
        -config_repository: ConfigurationRepository
        -backup_service: BackupService
        +save_configuration(config: ConfigurationEntity) bool
        +load_configuration(config_id: str) ConfigurationEntity
        +backup_configurations() bool
        +restore_configuration(backup_id: str) bool
    }

    %% Application Layer - Services
    class ValidationService {
        +validate_emulator_config(config: dict) ValidationResult
        +validate_rom_integrity(rom_path: str) ValidationResult
        +validate_system_requirements() ValidationResult
        +validate_paths(path_config: PathConfig) ValidationResult
    }

    class NotificationService {
        -observers: List[Observer]
        +add_observer(observer: Observer) void
        +remove_observer(observer: Observer) void
        +notify_success(message: str) void
        +notify_warning(message: str) void
        +notify_error(message: str) void
    }

    class BackupService {
        -storage_adapter: StorageAdapter
        +create_backup(data: dict) str
        +restore_backup(backup_id: str) dict
        +list_backups() List[BackupInfo]
        +delete_backup(backup_id: str) bool
    }

    %% Infrastructure Layer - Repositories
    class EmulatorRepository {
        <<interface>>
        +save(emulator: EmulatorEntity) bool
        +find_by_id(id: str) EmulatorEntity
        +find_all() List[EmulatorEntity]
        +delete(id: str) bool
        +find_by_format(format: str) List[EmulatorEntity]
    }

    class ROMRepository {
        <<interface>>
        +save(rom: ROMEntity) bool
        +find_by_id(id: str) ROMEntity
        +find_all() List[ROMEntity]
        +find_by_emulator(emulator_id: str) List[ROMEntity]
        +search(query: str) List[ROMEntity]
    }

    class SystemStatsRepository {
        <<interface>>
        +save(stats: SystemStatsEntity) bool
        +find_by_period(start: datetime, end: datetime) List[SystemStatsEntity]
        +get_latest() SystemStatsEntity
        +cleanup_old_data(days: int) void
    }

    class ConfigurationRepository {
        <<interface>>
        +save(config: ConfigurationEntity) bool
        +find_by_id(id: str) ConfigurationEntity
        +find_by_type(type: ConfigType) List[ConfigurationEntity]
        +delete(id: str) bool
    }

    %% Infrastructure Layer - Adapters
    class FileSystemEmulatorRepository {
        -file_manager: FileManager
        +save(emulator: EmulatorEntity) bool
        +find_by_id(id: str) EmulatorEntity
        +find_all() List[EmulatorEntity]
        +delete(id: str) bool
        +find_by_format(format: str) List[EmulatorEntity]
    }

    class JSONConfigurationRepository {
        -file_path: str
        -json_handler: JSONHandler
        +save(config: ConfigurationEntity) bool
        +find_by_id(id: str) ConfigurationEntity
        +find_by_type(type: ConfigType) List[ConfigurationEntity]
        +delete(id: str) bool
    }

    class MemorySystemStatsRepository {
        -stats_cache: List[SystemStatsEntity]
        -max_size: int
        +save(stats: SystemStatsEntity) bool
        +find_by_period(start: datetime, end: datetime) List[SystemStatsEntity]
        +get_latest() SystemStatsEntity
        +cleanup_old_data(days: int) void
    }

    %% Infrastructure Layer - External Services
    class SystemInfoAdapter {
        +get_cpu_usage() float
        +get_memory_usage() float
        +get_gpu_usage() float
        +get_temperature() float
        +get_system_info() dict
    }

    class ProcessManagerAdapter {
        +start_process(executable: str, args: List[str]) Process
        +kill_process(pid: int) bool
        +is_process_running(pid: int) bool
        +get_process_info(pid: int) dict
    }

    class FileManagerAdapter {
        +read_file(path: str) str
        +write_file(path: str, content: str) bool
        +copy_file(source: str, destination: str) bool
        +delete_file(path: str) bool
        +list_directory(path: str) List[str]
        +create_directory(path: str) bool
    }

    %% Presentation Layer - Controllers
    class EmulatorController {
        -emulator_use_case: EmulatorManagementUseCase
        +configure_emulator(request: dict) Response
        +execute_game(request: dict) Response
        +get_emulators() Response
        +validate_config(request: dict) Response
    }

    class SystemController {
        -monitoring_use_case: SystemMonitoringUseCase
        +get_current_stats() Response
        +get_historical_stats(request: dict) Response
        +configure_alerts(request: dict) Response
        +generate_report() Response
    }

    class ConfigurationController {
        -config_use_case: ConfigurationManagementUseCase
        +save_config(request: dict) Response
        +load_config(request: dict) Response
        +backup_configs() Response
        +restore_config(request: dict) Response
    }

    %% Presentation Layer - Views
    class MainWindow {
        -emulator_controller: EmulatorController
        -system_controller: SystemController
        -config_controller: ConfigurationController
        +setup_ui() void
        +handle_emulator_action(action: str) void
        +update_system_stats(stats: dict) void
        +show_notification(message: str, type: str) void
    }

    class OverlayWidget {
        -stats_data: dict
        -position: Position
        -transparency: float
        +update_stats(stats: dict) void
        +set_position(position: Position) void
        +set_transparency(value: float) void
        +show_overlay() void
        +hide_overlay() void
    }

    %% Enums and Types
    class ConfigType {
        <<enumeration>>
        EMULATOR
        SYSTEM
        UI
        PATHS
        BACKUP
    }

    class Position {
        <<enumeration>>
        TOP_LEFT
        TOP_RIGHT
        BOTTOM_LEFT
        BOTTOM_RIGHT
        CENTER
    }

    %% Relationships - Domain
    EmulatorEntity --> PathConfig : uses
    ROMEntity --> EmulatorEntity : belongs_to
    SystemStatsEntity --> PerformanceMetrics : contains

    %% Relationships - Application Layer
    EmulatorManagementUseCase --> EmulatorRepository : uses
    EmulatorManagementUseCase --> ValidationService : uses
    SystemMonitoringUseCase --> SystemStatsRepository : uses
    SystemMonitoringUseCase --> NotificationService : uses
    ConfigurationManagementUseCase --> ConfigurationRepository : uses
    ConfigurationManagementUseCase --> BackupService : uses

    %% Relationships - Infrastructure
    FileSystemEmulatorRepository ..|> EmulatorRepository : implements
    JSONConfigurationRepository ..|> ConfigurationRepository : implements
    MemorySystemStatsRepository ..|> SystemStatsRepository : implements

    %% Relationships - Presentation
    EmulatorController --> EmulatorManagementUseCase : uses
    SystemController --> SystemMonitoringUseCase : uses
    ConfigurationController --> ConfigurationManagementUseCase : uses
    MainWindow --> EmulatorController : uses
    MainWindow --> SystemController : uses
    MainWindow --> ConfigurationController : uses
    MainWindow --> OverlayWidget : contains

    %% Relationships - External Adapters
    SystemMonitoringUseCase --> SystemInfoAdapter : uses
    EmulatorManagementUseCase --> ProcessManagerAdapter : uses
    BackupService --> FileManagerAdapter : uses

    %% Styling
    classDef domainClass fill:#32CD32,stroke:#228B22,stroke-width:2px,color:#000
    classDef applicationClass fill:#FFD700,stroke:#DAA520,stroke-width:2px,color:#000
    classDef infrastructureClass fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    classDef presentationClass fill:#FF6B6B,stroke:#E55555,stroke-width:2px,color:#fff
    classDef interfaceClass fill:#DDA0DD,stroke:#9370DB,stroke-width:2px,color:#000

    class EmulatorEntity,ROMEntity,SystemStatsEntity,ConfigurationEntity,PathConfig,PerformanceMetrics domainClass
    class EmulatorManagementUseCase,SystemMonitoringUseCase,ConfigurationManagementUseCase,ValidationService,NotificationService,BackupService applicationClass
    class FileSystemEmulatorRepository,JSONConfigurationRepository,MemorySystemStatsRepository,SystemInfoAdapter,ProcessManagerAdapter,FileManagerAdapter infrastructureClass
    class EmulatorController,SystemController,ConfigurationController,MainWindow,OverlayWidget presentationClass
    class EmulatorRepository,ROMRepository,SystemStatsRepository,ConfigurationRepository interfaceClass
```

## Descrição das Classes

### Domain Layer (Camada de Domínio)

#### Entities (Entidades)
- **EmulatorEntity**: Representa um emulador com suas configurações
- **ROMEntity**: Representa um arquivo ROM com metadados
- **SystemStatsEntity**: Representa estatísticas do sistema em um momento
- **ConfigurationEntity**: Representa uma configuração do sistema

#### Value Objects (Objetos de Valor)
- **PathConfig**: Configurações de caminhos do sistema
- **PerformanceMetrics**: Métricas de performance em tempo real

### Application Layer (Camada de Aplicação)

#### Use Cases (Casos de Uso)
- **EmulatorManagementUseCase**: Gerenciamento de emuladores
- **SystemMonitoringUseCase**: Monitoramento do sistema
- **ConfigurationManagementUseCase**: Gerenciamento de configurações

#### Services (Serviços)
- **ValidationService**: Validação de dados e configurações
- **NotificationService**: Sistema de notificações
- **BackupService**: Serviço de backup e restauração

### Infrastructure Layer (Camada de Infraestrutura)

#### Repositories (Repositórios)
- Interfaces para persistência de dados
- Implementações específicas para diferentes tipos de armazenamento

#### Adapters (Adaptadores)
- **SystemInfoAdapter**: Acesso a informações do sistema
- **ProcessManagerAdapter**: Gerenciamento de processos
- **FileManagerAdapter**: Operações de arquivo

### Presentation Layer (Camada de Apresentação)

#### Controllers (Controladores)
- Coordenam as interações entre a UI e os casos de uso

#### Views (Visões)
- **MainWindow**: Janela principal da aplicação
- **OverlayWidget**: Widget de overlay para informações

## Padrões de Design Utilizados

### 1. Repository Pattern
- Abstração para acesso a dados
- Permite diferentes implementações de persistência

### 2. Observer Pattern
- Sistema de notificações
- Atualizações de UI em tempo real

### 3. Adapter Pattern
- Integração com APIs externas
- Abstração de dependências do sistema

### 4. Dependency Injection
- Inversão de dependências
- Facilita testes e manutenção

### 5. Clean Architecture
- Separação clara de responsabilidades
- Independência de frameworks externos

## Princípios SOLID

### Single Responsibility Principle (SRP)
- Cada classe tem uma única responsabilidade
- Separação clara entre domínio, aplicação e infraestrutura

### Open/Closed Principle (OCP)
- Classes abertas para extensão, fechadas para modificação
- Uso de interfaces e abstrações

### Liskov Substitution Principle (LSP)
- Implementações podem ser substituídas sem quebrar o sistema
- Interfaces bem definidas

### Interface Segregation Principle (ISP)
- Interfaces específicas e focadas
- Evita dependências desnecessárias

### Dependency Inversion Principle (DIP)
- Dependência de abstrações, não de implementações
- Inversão de controle através de injeção de dependência

## Notas de Implementação

1. **Thread Safety**: Classes de repositório devem ser thread-safe
2. **Error Handling**: Todas as operações devem ter tratamento de erro
3. **Logging**: Operações críticas devem ser logadas
4. **Performance**: Caching onde apropriado
5. **Testing**: Todas as classes devem ser testáveis