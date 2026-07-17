"""
FindLeads — Progress Display
Beautiful progress bars using Rich library.
"""

import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, TaskProgressColumn,
    TimeElapsedColumn, TimeRemainingColumn
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console(force_terminal=True)


class FindLeadsProgress:
    """Manage progress display for FindLeads pipeline."""
    
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        self.main_task = None
        self.current_step = 0
        self.total_steps = 7
    
    def __enter__(self):
        self.progress.__enter__()
        return self
    
    def __exit__(self, *args):
        self.progress.__exit__(*args)
    
    def start_pipeline(self, city, business_type, limit):
        """Show pipeline start banner."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_row("City", city)
        table.add_row("Type", business_type)
        table.add_row("Limit", str(limit))
        
        console.print()
        console.print(Panel(table, title="[bold green]PIPELINE STARTED[/]", border_style="green"))
        console.print()
    
    def start_step(self, step_num, description, total_items=100):
        """Start a new pipeline step."""
        self.current_step = step_num
        self.main_task = self.progress.add_task(
            f"[bold blue]Step {step_num}/{self.total_steps}: {description}",
            total=total_items
        )
    
    def update_step(self, advance=1):
        """Update main step progress."""
        if self.main_task is not None:
            self.progress.update(self.main_task, advance=advance)
    
    def set_step_progress(self, completed):
        """Set exact progress for main step."""
        if self.main_task is not None:
            self.progress.update(self.main_task, completed=completed)
    
    def start_sub(self, description, total):
        """Start a sub-task (e.g., processing each lead)."""
        return self.progress.add_task(
            f"  [dim]{description}",
            total=total
        )
    
    def update_sub(self, task_id, advance=1):
        """Advance sub-task."""
        self.progress.update(task_id, advance=advance)
    
    def set_sub_progress(self, task_id, completed):
        """Set exact progress for sub-task."""
        self.progress.update(task_id, completed=completed)
    
    def remove_sub(self, task_id):
        """Remove sub-task when done."""
        self.progress.remove_task(task_id)
    
    def finish_step(self):
        """Finish current step."""
        if self.main_task is not None:
            self.progress.update(self.main_task, completed=self.progress.tasks[self.main_task].total)
            self.main_task = None
    
    def print(self, message):
        """Print message above progress bars."""
        self.progress.console.print(message)
    
    def print_success(self, message):
        """Print success message."""
        self.progress.console.print(f"  [green][OK][/green] {message}")
    
    def print_error(self, message):
        """Print error message."""
        self.progress.console.print(f"  [red][FAIL][/red] {message}")
    
    def print_warning(self, message):
        """Print warning message."""
        self.progress.console.print(f"  [yellow][!][/yellow] {message}")
    
    def print_info(self, message):
        """Print info message."""
        self.progress.console.print(f"  [dim][i][/dim] {message}")
    
    def show_results(self, results):
        """Show final results table."""
        console.print()
        
        table = Table(title="PIPELINE COMPLETE", show_header=True, header_style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")
        
        for key, value in results.items():
            table.add_row(key, str(value))
        
        console.print(Panel(table, border_style="green"))
        console.print()


def format_time(seconds):
    """Format seconds to human readable time."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
