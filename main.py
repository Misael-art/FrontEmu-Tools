#!/usr/bin/env python3
"""
SD Emulation GUI - Main Entry Point (Legacy Compatibility)

Este arquivo serve como ponto de entrada compatível com a estrutura anterior,
redirecionando para a nova arquitetura organizada em src/sd_emulation_gui/.

Mantenha este arquivo para compatibilidade com scripts de inicialização existentes.
"""

import sys
import traceback
from pathlib import Path

def main():
    """
    Ponto de entrada principal da aplicação.

    Redireciona para a nova estrutura organizada em src/sd_emulation_gui/.
    """
    try:
        # Adicionar src ao path para importar o novo pacote
        project_root = Path(__file__).parent
        src_path = project_root / "src"
        sys.path.insert(0, str(src_path))

        # Importar e executar a aplicação da nova estrutura
        from sd_emulation_gui.app.main import main as app_main

        print("[INFO] Iniciando SD Emulation GUI (Nova Arquitetura)...")
        print(f"[INFO] Estrutura: {src_path}")

        # Executar a aplicação
        return app_main()

    except ImportError as e:
        print("[ERRO] Não foi possível importar a aplicação da nova estrutura.")
        print(f"   Detalhes: {e}")
        print(f"   Verifique se src/sd_emulation_gui/ existe em: {src_path}")
        print("   Estrutura atual do diretório src/:")
        if src_path.exists():
            for item in src_path.iterdir():
                print(f"   - {item.name}")
        else:
            print("   ❌ Diretório src/ não encontrado!")
        return 1

    except Exception as e:
        print("[ERRO] ERRO INESPERADO durante inicialização:")
        print(f"   {e}")
        print("\n[ERRO] Stack trace completo:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)