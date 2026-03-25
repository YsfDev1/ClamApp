import psutil

class TaskManagerLogic:
    """
    Logic for fetching and managing system processes.
    """
    @staticmethod
    def get_processes():
        """
        Returns a list of dictionaries containing process info.
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                # We use info attribute which was populated by process_iter
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return processes

    @staticmethod
    def kill_process(pid):
        """
        Attempts to terminate a process by PID.
        """
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True, "Process terminated."
        except psutil.AccessDenied:
            return False, "Access Denied. You might need root privileges."
        except psutil.NoSuchProcess:
            return False, "Process no longer exists."
        except Exception as e:
            return False, str(e)
