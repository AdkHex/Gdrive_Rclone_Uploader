import os
import glob
import argparse
import subprocess
import shutil
import tempfile
import traceback
import time
import threading
import queue
import re
import pyfiglet
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from colorama import init, Fore, Style
from rich.progress import (
    Progress, 
    BarColumn, 
    TextColumn, 
    TaskProgressColumn, 
    TimeRemainingColumn,
    DownloadColumn
)
from rich.live import Live
from rich.panel import Panel
from rich.table import Table, Column
from rich.console import Group, Console
from rich.text import Text
from rich.layout import Layout
from rich import box
import sys

# Initialize colorama
init()

# Color constants
COLOR_INFO = Fore.CYAN
COLOR_SUCCESS = Fore.GREEN
COLOR_WARNING = Fore.YELLOW
COLOR_ERROR = Fore.RED
COLOR_RESET = Style.RESET_ALL

def color_print(message, color=COLOR_INFO):
    print(f"{color}{message}{COLOR_RESET}")

class GDriveUploader:
    def __init__(self, input_dir, output_folder_id, max_workers=4, chunk_size="8M", transfers=4):
        self.input_dir = os.path.abspath(input_dir)
        self.output_folder_id = output_folder_id
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.transfers = transfers
        self.accounts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts")
        self.service_accounts = self._get_service_accounts()
        self.current_account_index = 0
        self.rclone_path = self._find_rclone()
        self.temp_dir = tempfile.mkdtemp()
        self.upload_stats = defaultdict(dict)
        self.overall_transferred = 0
        self.total_size = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.completed_files = 0
        self.active_uploads = set()
        self.console = Console()
        self.last_update_time = time.time()

    def _create_banner(self):
        banner = pyfiglet.figlet_format("GDrive Uploader", font="slant")
        return banner

    def _find_rclone(self):
        rclone_path = shutil.which("rclone")
        if rclone_path:
            return rclone_path
        local_rclone = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rclone.exe")
        if os.path.exists(local_rclone):
            return local_rclone
        color_print("rclone executable not found. Please install rclone from https://rclone.org/downloads/", COLOR_ERROR)
        raise FileNotFoundError("rclone executable not found")

    def _get_service_accounts(self):
        accounts = glob.glob(os.path.join(self.accounts_dir, "*.json"))
        if not accounts:
            color_print(f"No service account JSON files found in {self.accounts_dir}", COLOR_ERROR)
            raise FileNotFoundError(f"No service account JSON files found in {self.accounts_dir}")
        color_print(f"Found {len(accounts)} service accounts", COLOR_SUCCESS)
        return accounts

    def _get_next_account(self):
        account = self.service_accounts[self.current_account_index]
        next_index = (self.current_account_index + 1) % len(self.service_accounts)
        self.current_account_index = next_index
        return account

    def _create_rclone_config(self, service_account_file):
        config_file = os.path.join(self.temp_dir, f"rclone_{os.path.basename(service_account_file)}.conf")
        is_team_drive = self.output_folder_id.startswith("0A")
        if is_team_drive:
            config_content = f"""[gdrive]\ntype = drive\nscope = drive\nservice_account_file = {service_account_file}\nteam_drive = {self.output_folder_id}\n"""
        else:
            config_content = f"""[gdrive]\ntype = drive\nscope = drive\nservice_account_file = {service_account_file}\nroot_folder_id = {self.output_folder_id}\n"""
        with open(config_file, 'w') as f:
            f.write(config_content)
        return config_file

    def _get_files_to_upload(self):
        all_files = []
        total_size = 0
        for root, dirs, filenames in os.walk(self.input_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, self.input_dir)
                file_size = os.path.getsize(file_path)
                all_files.append((file_path, rel_path, file_size))
                total_size += file_size
        return all_files, total_size

    def _generate_stats_table(self):
        table = Table(
            Column("File", width=45, overflow="ellipsis"),
            Column("Progress", width=25),
            Column("Speed", width=12),
            Column("ETA", width=10),
            Column("Status", width=12),
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 1)
        )
        
        # Add active uploads first
        for rel_path in list(self.active_uploads):
            stats = self.upload_stats.get(rel_path, {})
            if stats:
                transferred = stats.get('transferred', 0)
                size = stats.get('size', 1)
                progress_percent = min(100, int((transferred / size) * 100)) if size > 0 else 0
                
                # Create progress bar
                bar_length = 20
                filled = int(bar_length * progress_percent // 100)
                bar = '━' * filled + ' ' * (bar_length - filled)
                bar_color = "yellow"
                
                # Get ETA and speed
                eta = stats.get('eta', '')
                speed = stats.get('speed', '')
                
                table.add_row(
                    rel_path,
                    f"[{bar_color}]{bar}[/{bar_color}] {progress_percent}%",
                    speed,
                    eta,
                    "[yellow]Uploading[/yellow]"
                )
        
        # Add completed files
        for rel_path, stats in self.upload_stats.items():
            if stats.get('completed') and rel_path not in self.active_uploads:
                table.add_row(
                    f"[green]{rel_path}[/green]",
                    "[green]━━━━━━━━━━━━━━━━━━━━[/green] 100%",
                    "Done",
                    "",
                    "[bold green]✓ Completed[/bold green]"
                )
        
        # Add pending files
        for rel_path, stats in self.upload_stats.items():
            if not stats.get('started') and rel_path not in self.active_uploads:
                table.add_row(
                    f"[dim]{rel_path}[/dim]",
                    "[dim]━━━━━━━━━━━━━━━━━━━━[/dim] 0%",
                    "",
                    "",
                    "[dim]Pending[/dim]"
                )
                
        return table

    def _generate_summary_table(self):
        table = Table.grid(padding=(0, 1))
        table.add_column("Metric", style="bold cyan", width=10)
        table.add_column("Value", style="bold", width=15)
        
        elapsed = time.time() - self.start_time
        transferred_gb = self.overall_transferred / (1024 ** 3)
        total_gb = self.total_size / (1024 ** 3) if self.total_size > 0 else 0
        
        # Calculate progress safely
        progress_percent = 0
        if self.total_size > 0:
            progress_percent = min(100, int((self.overall_transferred / self.total_size) * 100))
        
        # Calculate speed and ETA safely
        speed_mbps = 0
        eta_str = "-:--:--"
        if elapsed > 0:
            speed_bps = self.overall_transferred / elapsed
            speed_mbps = speed_bps / (1024 ** 2)
            
            if speed_bps > 0 and self.total_size > self.overall_transferred:
                remaining_bytes = self.total_size - self.overall_transferred
                remaining_seconds = remaining_bytes / speed_bps
                hours, rem = divmod(remaining_seconds, 3600)
                minutes, seconds = divmod(rem, 60)
                eta_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        table.add_row("Files", str(len(self.upload_stats)))
        table.add_row("Size", f"{total_gb:.2f} GB")
        table.add_row("Uploaded", f"{transferred_gb:.2f} GB")
        table.add_row("Progress", f"{progress_percent}%")
        table.add_row("Speed", f"{speed_mbps:.2f} MB/s")
        table.add_row("Elapsed", time.strftime('%H:%M:%S', time.gmtime(elapsed)))
        table.add_row("ETA", eta_str)
        table.add_row("Active", f"{len(self.active_uploads)}/{self.max_workers}")
        
        return table

    def upload(self):
        # Create banner
        banner = self._create_banner()
        color_print(f"\n{banner}", COLOR_INFO)
        color_print("> V.1.0 By Ionicboy", COLOR_INFO)
        color_print(f"{self.input_dir} → {self.output_folder_id}\n", COLOR_INFO)
        
        all_files, self.total_size = self._get_files_to_upload()
        total_files = len(all_files)
        
        if total_files == 0:
            color_print("No files found to upload", COLOR_WARNING)
            return

        # Initialize upload stats
        for file_path, rel_path, file_size in all_files:
            self.upload_stats[rel_path] = {
                'size': file_size,
                'transferred': 0,
                'speed': '',
                'eta': '',
                'completed': False,
                'failed': False,
                'started': False
            }
        
        # Create progress components
        overall_progress = Progress(
            TextColumn("[bold blue]Overall Progress", justify="right"),
            BarColumn(bar_width=None, complete_style="blue", finished_style="green"),
            TaskProgressColumn(),
            TextColumn("•"),
            DownloadColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            expand=True
        )
        
        # Create layout
        layout = Layout()
        layout.split(
            Layout(name="progress", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4)
        )
        layout["main"].split_row(
            Layout(name="summary", size=30),
            Layout(name="status", ratio=2)
        )
        
        with Live(layout, refresh_per_second=20, screen=True) as live:
            overall_task = overall_progress.add_task("", total=self.total_size)
            layout["progress"].update(Panel(overall_progress, title="Overall Progress", padding=(0, 1)))
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for file_path, rel_path, file_size in all_files:
                    future = executor.submit(
                        self.upload_worker, 
                        file_path, 
                        rel_path, 
                        file_size
                    )
                    futures.append(future)
                
                # Update display while tasks are running
                while not all(future.done() for future in futures):
                    # Update progress bar
                    overall_progress.update(overall_task, completed=self.overall_transferred)
                    
                    # Update main content
                    summary_table = self._generate_summary_table()
                    stats_table = self._generate_stats_table()
                    
                    layout["summary"].update(Panel(summary_table, title="Upload Summary", padding=(0, 1)))
                    layout["status"].update(Panel(stats_table, title="File Status", padding=(0, 1)))
                    
                    # Update footer with active transfers
                    active_text = Text("Active Uploads: ", style="bold yellow")
                    if self.active_uploads:
                        for rel_path in self.active_uploads:
                            stats = self.upload_stats.get(rel_path, {})
                            transferred = stats.get('transferred', 0)
                            size = stats.get('size', 1)
                            percent = min(100, int((transferred / size) * 100)) if size > 0 else 0
                            speed = stats.get('speed', '')
                            active_text.append(f"\n  - {rel_path}: {percent}% ({speed})")
                    else:
                        active_text.append(" [dim]None[/dim]")
                    
                    layout["footer"].update(Panel(active_text, title="Current Transfers", padding=(0, 1)))
                    
                    time.sleep(0.05)
            
            # Final update
            overall_progress.update(overall_task, completed=self.overall_transferred)
            summary_table = self._generate_summary_table()
            stats_table = self._generate_stats_table()
            layout["summary"].update(Panel(summary_table, title="Upload Summary", padding=(0, 1)))
            layout["status"].update(Panel(stats_table, title="File Status", padding=(0, 1)))
            
            # Show completion message
            layout["footer"].update(Panel(Text("All uploads completed!", style="bold green"), title="Status"))
            
            # Keep the screen for 5 seconds
            time.sleep(5)
        
        # Cleanup and show results
        successful_uploads = sum(1 for stats in self.upload_stats.values() if stats.get('completed'))
        failed_uploads = total_files - successful_uploads
        
        color_print(f"\nUpload completed: {successful_uploads}/{total_files} files uploaded successfully", 
                   COLOR_SUCCESS if successful_uploads == total_files else COLOR_WARNING)
        
        if failed_uploads > 0:
            color_print("\nFailed files:", COLOR_WARNING)
            for rel_path, stats in self.upload_stats.items():
                if not stats.get('completed'):
                    color_print(f"  - {rel_path}", COLOR_WARNING)
        
        shutil.rmtree(self.temp_dir)

    def upload_worker(self, file_path, rel_path, file_size):
        # Mark as started
        with self.lock:
            self.upload_stats[rel_path]['started'] = True
            self.active_uploads.add(rel_path)
        
        service_account = self._get_next_account()
        config_file = self._create_rclone_config(service_account)
        dest_path = f"gdrive:{os.path.dirname(rel_path)}" if os.path.dirname(rel_path) else "gdrive:/"
        
        cmd = [
            self.rclone_path,
            "--config", config_file,
            "copy",
            "--drive-chunk-size", self.chunk_size,
            "--transfers", "1",  # Set transfers to 1 per worker
            "--stats", "1s",
            "--progress",
            file_path,
            dest_path
        ]
        
        try:
            # Create environment for rclone with progress enabled
            env = os.environ.copy()
            env["RCLONE_PROGRESS"] = "true"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr with stdout
                universal_newlines=True,
                bufsize=1,
                env=env
            )
            
            q = queue.Queue()
            
            def enqueue_output(pipe, q):
                for line in iter(pipe.readline, ''):
                    q.put(line)
                pipe.close()
                
            t_out = threading.Thread(target=enqueue_output, args=(process.stdout, q))
            t_out.daemon = True
            t_out.start()
            
            last_transferred = 0
            last_percent = 0
            last_speed = ""
            last_eta = ""
            
            while True:
                try:
                    line = q.get(timeout=0.1)
                except queue.Empty:
                    if process.poll() is not None:
                        break
                    continue
                
                # Parse progress information with improved regex
                percent_match = re.search(r"(\d+)%", line)
                speed_match = re.search(r"([\d.]+\s*[KMG]?Bytes/s)", line)
                eta_match = re.search(r"ETA\s+([\d\w:]+)", line)
                
                # Update values only if found
                if percent_match:
                    last_percent = int(percent_match.group(1))
                if speed_match:
                    last_speed = speed_match.group(1).strip()
                if eta_match:
                    last_eta = eta_match.group(1).strip()
                
                # Calculate bytes transferred
                transferred_bytes = file_size * last_percent // 100
                delta = transferred_bytes - last_transferred
                last_transferred = transferred_bytes
                
                # Update stats
                with self.lock:
                    self.overall_transferred += delta
                    self.upload_stats[rel_path].update({
                        'transferred': transferred_bytes,
                        'speed': last_speed,
                        'eta': last_eta
                    })
            
            process.wait()
            
            # Final update
            with self.lock:
                if process.returncode == 0:
                    # Ensure we account for any remaining bytes
                    remaining_bytes = file_size - last_transferred
                    self.overall_transferred += remaining_bytes
                    self.completed_files += 1
                    
                    self.upload_stats[rel_path].update({
                        'transferred': file_size,
                        'speed': 'Done',
                        'eta': '',
                        'completed': True
                    })
                else:
                    self.upload_stats[rel_path].update({
                        'speed': 'Failed',
                        'failed': True
                    })
                
                self.active_uploads.remove(rel_path)
                    
        except Exception as e:
            with self.lock:
                self.upload_stats[rel_path].update({
                    'speed': 'Error',
                    'failed': True
                })
                self.active_uploads.remove(rel_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Drive Parallel Uploader")
    parser.add_argument("input_dir", help="Input directory to upload")
    parser.add_argument("output_folder_id", help="Google Drive folder ID")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel uploads")
    parser.add_argument("--chunk-size", default="8M", help="Upload chunk size")
    parser.add_argument("--transfers", type=int, default=4, help="Number of file transfers")
    
    args = parser.parse_args()
    
    uploader = GDriveUploader(
        input_dir=args.input_dir,
        output_folder_id=args.output_folder_id,
        max_workers=args.workers,
        chunk_size=args.chunk_size,
        transfers=args.transfers
    )
    
    try:
        uploader.upload()
    except KeyboardInterrupt:
        color_print("\nUpload canceled by user", COLOR_WARNING)
    except Exception as e:
        color_print(f"\nCritical error: {str(e)}", COLOR_ERROR)
        traceback.print_exc()
