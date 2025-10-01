# Diagramas de Sequência - FrontEmu-Tools

## Visão Geral
Este documento contém os principais diagramas de sequência que ilustram as interações entre os componentes do FrontEmu-Tools.

## 1. Sequência: Executar Jogo

```mermaid
sequenceDiagram
    participant User as 👤 Usuário
    participant UI as 🖥️ MainWindow
    participant EC as 🎮 EmulatorController
    participant EMU as 🔧 EmulatorManagementUseCase
    participant VS as ✅ ValidationService
    participant ER as 📁 EmulatorRepository
    participant RR as 💿 ROMRepository
    participant PA as ⚙️ ProcessManagerAdapter
    participant NS as 🔔 NotificationService

    User->>UI: Clica em "Executar Jogo"
    UI->>EC: execute_game(rom_id, emulator_id)
    
    EC->>EMU: execute_game(rom_id, emulator_id)
    
    %% Validação
    EMU->>RR: find_by_id(rom_id)
    RR-->>EMU: ROMEntity
    
    EMU->>ER: find_by_id(emulator_id)
    ER-->>EMU: EmulatorEntity
    
    EMU->>VS: validate_rom_integrity(rom_path)
    VS-->>EMU: ValidationResult(success=true)
    
    EMU->>VS: validate_emulator_config(emulator_config)
    VS-->>EMU: ValidationResult(success=true)
    
    %% Execução
    EMU->>PA: start_process(executable, args)
    PA-->>EMU: Process(pid=1234)
    
    %% Notificação de sucesso
    EMU->>NS: notify_success("Jogo iniciado com sucesso")
    NS->>UI: update_notification("Jogo iniciado")
    
    EMU-->>EC: ExecutionResult(success=true, pid=1234)
    EC-->>UI: Response(success=true)
    UI-->>User: Exibe jogo em execução

    %% Monitoramento contínuo
    loop Monitoramento
        EMU->>PA: is_process_running(pid)
        PA-->>EMU: bool
        
        alt Processo ainda rodando
            EMU->>UI: update_status("Executando")
        else Processo finalizado
            EMU->>NS: notify_info("Jogo finalizado")
            NS->>UI: update_notification("Jogo finalizado")
        end
    end
```

## 2. Sequência: Monitoramento de Performance

```mermaid
sequenceDiagram
    participant Timer as ⏰ Timer
    participant SMU as 📊 SystemMonitoringUseCase
    participant SIA as 🖥️ SystemInfoAdapter
    participant SSR as 💾 SystemStatsRepository
    participant NS as 🔔 NotificationService
    participant OW as 📱 OverlayWidget
    participant UI as 🖥️ MainWindow

    %% Coleta periódica de métricas
    loop A cada 1 segundo
        Timer->>SMU: collect_current_metrics()
        
        %% Coleta de dados do sistema
        SMU->>SIA: get_cpu_usage()
        SIA-->>SMU: 45.2
        
        SMU->>SIA: get_memory_usage()
        SIA-->>SMU: 67.8
        
        SMU->>SIA: get_gpu_usage()
        SIA-->>SMU: 89.1
        
        SMU->>SIA: get_temperature()
        SIA-->>SMU: 72.5
        
        %% Criação da entidade
        SMU->>SMU: create_SystemStatsEntity()
        
        %% Persistência
        SMU->>SSR: save(stats_entity)
        SSR-->>SMU: bool(success)
        
        %% Verificação de alertas
        alt CPU > 90% ou Temp > 80°C
            SMU->>NS: notify_warning("Performance crítica")
            NS->>UI: show_warning_notification()
        else GPU > 95%
            SMU->>NS: notify_error("GPU sobrecarregada")
            NS->>UI: show_error_notification()
        else Normal
            SMU->>OW: update_stats(performance_metrics)
            OW->>OW: refresh_display()
        end
        
        %% Atualização da UI
        SMU-->>UI: performance_data
        UI->>UI: update_performance_charts()
    end
```

## 3. Sequência: Configuração de Emulador

```mermaid
sequenceDiagram
    participant User as 👤 Usuário
    participant UI as 🖥️ ConfigDialog
    participant CC as ⚙️ ConfigurationController
    participant CMU as 📋 ConfigurationManagementUseCase
    participant VS as ✅ ValidationService
    participant CR as 💾 ConfigurationRepository
    participant BS as 💾 BackupService
    participant NS as 🔔 NotificationService

    User->>UI: Abre configurações
    UI->>CC: get_current_config(emulator_id)
    
    CC->>CMU: load_configuration(emulator_id)
    CMU->>CR: find_by_id(emulator_id)
    CR-->>CMU: ConfigurationEntity
    CMU-->>CC: configuration_data
    CC-->>UI: current_config
    
    UI-->>User: Exibe formulário preenchido
    
    User->>UI: Modifica configurações
    User->>UI: Clica "Salvar"
    
    UI->>CC: save_configuration(new_config)
    
    %% Backup da configuração atual
    CC->>CMU: backup_configurations()
    CMU->>BS: create_backup(current_config)
    BS-->>CMU: backup_id
    
    %% Validação da nova configuração
    CC->>CMU: validate_and_save(new_config)
    CMU->>VS: validate_emulator_config(new_config)
    
    alt Validação bem-sucedida
        VS-->>CMU: ValidationResult(success=true)
        
        %% Salvar nova configuração
        CMU->>CR: save(configuration_entity)
        CR-->>CMU: bool(success)
        
        CMU->>NS: notify_success("Configuração salva")
        NS->>UI: show_success_message()
        
        CMU-->>CC: SaveResult(success=true)
        CC-->>UI: Response(success=true)
        UI-->>User: "Configuração salva com sucesso"
        
    else Validação falhou
        VS-->>CMU: ValidationResult(success=false, errors)
        
        %% Restaurar backup
        CMU->>BS: restore_backup(backup_id)
        BS-->>CMU: original_config
        
        CMU->>NS: notify_error("Configuração inválida")
        NS->>UI: show_error_message(errors)
        
        CMU-->>CC: SaveResult(success=false, errors)
        CC-->>UI: Response(success=false, errors)
        UI-->>User: "Erro: " + error_details
    end
```

## 4. Sequência: Detecção de Sistema Legacy

```mermaid
sequenceDiagram
    participant App as 🚀 Application
    participant LDS as 🔍 LegacyDetectionService
    participant FMA as 📁 FileManagerAdapter
    participant VS as ✅ ValidationService
    participant CR as 💾 ConfigurationRepository
    participant NS as 🔔 NotificationService
    participant UI as 🖥️ MainWindow

    App->>LDS: detect_legacy_systems()
    
    %% Busca por emuladores conhecidos
    LDS->>FMA: list_directory("C:/Program Files")
    FMA-->>LDS: directory_list
    
    LDS->>FMA: list_directory("C:/Program Files (x86)")
    FMA-->>LDS: directory_list_x86
    
    %% Análise de cada diretório
    loop Para cada diretório
        LDS->>LDS: analyze_directory(path)
        
        alt Emulador detectado
            LDS->>FMA: read_file(config_file)
            FMA-->>LDS: config_content
            
            LDS->>VS: validate_emulator_config(config)
            VS-->>LDS: ValidationResult
            
            alt Configuração válida
                LDS->>CR: save(emulator_config)
                CR-->>LDS: bool(success)
                
                LDS->>NS: notify_success("Emulador detectado: " + name)
                NS->>UI: show_detection_notification()
            else Configuração inválida
                LDS->>NS: notify_warning("Emulador encontrado mas configuração inválida")
                NS->>UI: show_warning_notification()
            end
        end
    end
    
    %% Relatório final
    LDS->>LDS: generate_detection_report()
    LDS-->>App: DetectionReport(found_emulators, invalid_configs)
    
    App->>UI: display_detection_results(report)
    UI-->>UI: update_emulator_list()
```

## 5. Sequência: Backup e Restauração

```mermaid
sequenceDiagram
    participant User as 👤 Usuário
    participant UI as 🖥️ BackupDialog
    participant CC as ⚙️ ConfigurationController
    participant CMU as 📋 ConfigurationManagementUseCase
    participant BS as 💾 BackupService
    participant FMA as 📁 FileManagerAdapter
    participant CR as 💾 ConfigurationRepository
    participant NS as 🔔 NotificationService

    %% Processo de Backup
    User->>UI: Clica "Criar Backup"
    UI->>CC: create_backup()
    
    CC->>CMU: backup_configurations()
    CMU->>CR: find_all()
    CR-->>CMU: List[ConfigurationEntity]
    
    CMU->>BS: create_backup(all_configs)
    BS->>FMA: create_directory(backup_path)
    FMA-->>BS: bool(success)
    
    loop Para cada configuração
        BS->>FMA: write_file(config_file, content)
        FMA-->>BS: bool(success)
    end
    
    BS->>BS: generate_backup_metadata()
    BS->>FMA: write_file(metadata_file, metadata)
    FMA-->>BS: bool(success)
    
    BS-->>CMU: backup_id
    CMU->>NS: notify_success("Backup criado: " + backup_id)
    NS->>UI: show_success_notification()
    
    CMU-->>CC: BackupResult(success=true, backup_id)
    CC-->>UI: Response(success=true)
    UI-->>User: "Backup criado com sucesso"
    
    %% Processo de Restauração
    User->>UI: Seleciona backup e clica "Restaurar"
    UI->>CC: restore_backup(backup_id)
    
    CC->>CMU: restore_configuration(backup_id)
    CMU->>BS: restore_backup(backup_id)
    
    BS->>FMA: read_file(metadata_file)
    FMA-->>BS: metadata_content
    
    BS->>BS: validate_backup_integrity()
    
    alt Backup válido
        loop Para cada arquivo de configuração
            BS->>FMA: read_file(config_file)
            FMA-->>BS: config_content
            
            BS->>CMU: restore_configuration_item(config)
            CMU->>CR: save(configuration_entity)
            CR-->>CMU: bool(success)
        end
        
        BS-->>CMU: RestoreResult(success=true)
        CMU->>NS: notify_success("Configurações restauradas")
        NS->>UI: show_success_notification()
        
    else Backup corrompido
        BS-->>CMU: RestoreResult(success=false, error)
        CMU->>NS: notify_error("Backup corrompido")
        NS->>UI: show_error_notification()
    end
    
    CMU-->>CC: RestoreResult
    CC-->>UI: Response
    UI-->>User: Resultado da restauração
```

## Padrões de Interação

### 1. Validação Consistente
- Todas as operações críticas passam por validação
- Rollback automático em caso de falha

### 2. Notificações Assíncronas
- Sistema de notificações não bloqueia operações
- Feedback visual imediato para o usuário

### 3. Tratamento de Erro
- Cada operação tem tratamento específico de erro
- Logs detalhados para debugging

### 4. Monitoramento Contínuo
- Coleta periódica de métricas
- Alertas baseados em thresholds

### 5. Backup Automático
- Backup antes de operações críticas
- Restauração automática em caso de falha

## Considerações de Performance

1. **Operações Assíncronas**: Operações longas não bloqueiam a UI
2. **Caching**: Dados frequentemente acessados são cached
3. **Lazy Loading**: Carregamento sob demanda
4. **Pooling**: Reutilização de recursos quando possível
5. **Throttling**: Limitação de frequência para operações intensivas