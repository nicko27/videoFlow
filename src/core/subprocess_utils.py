
"""
Utilitaires subprocess sécurisés avec timeouts
"""

import subprocess
import signal
import os
import threading
import time
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

class TimeoutError(Exception):
    """Exception levée en cas de timeout"""
    pass

class SafeSubprocess:
    """Gestionnaire subprocess sécurisé avec timeouts"""
    
    @staticmethod
    def run_with_timeout(cmd: List[str], timeout: int = 30, 
                        cwd: Optional[str] = None,
                        env: Optional[Dict[str, str]] = None,
                        input_data: Optional[str] = None) -> Tuple[int, str, str]:
        """Exécute une commande avec timeout"""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else None,
                cwd=cwd,
                env=env,
                universal_newlines=True,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            try:
                stdout, stderr = process.communicate(
                    input=input_data, 
                    timeout=timeout
                )
                return process.returncode, stdout, stderr
                
            except subprocess.TimeoutExpired:
                # Tuer le processus et tous ses enfants
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                # Attendre un peu puis forcer
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait()
                
                raise TimeoutError(f"Commande timeout après {timeout}s: {' '.join(cmd)}")
                
        except Exception as e:
            raise VideoFlowError(
                f"Erreur exécution commande: {e}",
                ErrorType.UNKNOWN,
                ErrorSeverity.HIGH,
                {"command": cmd, "timeout": timeout}
            )
    
    @staticmethod
    def run_ffmpeg(cmd: List[str], timeout: int = 300, 
                   progress_callback: Optional[callable] = None) -> Tuple[int, str, str]:
        """Exécute ffmpeg avec monitoring de progression"""
        full_cmd = ['ffmpeg'] + cmd
        
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        stderr_output = []
        start_time = time.time()
        
        try:
            while True:
                # Vérifier le timeout
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"FFmpeg timeout après {timeout}s")
                
                # Lire stderr ligne par ligne
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    stderr_output.append(line)
                    
                    # Extraire la progression si callback fourni
                    if progress_callback:
                        try:
                            # Chercher des patterns de progression FFmpeg
                            import re
                            time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                            if time_match:
                                h, m, s = time_match.groups()
                                current_time = int(h) * 3600 + int(m) * 60 + float(s)
                                progress_callback(current_time)
                        except Exception:
                            pass  # Ignorer les erreurs de parsing
            
            stdout, _ = process.communicate()
            return process.returncode, stdout, ''.join(stderr_output)
            
        except Exception as e:
            # Nettoyer le processus
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=5)
            except:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
            
            raise e

@contextmanager
def managed_subprocess(cmd: List[str], **kwargs):
    """Gestionnaire de contexte pour subprocess"""
    process = None
    try:
        process = subprocess.Popen(cmd, **kwargs)
        yield process
    finally:
        if process:
            try:
                if process.poll() is None:  # Processus encore en cours
                    process.terminate()
                    process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"Erreur nettoyage subprocess: {e}")
