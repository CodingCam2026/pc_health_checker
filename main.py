
import psutil
import platform
from datetime import datetime, timedelta
import subprocess
import json

class PCStats:
    """Gets the pc statitcs"""
    def __init__(self):
        pass
    
    def to_gb(self,value):
        """Returns the value of bytes to GB"""
        return round(value / (1024 ** 3), 2)
    
    def _get_cpu_stats(self):
        """Gets the cpu stats"""
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_stats = {
            "cpu_usage":cpu_usage,
            "cpu_cores":cpu_cores,
            "cpu_threads":cpu_threads,
            "cpu_freq":cpu_freq
            }
        if cpu_freq:
            cpu_stats["cpu_frequency"] = f"{cpu_freq.current:.0f}"
        
        cpu_stats["cpu_model"] = self._get_cpu_model()
        return cpu_stats
    
    def _get_cpu_model(self):
        """Gets the CPU manufacturer and model"""

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Processor | "
                "Select-Object Name, Manufacturer, MaxClockSpeed | "
                "ConvertTo-Json"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        return json.loads(result.stdout)
    
    def _get_cpu_temperature(self):
        """Gets available Windows ACPI thermal-zone readings"""

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance -Namespace root/wmi "
                "-ClassName MSAcpi_ThermalZoneTemperature "
                "-ErrorAction Stop | "
                "Select-Object InstanceName, CurrentTemperature | "
                "ConvertTo-Json -Compress"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        data = json.loads(result.stdout)

        if isinstance(data, dict):
            data = [data]

        return [
            {
                "sensor": sensor["InstanceName"],
                "temperature_c": round(
                    sensor["CurrentTemperature"] / 10 - 273.15, 1
                )
            }
            for sensor in data
            if sensor.get("CurrentTemperature") is not None
        ] or None
        
        
    def _get_ram_stats(self):
        """Gets the ram stats"""
        ram = psutil.virtual_memory()
        total_ram_gb = self.to_gb(ram.total)
        used_ram_gb = self.to_gb(ram.used)
        available_ram_gb = self.to_gb(ram.available)
        used_ram_percent = ram.percent
        return {
            "total_ram_gb":total_ram_gb,
            "used_ram_gb":used_ram_gb,
            "available_ram_gb":available_ram_gb,
            "used_ram_percent":used_ram_percent,
            "ram_infomation":self._run_ram_information()
        }
        
    def _run_ram_information(self):
        """Gets RAM information and returns it as a dictionary"""
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_PhysicalMemory | "
                "Select-Object Manufacturer, Capacity, Speed, PartNumber | "
                "ConvertTo-Json"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        ram_info = json.loads(result.stdout)

        return ram_info

    
    def _get_storage_stats(self,drive_path):
        """Gets the storage stats from the drive_path"""
        disk = psutil.disk_usage(drive_path)
        total_disk_gb = self.to_gb(disk.total)
        used_total_gb = self.to_gb(disk.used)
        available_disk_gb = self.to_gb(disk.free)
        used_disk_percentage = disk.percent
        return {
            "total_disk_gb":total_disk_gb,
            "used_total_gb":used_total_gb,
            "available_disk_gb":available_disk_gb,
            "used_disk_percentage":used_disk_percentage
        }
    
    # def _get_network_stats(self):
    #     """Gets the network stats"""
    #     network = psutil.net_io_counters()
    #     sent_network_gb = self.to_gb(network.bytes_sent)
    #     received_network_gb = self.to_gb(network.bytes_recv)
    #     return {
    #         "sent_network_gb":sent_network_gb,
    #         "received_network_gb":received_network_gb
    #     }
        
    def _get_system_info(self):
        """Gets the system infomation"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        os = f"{platform.system()} {platform.release()}"
        formated_uptime = str(timedelta(seconds=int(uptime.total_seconds())))
        return {
            "os":os,
            "uptime":formated_uptime
        }
    
    
    def _get_gpu_information(self):
        """Gets GPU hardware information"""
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object Name, VideoProcessor, "
                "DriverVersion, Status, AdapterRAM | "
                "ConvertTo-Json -Compress"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        gpu_info = json.loads(result.stdout)
        return gpu_info
    
    def get_all_stats(self,drive_path="C:\\"):
        """Gets all the stats"""
        return {
            "cpu_stats":self._get_cpu_stats(),
            "ram_stats":self._get_ram_stats(),
            "storage_stats":self._get_storage_stats(drive_path),
            "network_stats":None,
            "system_info":self._get_system_info(),
            "gpu_info":self._get_gpu_information()
        }

class PCHealth:
    """Class for managing the methods used to get the health of differnet pc parts"""
    def __init__(self):
        pass

    def run_smart_information(self):
        """Gets available physical disk reliability information"""

        command = """
        Get-PhysicalDisk | ForEach-Object {
            $disk = $_

            try {
                $stats = $disk | Get-StorageReliabilityCounter -ErrorAction Stop
            }
            catch {
                $stats = $null
            }

            [PSCustomObject]@{
                Name = $disk.FriendlyName
                MediaType = [string]$disk.MediaType
                HealthStatus = [string]$disk.HealthStatus
                Temperature = if ($stats) { $stats.Temperature } else { $null }
                PowerOnHours = if ($stats) { $stats.PowerOnHours } else { $null }
                Wear = if ($stats) { $stats.Wear } else { $null }
                ReadErrors = if ($stats) { $stats.ReadErrorsTotal } else { $null }
                WriteErrors = if ($stats) { $stats.WriteErrorsTotal } else { $null }
                ReadErrorsUncorrected = if ($stats) { $stats.ReadErrorsUncorrected } else { $null }
                WriteErrorsUncorrected = if ($stats) { $stats.WriteErrorsUncorrected } else { $null }
            }
        } | ConvertTo-Json -Compress
        """

        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=True
        )

        if not result.stdout.strip():
            return []

        drive_info = json.loads(result.stdout)

        if isinstance(drive_info, dict):
            drive_info = [drive_info]

        return drive_info


if __name__ == "__main__":
    pc_health_checker = PCHealth()
    pc_stats = PCStats()
    pc_stats = pc_stats.get_all_stats()
    print(pc_stats)