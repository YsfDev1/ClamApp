import subprocess

class AppManagerLogic:
    """
    Lists installed packages and their details.
    """
    @staticmethod
    def list_apps():
        """
        Uses dpkg-query to get a list of installed packages on Pardus (Debian-based).
        """
        try:
            # Format: Package, Version, Architecture, Status, Description
            cmd = ["dpkg-query", "-W", "-f=${Package}|${Version}|${Architecture}|${Status}|${binary:Summary}\n"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            apps = []
            for line in res.stdout.splitlines():
                parts = line.split("|")
                if len(parts) >= 5 and "installed" in parts[3]:
                    apps.append({
                        "name": parts[0],
                        "version": parts[1],
                        "arch": parts[2],
                        "summary": parts[4]
                    })
            return apps
        except Exception as e:
            print(f"App Manager Logic: Error listing apps: {e}")
            return []

    @staticmethod
    def get_details(package_name):
        """
        Gets detailed info for a specific package.
        """
        try:
            res = subprocess.run(["dpkg", "-s", package_name], capture_output=True, text=True)
            return res.stdout
        except Exception:
            return "Could not retrieve details."
