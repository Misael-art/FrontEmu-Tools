"""
Admin Utilities Module

Provides utilities for managing administrative privileges on Windows systems,
including privilege detection, UAC prompts, and application restart functionality.
"""

import ctypes
import locale
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional


class AdminUtils:
    """Utilities for managing administrative privileges on Windows."""
    
    @staticmethod
    def is_admin() -> bool:
        """Check if the current process is running with administrative privileges."""
        if sys.platform != "win32":
            return True  # Assume admin on non-Windows systems
        
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    
    @staticmethod
    def get_everyone_account_name() -> str:
        """Get the localized name for the 'Everyone' account based on system language."""
        try:
            # Get system default language
            system_lang = locale.getdefaultlocale()[0]
            
            if system_lang and system_lang.startswith('pt'):
                return "Todos"
            elif system_lang and system_lang.startswith('es'):
                return "Todos"
            elif system_lang and system_lang.startswith('fr'):
                return "Tout le monde"
            elif system_lang and system_lang.startswith('de'):
                return "Jeder"
            elif system_lang and system_lang.startswith('it'):
                return "Everyone"  # Italian uses English term
            else:
                return "Everyone"  # Default to English
        except Exception:
            return "Everyone"  # Fallback to English
    
    @staticmethod
    def restart_as_admin(script_path: Optional[str] = None) -> bool:
        """
        Restart the current application with administrative privileges.
        
        Args:
            script_path: Path to the script to restart. If None, uses current script.
            
        Returns:
            True if restart was initiated, False otherwise.
        """
        if sys.platform != "win32":
            return False
        
        if AdminUtils.is_admin():
            return True  # Already running as admin
        
        try:
            # Determine how to restart the application
            if hasattr(sys, '_MEIPASS'):
                # Running as PyInstaller bundle
                executable = sys.executable
                arguments = sys.argv[1:]  # Skip the executable itself
            else:
                # Running as Python script - need to construct proper command
                executable = sys.executable
                # Get the main script path relative to current directory
                main_script = sys.argv[0]
                if main_script.startswith('-m '):
                    # Running with -m flag
                    arguments = sys.argv
                else:
                    # Regular script execution
                    script_dir = Path(__file__).parent.parent.parent  # Go up to project root
                    # Find the correct main.py path
                    possible_main_paths = [
                        script_dir / 'src' / 'sd_emulation_gui' / 'app' / 'main.py',
                        script_dir / 'app' / 'main.py',
                        script_dir / 'main.py'
                    ]
                    
                    main_script = None
                    for path in possible_main_paths:
                        if path.exists():
                            main_script = str(path)
                            break
                    
                    if not main_script:
                        # Fallback to the first option
                        main_script = str(script_dir / 'src' / 'sd_emulation_gui' / 'app' / 'main.py')
                    
                    arguments = [main_script] + sys.argv[1:]
            
            # Build command arguments string
            if arguments:
                cmd_args = ' '.join(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in arguments)
            else:
                cmd_args = ''
                
            print(f"Restarting as admin: {executable} {cmd_args}")
            
            # Use ShellExecute with 'runas' verb to trigger UAC
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",  # Trigger UAC
                executable,
                cmd_args,
                str(Path.cwd()),  # Working directory
                1  # SW_SHOWNORMAL
            )
            
            print(f"ShellExecuteW result: {result}")
            
            # ShellExecuteW returns > 32 for success
            if result > 32:
                print("UAC prompt should have appeared. Waiting for user response...")
                # Give the new process a moment to start
                import time
                time.sleep(2)  # Increased delay
                
                print("Exiting current process to allow admin restart...")
                # Exit current process since new admin process should be starting
                sys.exit(0)
            else:
                error_messages = {
                    0: "Out of memory or resources",
                    2: "File not found", 
                    3: "Path not found",
                    5: "Access denied",
                    8: "Out of memory",
                    26: "Cannot share",
                    27: "Association incomplete",
                    28: "DDE timeout",
                    29: "DDE failed",
                    30: "DDE busy",
                    31: "No association"
                }
                error_msg = error_messages.get(result, f"Unknown error code: {result}")
                print(f"ShellExecuteW failed: {error_msg}")
                return False
                
        except Exception as e:
            print(f"Failed to restart as admin: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def request_admin_if_needed(operation_description: str = "esta operação", allow_continue: bool = True) -> bool:
        """
        Request administrative privileges if not already running as admin.
        
        Args:
            operation_description: Description of the operation requiring admin rights.
            allow_continue: If True, allows user to continue without admin privileges.
            
        Returns:
            True if running as admin (now or already), False if user declined or restart failed.
        """
        if AdminUtils.is_admin():
            return True
        
        try:
            # Try to import PySide6 for GUI dialog
            from PySide6.QtWidgets import QMessageBox, QApplication
            
            # Check if QApplication exists, create if needed
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            # Build dialog message
            message = f"A operação '{operation_description}' funciona melhor com privilégios de administrador.\n\n"
            
            if allow_continue:
                message += (
                    "Opções disponíveis:\n\n"
                    "• Clique 'Sim' para reiniciar com privilégios administrativos\n"
                    "• Clique 'Não' para tentar continuar sem privilégios\n\n"
                    "Nota: Algumas operações podem falhar sem privilégios administrativos."
                )
            else:
                message += (
                    "Esta operação REQUER privilégios administrativos.\n\n"
                    "• Clique 'Sim' para reiniciar com privilégios administrativos\n"
                    "• Clique 'Não' para cancelar a operação"
                )
            
            # Show dialog asking user what to do
            reply = QMessageBox.question(
                None,
                "Privilégios Administrativos Recomendados" if allow_continue else "Privilégios Administrativos Necessários",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default to No to avoid accidental restarts
            )
            
            if reply == QMessageBox.Yes:
                # User chose to restart as admin
                restart_success = AdminUtils.restart_as_admin()
                if not restart_success:
                    # Restart failed, ask if user wants to continue anyway
                    if allow_continue:
                        continue_reply = QMessageBox.question(
                            None,
                            "Reinicialização Falhou",
                            "Não foi possível reiniciar com privilégios administrativos.\n\n"
                            "Deseja tentar continuar sem privilégios?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        return continue_reply == QMessageBox.Yes
                    else:
                        QMessageBox.warning(
                            None,
                            "Operação Cancelada",
                            "Não foi possível obter privilégios administrativos.\n"
                            "A operação foi cancelada."
                        )
                        return False
                return restart_success
            else:
                # User chose not to restart
                return allow_continue
                
        except ImportError:
            # Fallback to console prompt if GUI not available
            print(f"\n⚠️  Privilégios administrativos necessários para: {operation_description}")
            if allow_continue:
                print("Opções:")
                print("1. Pressione ENTER para tentar reiniciar como administrador")
                print("2. Digite 'n' e pressione ENTER para continuar sem privilégios")
                
                choice = input("\nEscolha (ENTER/n): ").strip().lower()
                if choice in ['', 'y', 'yes', 's', 'sim']:
                    restart_success = AdminUtils.restart_as_admin()
                    return restart_success if restart_success else True  # Continue anyway if restart fails
                else:
                    return True  # Continue without admin
            else:
                print("Esta operação requer privilégios administrativos.")
                choice = input("Tentar reiniciar como administrador? (s/N): ").strip().lower()
                if choice in ['s', 'sim', 'y', 'yes']:
                    return AdminUtils.restart_as_admin()
                else:
                    return False
    
    @staticmethod
    def run_elevated_command(command: list, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Run a command with elevated privileges.
        
        Args:
            command: Command and arguments as list
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if sys.platform != "win32":
                # On non-Windows, just run normally
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout
                )
                return (result.returncode == 0, result.stdout, result.stderr)
            
            # On Windows, run with elevated privileges if we have them
            if AdminUtils.is_admin():
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout
                )
                return (result.returncode == 0, result.stdout, result.stderr)
            else:
                # Not running as admin, command might fail
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=timeout
                )
                return (result.returncode == 0, result.stdout, result.stderr)
                
        except subprocess.TimeoutExpired:
            return (False, "", f"Command timed out after {timeout} seconds")
        except Exception as e:
            return (False, "", str(e))
    
    @staticmethod
    def get_user_confirmation_for_admin(operation: str) -> bool:
        """
        Get user confirmation before requesting admin privileges.
        
        Args:
            operation: Description of operation requiring admin rights
            
        Returns:
            True if user confirms, False otherwise
        """
        try:
            from PySide6.QtWidgets import QMessageBox, QApplication
            
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            reply = QMessageBox.question(
                None,
                "Confirmação de Operação Administrativa",
                f"A operação solicitada requer privilégios administrativos:\n\n"
                f"'{operation}'\n\n"
                f"Esta operação pode:\n"
                f"• Modificar arquivos do sistema\n"
                f"• Alterar permissões de arquivos/pastas\n"
                f"• Criar links simbólicos\n\n"
                f"Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            return reply == QMessageBox.Yes
            
        except ImportError:
            # Console fallback
            print(f"\n🔐 Operação administrativa solicitada: {operation}")
            print("\nEsta operação pode:")
            print("• Modificar arquivos do sistema")
            print("• Alterar permissões de arquivos/pastas")  
            print("• Criar links simbólicos")
            
            choice = input("\nDeseja continuar? (s/N): ").strip().lower()
            return choice in ['s', 'sim', 'y', 'yes']


# Convenience functions
def is_admin() -> bool:
    """Check if running with admin privileges."""
    return AdminUtils.is_admin()


def request_admin(operation: str = "esta operação") -> bool:
    """Request admin privileges if needed."""
    return AdminUtils.request_admin_if_needed(operation)


def get_everyone_account() -> str:
    """Get localized 'Everyone' account name."""
    return AdminUtils.get_everyone_account_name()


def run_as_admin(command: list, timeout: int = 30) -> Tuple[bool, str, str]:
    """Run command with admin privileges."""
    return AdminUtils.run_elevated_command(command, timeout)