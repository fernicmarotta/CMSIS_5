# RTX5 GDB Awareness Script
# Provides runtime information about RTX5 objects in GDB
# Output is presented in ASCII text format with tree and table styles.

import gdb
import datetime
import os # Import os for _check_ui_support


# Global flag for UI support
UI_ENABLED = True


def _check_ui_support():
    """Check if terminal supports colors/TUI."""
    global UI_ENABLED
    try:
        # Attempt to enable TUI, which will fail if not supported
        gdb.execute("tui enable", to_string=True)
        UI_ENABLED = True
    except gdb.error:
        UI_ENABLED = False

    # Also check if we're in a dumb terminal, which typically doesn't support ANSI codes
    if os.environ.get('TERM') == 'dumb':
        UI_ENABLED = False


def _color(text, color_code):
    """Apply color if UI is enabled."""
    if UI_ENABLED:
        return f"{color_code}{text}{Colors.RESET}"
    return text


def _cstr(val):
    """Read C string from pointer, handling NULL and errors."""
    try:
        if int(val) == 0:
            return None
        return val.string()
    except gdb.error:
        return None


def _format_percentage_bar(used, total, width=20):
    """Create a visual percentage bar."""
    if total == 0:
        return "N/A"
    percent = (used * 100) // total
    filled = (used * width) // total
    bar = ""
    for i in range(width):
        if i < filled:
            if percent > 80:
                bar += _color("█", Colors.RED)
            elif percent > 50:
                bar += _color("█", Colors.YELLOW)
            else:
                bar += _color("█", Colors.GREEN)
        else:
            bar += _color("░", Colors.DIM)
    return f"{bar} {percent:3d}% ({used}/{total})"


def _symbol_at(addr, max_len=None):
    """Return symbol name for *addr* if available, optionally truncated.
    Handles various GDB 'info symbol' outputs and anonymous symbols.
    """
    try:
        addr_int = int(addr)
        if addr_int == 0:
            return "NULL"

        out = gdb.execute(f"info symbol {addr_int}", to_string=True).strip()

        # Case 1: No symbol found
        if "No symbol matches" in out:
            return f"0x{addr_int:08x}"

        # Case 2: Extract symbol name from various common GDB output formats
        symbol_name = out
        if " in section " in out:
            symbol_name = out.split(" in section ")[0].strip()
        elif " at address " in out: # Handles "symbol_name at address 0x..."
            symbol_name = out.split(" at address ")[0].strip()
        elif " (from " in out: # Handles "symbol_name (from /path/to/file.o)"
            symbol_name = out.split(" (from ")[0].strip()

        # If the symbol name is an anonymous symbol, keep it concise.
        # Otherwise, apply truncation if max_len is specified and the name is too long.
        if symbol_name.startswith("[Anonymous Symbol]"):
            # No truncation for anonymous symbols, they are already concise.
            pass
        elif max_len and len(symbol_name) > max_len:
            # Ensure at least 3 characters for "..."
            if max_len >= 3:
                return symbol_name[:max_len-3] + "..."
            else:
                return symbol_name[:max_len] # If max_len is too small for "...", just truncate
        return symbol_name
    except gdb.error:
        # Fallback to address if GDB command fails for any reason
        return f"0x{int(addr):08x}"


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'


class UI:
    """UI helpers for both colored and plain output."""

    @staticmethod
    def header(title):
        """Prints a large, decorative header."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        full_title = f"{title} [{ts}]"
        line_length = 79 # Total width of the box
        inner_width = line_length - 4 # For padding and borders
        title_padding = (inner_width - len(full_title)) // 2
        title_str = " " * title_padding + full_title + " " * (inner_width - len(full_title) - title_padding)

        if UI_ENABLED:
            gdb.write(f"\n{_color('╔' + '═' * (line_length - 2) + '╗', Colors.BRIGHT_MAGENTA)}\n")
            gdb.write(f"{_color('║', Colors.BRIGHT_MAGENTA)}{_color(title_str, Colors.BRIGHT_CYAN)}{_color('║', Colors.BRIGHT_MAGENTA)}\n")
            gdb.write(f"{_color('╚' + '═' * (line_length - 2) + '╝', Colors.BRIGHT_MAGENTA)}\n")
        else:
            gdb.write(f"\n{'=' * 10} {full_title} {'=' * 10}\n")

    @staticmethod
    def section(title):
        """Prints a section header with top/bottom borders."""
        line_length = 79 # Total width of the box
        inner_width = line_length - 4 # For padding and borders
        title_padding = (inner_width - len(title)) // 2
        title_str = " " * title_padding + title + " " * (inner_width - len(title) - title_padding)

        if UI_ENABLED:
            gdb.write(f"\n{_color('┌' + '─' * (line_length - 2) + '┐', Colors.CYAN)}\n")
            gdb.write(f"{_color('│', Colors.CYAN)}{_color(title_str, Colors.CYAN)}{_color('│', Colors.CYAN)}\n")
            gdb.write(f"{_color('├' + '─' * (line_length - 2) + '┤', Colors.CYAN)}\n") # Separator line after title
        else:
            gdb.write(f"\n{title}\n{'-' * len(title)}\n")

    @staticmethod
    def section_footer():
        """Prints the closing border for a section."""
        line_length = 79
        if UI_ENABLED:
            gdb.write(f"{_color('└' + '─' * (line_length - 2) + '┘', Colors.CYAN)}\n")
        else:
            gdb.write("\n") # Just a newline for plain text


    @staticmethod
    def table_header(headers):
        """Prints a table header row."""
        # Calculate maximum width for each column
        col_widths = [len(h) for h in headers]
        header_str = " | ".join(headers)
        gdb.write(f"{Colors.BOLD}{header_str}{Colors.RESET}\n")
        gdb.write("-" * len(header_str) + "\n")

    @staticmethod
    def table_row(row_items, col_widths=None):
        """Prints a table data row."""
        # If col_widths are provided, format items to align
        if col_widths:
            formatted_items = [f"{item:<{width}}" for item, width in zip(row_items, col_widths)]
            gdb.write(" | ".join(formatted_items) + "\n")
        else:
            gdb.write(" | ".join(row_items) + "\n")

    @staticmethod
    def table_sep():
        """Table separator line."""
        if UI_ENABLED:
            return _color("├" + "─" * 70 + "┤", Colors.DIM)
        else:
            return "-" * 72


class Rtx5Awareness:
    """Main RTX5 awareness implementation."""

    def __init__(self):
        self.info = None
        self.config = None
        self.init_constants()

    def init_constants(self):
        """Initialize state mappings and constants."""
        # Thread states - complete mapping
        self.thread_states = {
            0x00: ("INACTIVE", Colors.DIM),
            0x01: ("READY", Colors.GREEN),
            0x02: ("RUNNING", Colors.BRIGHT_GREEN),
            0x03: ("BLOCKED", Colors.YELLOW),
            0x04: ("TERMINATED", Colors.RED),
            0x13: ("WAIT_DELAY", Colors.YELLOW),
            0x23: ("WAIT_JOIN", Colors.YELLOW),
            0x33: ("WAIT_THREAD_FLAGS", Colors.YELLOW),
            0x43: ("WAIT_EVENT_FLAGS", Colors.YELLOW),
            0x53: ("WAIT_MUTEX", Colors.YELLOW),
            0x63: ("WAIT_SEMAPHORE", Colors.YELLOW),
            0x73: ("WAIT_MEMORY_POOL", Colors.YELLOW),
            0x83: ("WAIT_MESSAGE_GET", Colors.YELLOW),
            0x93: ("WAIT_MESSAGE_PUT", Colors.YELLOW),
        }

        # Thread flags/attributes
        self.thread_attr_flags = {
            0x01: "Detached",
            0x02: "Joinable",
            0x04: "Unprivileged",
            0x08: "FPU Context",
            0x10: "Stack Check",
            0x20: "Stack Watermark",
        }

        # Thread priorities (simplified for display)
        self.thread_priorities = {
            0: "osPriorityNone",
            1: "osPriorityIdle",
            8: "osPriorityLow",
            9: "osPriorityLow1", # Added based on user output
            15: "osPriorityLow7",
            16: "osPriorityBelowNormal",
            23: "osPriorityBelowNormal7",
            24: "osPriorityNormal",
            30: "osPriorityNormal6", # Added based on user output (for 30)
            31: "osPriorityNormal7",
            32: "osPriorityAboveNormal",
            39: "osPriorityAboveNormal7",
            40: "osPriorityHigh",
            47: "osPriorityHigh7",
            48: "osPriorityRealtime",
            55: "osPriorityRealtime7",
            56: "osPriorityISR",
            -1: "osPriorityError",
        }


        # Timer states
        self.timer_states = {
            0x00: ("INACTIVE", Colors.DIM),
            0x01: ("STOPPED", Colors.YELLOW),
            0x02: ("RUNNING", Colors.GREEN),
        }

        # Timer types
        self.timer_types = {
            0x00: "One-shot",
            0x01: "Periodic",
        }

        # Mutex attributes
        self.mutex_attr = {
            0x01: "Recursive",
            0x02: "PrioInherit",
            0x08: "Robust",
        }

        # Event flags options (from osRtxThread_t flags_options)
        self.event_flags_opts = {
            0x00: "osFlagsWaitAny",
            0x01: "osFlagsWaitAll",
            0x02: "osFlagsNoClear",
        }

        # Kernel states
        self.kernel_states = {
            0x00: ("osKernelInactive", Colors.RED),
            0x01: ("osKernelReady", Colors.YELLOW),
            0x02: ("osKernelRunning", Colors.BRIGHT_GREEN),
            0x03: ("osKernelLocked", Colors.YELLOW),
            0x04: ("osKernelSuspended", Colors.BLUE),
            0x05: ("osKernelError", Colors.RED),
        }

        # Kernel flags (from osRtxConfig_t flags)
        self.kernel_config_flags = {
            0x01: "Privileged Mode",
            0x02: "Stack Check",
            0x04: "Stack Watermark",
            0x40: "Safety Features",
            0x80: "Safety Class",
            0x100: "Execution Zone",
            0x200: "Thread Watchdog",
            0x400: "Object Ptr Check",
            0x800: "SVC Ptr Check",
        }

        # Constants for global heap iteration (from rtx_memory.c)
        self.MB_INFO_LEN_MASK = 0xFFFFFFFC
        self.MB_INFO_TYPE_MSK = 0x00000003
        self.MB_TYPE_MEM = 0x00
        self.MB_TYPE_MP = 0x01
        self.MB_TYPE_MQ = 0x02

        # RTX Object IDs (from rtx_os.h / rtx_def.h)
        self.RTX_OBJ_ID_THREAD = 0xF1
        self.RTX_OBJ_ID_TIMER = 0xF2
        self.RTX_OBJ_ID_EVENTFLAGS = 0xF3
        self.RTX_OBJ_ID_MUTEX = 0xF5
        self.RTX_OBJ_ID_SEMAPHORE = 0xF6
        self.RTX_OBJ_ID_MEMORYPOOL = 0xF7
        self.RTX_OBJ_ID_MESSAGEQUEUE = 0xFA


    def _get_enum_name(self, enum_map, value):
        """Helper to get human-readable enum name."""
        return enum_map.get(value, str(value))


    def load_symbols(self):
        """Load RTX5 symbols from target."""
        try:
            self.info = gdb.parse_and_eval("osRtxInfo")
            self.config = gdb.parse_and_eval("osRtxConfig")
            return True
        except gdb.error as e:
            gdb.write(_color(f"Error: Failed to load RTX5 symbols (osRtxInfo, osRtxConfig). Ensure you are debugging an RTX5 application. Details: {e}\n", Colors.BRIGHT_RED))
            return False

    def show_kernel_info(self):
        """Display comprehensive kernel information."""
        k = self.info["kernel"]

        UI.section("Kernel Information")

        # Basic kernel state
        state = int(k['state'])
        state_str, state_color = self.kernel_states.get(state, (f"UNKNOWN({state})", Colors.RED))

        gdb.write(f"State: {_color(state_str, state_color)}")
        gdb.write(f"  Tick: {int(k['tick'])}")

        # Version info
        kernel_version = "N/A"
        api_version = "N/A"
        try:
            ver = gdb.parse_and_eval("osRtxVersionKernel")
            api = gdb.parse_and_eval("osRtxVersionAPI")
            kernel_version = f"{int(ver / 10000000)}.{int((ver / 10000) % 1000)}.{int(ver % 10000)}"
            api_version = f"{int(api / 10000000)}.{int((api / 10000) % 1000)}.{int(api % 10000)}"
        except gdb.error:
            pass # Symbols not found, keep N/A

        gdb.write(f"  Version: {kernel_version}")
        gdb.write(f"  API: {api_version}\n")

        # SysTick Frequency
        sys_tick_freq = "N/A"
        try:
            sys_tick_freq = f"{int(self.config['tick_freq'])}Hz"
        except gdb.error:
            pass
        gdb.write(f"SysTickFreq: {sys_tick_freq}")

        # Round-Robin Timeout
        rr_timeout_ms = "N/A"
        try:
            rr_ticks = int(self.config['robin_timeout'])
            tick_freq = int(self.config['tick_freq'])
            if tick_freq > 0:
                rr_timeout_ms = f"{int(rr_ticks * 1000 / tick_freq)}ms"
            else:
                rr_timeout_ms = f"{rr_ticks} ticks" # Fallback if freq is 0
        except gdb.error:
            pass
        gdb.write(f"  RoundRobin: {rr_timeout_ms}")

        # ISR FIFO Info
        isr_fifo_entries = "N/A"
        try:
            isr = self.info['isr_queue']
            isr_fifo_entries = f"{int(isr['max'])} entries"
        except gdb.error:
            pass
        gdb.write(f"  ISR FIFO: {isr_fifo_entries}\n")


        gdb.write(f"PendSV: {int(k['pendSV'])}  ")
        gdb.write(f"Blocked: {int(k['blocked'])}  ")
        # Check for 'sleep' member before accessing
        if 'sleep' in k.type.fields():
            gdb.write(f"Sleep: {int(k['sleep'])}\n")
        else:
            gdb.write(f"Sleep: N/A\n")
        UI.section_footer()


    def show_kernel_config(self):
        """Display kernel configuration details."""
        c = self.config

        UI.section("Kernel Configuration")

        # Decode flags
        flags = int(c['flags'])
        gdb.write(f"\nFlags: 0x{flags:08x}\n")
        # Use UI.tree for flags
        flag_lines = []
        for bit_val, name in self.kernel_config_flags.items():
            status_char = "✓" if flags & bit_val else " "
            status_color = Colors.GREEN if flags & bit_val else Colors.DIM
            flag_lines.append(f"[{_color(status_char, status_color)}] {name}")
        # Use UI.tree for flags, without the specific '├─' and '└─' for better integration
        for line in flag_lines:
            gdb.write(f"  {line}\n")


        gdb.write(f"\nMemory Configuration:\n")

        # Global Stack (if applicable, though often per-thread)
        # This is hard to get accurately for overall usage without specific symbols.
        # For now, we'll show the configured global stack if it exists.
        mem = c['mem']
        if int(mem['stack_addr']):
            stack_size = int(mem['stack_size'])
            # Cannot easily get global stack usage without specific symbols
            gdb.write(f"  Global Stack: 0x{int(mem['stack_addr']):08x} ({stack_size} bytes) - N/A used\n")
        else:
            gdb.write(f"  Global Stack: Not used\n")

        # Global Heap (Dynamic Memory)
        try:
            os_mem_val = gdb.parse_and_eval("os_mem") # This is the array
            # The mem_head_t structure is at the very beginning of this memory block
            mem_head_type = gdb.lookup_type("mem_head_t").pointer()
            mem_head = os_mem_val.address.cast(mem_head_type).dereference()

            heap_size = int(mem_head['size'])
            heap_used = int(mem_head['used'])
            if heap_size > 0:
                gdb.write(f"  Global Heap: 0x{int(os_mem_val.address):08x} ({heap_size} bytes) - {_format_percentage_bar(heap_used, heap_size)}\n")
            else:
                gdb.write(f"  Global Heap: Not configured or size is 0\n")
        except gdb.error as e:
            gdb.write(f"  Global Heap: N/A (Error accessing os_mem: {e})\n")

        # MP/MQ data
        if int(mem['mp_data_addr']):
            mp_size = int(mem['mp_data_size'])
            gdb.write(f"  MP Data: 0x{int(mem['mp_data_addr']):08x} ({mp_size} bytes)\n")
        else:
            gdb.write(f"  MP Data: Not used\n")

        if int(mem['mq_data_addr']):
            mq_size = int(mem['mq_data_size'])
            gdb.write(f"  MQ Data: 0x{int(mem['mq_data_addr']):08x} ({mq_size} bytes)\n")
        else:
            gdb.write(f"  MQ Data: Not used\n")

        # Common memory
        if int(mem['common_addr']):
            common_size = int(mem['common_size'])
            gdb.write(f"  Common: 0x{int(mem['common_addr']):08x} ({common_size} bytes)\n")
        else:
            gdb.write(f"  Common: Not used\n")


        # ISR Configuration
        gdb.write(f"\nISR Configuration:\n")
        try:
            isr = self.info['isr_queue']
            gdb.write(f"  FIFO Size: {int(isr['max'])} entries\n")
            if 'watermark' in isr.type.fields():
                watermark = int(isr['watermark'])
                fifo_size = int(isr['max'])
                watermark_percent = (watermark * 100) // fifo_size if fifo_size else 0
                gdb.write(f"  Watermark: {watermark} entries ({watermark_percent}%)\n")
            else:
                gdb.write(f"  Watermark: N/A (member not found)\n")
        except gdb.error:
            gdb.write(f"  ISR FIFO: (Information not available)\n")

        try:
            # Check for ISR stack info directly in osRtxInfo
            if 'stack_info' in self.info.type.fields() and 'isr_stack_size' in self.info['stack_info'].type.fields():
                isr_stack_size = int(self.info['stack_info']['isr_stack_size'])
                gdb.write(f"  Stack Size: {isr_stack_size} bytes\n")
            else:
                gdb.write(f"  Stack Size: N/A (info.stack_info.isr_stack_size not found)\n")
        except gdb.error:
            gdb.write(f"  Stack Size: N/A (Error accessing ISR stack info)\n")
        UI.section_footer()


    def show_system_info(self):
        """Show system threads and handlers."""
        UI.section("System Threads & Configuration")

        # Idle thread
        try:
            idle_thread_ptr = self.info["thread"]["idle"]
            if int(idle_thread_ptr) != 0:
                idle_thread = idle_thread_ptr.dereference()
                gdb.write(f"\nIdle Thread:\n")
                gdb.write(f"  Address: 0x{int(idle_thread_ptr):x}\n")
                gdb.write(f"  Name: {_cstr(idle_thread['name'])}\n")
                gdb.write(f"  Stack Size: {int(idle_thread['stack_size'])} bytes\n")
                gdb.write(f"  Priority: {self._get_enum_name(self.thread_priorities, int(idle_thread['priority']))}\n")
                gdb.write(f"  Entry: {_symbol_at(int(idle_thread['thread_addr']))}\n") # No truncation for detailed view
            else:
                gdb.write("\nIdle Thread: (Not found or inactive)\n")
        except gdb.error as e:
            gdb.write(f"\nIdle Thread: (Error accessing: {e})\n")


        # Timer thread
        try:
            timer_thread_ptr = self.info["timer"]["thread"]
            if int(timer_thread_ptr) != 0:
                timer_thread = timer_thread_ptr.dereference()
                gdb.write(f"\nTimer Thread:\n")
                gdb.write(f"  Address: 0x{int(timer_thread_ptr):x}\n")
                gdb.write(f"  Name: {_cstr(timer_thread['name'])}\n")
                gdb.write(f"  Stack Size: {int(timer_thread['stack_size'])} bytes\n")
                gdb.write(f"  Priority: {self._get_enum_name(self.thread_priorities, int(timer_thread['priority']))}\n")
                gdb.write(f"  Entry: {_symbol_at(int(timer_thread['thread_addr']))}\n") # No truncation for detailed view

                # Timer message queue info
                timer_mq_ptr = self.info["timer"]["mq"]
                if int(timer_mq_ptr) != 0:
                    timer_mq = timer_mq_ptr.dereference()
                    mq_capacity = "N/A"
                    mq_msg_size = "N/A"
                    try:
                        # Access max_msgs directly from the message queue object
                        if 'max_msgs' in timer_mq.type.fields():
                            mq_capacity = str(int(timer_mq['max_msgs']))
                        else:
                            gdb.write(f"{Colors.YELLOW}Warning: 'max_msgs' member not found in timer message queue at 0x{int(timer_mq_ptr):x}.{Colors.RESET}\n")

                        if 'msg_size' in timer_mq.type.fields():
                            mq_msg_size = str(int(timer_mq['msg_size']))
                        else:
                            gdb.write(f"{Colors.YELLOW}Warning: 'msg_size' member not found in timer message queue at 0x{int(timer_mq_ptr):x}.{Colors.RESET}\n")

                        gdb.write(f"  Message Queue: {_cstr(timer_mq['name'])} (Capacity: {mq_capacity}, Msg Size: {mq_msg_size})\n")
                    except gdb.error as mq_e:
                        gdb.write(f"  Message Queue: (Error accessing: {mq_e})\n")
                else:
                    gdb.write(f"  Message Queue: (Not found or inactive)\n")
            else:
                gdb.write("\nTimer Thread: (Not found or inactive)\n")
        except gdb.error as e:
            gdb.write(f"\nTimer Thread: (Error accessing: {e})\n")


        # Handlers (from osRtxInfo for runtime handlers)
        gdb.write(f"\nSystem Handlers (from osRtxInfo):\n")
        handlers_info = [
            ("post_process.thread", "Post-Process (Thread)", "post_process"),
            ("post_process.event_flags", "Post-Process (Event Flags)", "post_process"),
            ("post_process.semaphore", "Post-Process (Semaphore)", "post_process"),
            ("post_process.memory_pool", "Post-Process (Memory Pool)", "post_process"),
            ("post_process.message", "Post-Process (Message Queue)", "post_process"),
            ("timer.tick", "Timer Tick Function", "timer"),
        ]

        for field_path, display_name, parent_field in handlers_info:
            try:
                if parent_field:
                    # Access nested field
                    handler_val = self.info[parent_field][field_path.split('.')[-1]]
                else:
                    handler_val = self.info[field_path]

                if int(handler_val) != 0:
                    gdb.write(f"  {display_name}: {_symbol_at(int(handler_val))}\n") # No truncation for detailed view
                else:
                    gdb.write(f"  {display_name}: (Not set)\n")
            except gdb.error:
                gdb.write(f"  {display_name}: (N/A or Error)\n")
        UI.section_footer()


    def show_threads(self):
        """Display detailed thread information."""
        UI.section("Threads")

        all_threads_data = []
        seen_thread_addresses = set()

        # 1. Primary method: Attempt to read threads from linked lists
        try:
            gdb.write(f"{Colors.CYAN}Reading Threads from linked lists...{Colors.RESET}\n")

            # Ready threads
            ready_list_head = self.info["thread"]["ready"]["thread_list"]
            if int(ready_list_head) != 0:
                for t in self._iterate_threads(ready_list_head, "thread_next"):
                    thread_address = int(t.address)
                    if thread_address not in seen_thread_addresses:
                        seen_thread_addresses.add(thread_address)
                        all_threads_data.append(self._format_thread_data(t))

            # Delay threads
            delay_list_head = self.info["thread"]["delay_list"]
            if int(delay_list_head) != 0:
                for t in self._iterate_threads(delay_list_head, "delay_next"):
                    thread_address = int(t.address)
                    if thread_address not in seen_thread_addresses:
                        seen_thread_addresses.add(thread_address)
                        all_threads_data.append(self._format_thread_data(t))

            # Wait threads (generic wait list)
            wait_list_head = self.info["thread"]["wait_list"]
            if int(wait_list_head) != 0:
                for t in self._iterate_threads(wait_list_head, "thread_next"):
                    thread_address = int(t.address)
                    if thread_address not in seen_thread_addresses:
                        seen_thread_addresses.add(thread_address)
                        all_threads_data.append(self._format_thread_data(t))

            # Terminated threads (if available)
            if 'terminated_list' in self.info["thread"].type.fields():
                terminated_list_head = self.info["thread"]["terminated_list"]
                if int(terminated_list_head) != 0:
                    for t in self._iterate_threads(terminated_list_head, "thread_next"):
                        thread_address = int(t.address)
                        if thread_address not in seen_thread_addresses:
                            seen_thread_addresses.add(thread_address)
                            all_threads_data.append(self._format_thread_data(t))

            # Watchdog threads (if enabled)
            if 'wdog_list' in self.info["thread"].type.fields():
                wdog_list_head = self.info["thread"]["wdog_list"]
                if int(wdog_list_head) != 0:
                    for t in self._iterate_threads(wdog_list_head, "delay_next"):
                        thread_address = int(t.address)
                        if thread_address not in seen_thread_addresses:
                            seen_thread_addresses.add(thread_address)
                            all_threads_data.append(self._format_thread_data(t))

            # Add current running thread explicitly if not already in list
            try:
                current_running_thread = self.info["thread"]["run"]["curr"]
                if int(current_running_thread) != 0 and int(current_running_thread.address) not in seen_thread_addresses:
                    seen_thread_addresses.add(int(current_running_thread.address))
                    all_threads_data.append(self._format_thread_data(current_running_thread.dereference()))
            except gdb.error:
                pass # Current running thread might not be available or accessible

        except gdb.error as e:
            gdb.write(f"{Colors.RED}Error: Failed to retrieve thread data from linked lists: {e}{Colors.RESET}\n")


        # 2. Fallback method: If no threads found via linked lists, attempt to read from os_cb_sections
        if not all_threads_data:
            gdb.write(f"{Colors.YELLOW}No threads found via linked lists. Attempting to read from os_cb_sections (static allocation).{Colors.RESET}\n")
            try:
                cb_sections_array = gdb.parse_and_eval("os_cb_sections")
                thread_cb_start = int(cb_sections_array[0].dereference())
                thread_cb_end = int(cb_sections_array[1].dereference())

                # Add a more robust check for plausible memory ranges
                MAX_PLAUSIBLE_CB_SECTION_SIZE = 16 * 1024 * 1024 # 16 MB
                MIN_PLAUSIBLE_START_ADDR = 0x8000 # Avoid very low addresses that might be vectors/registers
                MAX_PLAUSIBLE_END_ADDR = 0x80000000 # A heuristic for typical 32-bit RAM upper bound

                if (thread_cb_start != 0 and thread_cb_end != 0 and
                        thread_cb_end > thread_cb_start and
                        (thread_cb_end - thread_cb_start) < MAX_PLAUSIBLE_CB_SECTION_SIZE and
                        thread_cb_start >= MIN_PLAUSIBLE_START_ADDR and
                        thread_cb_end < MAX_PLAUSIBLE_END_ADDR):

                    thread_type = gdb.lookup_type("osRtxThread_t")
                    thread_size = thread_type.sizeof

                    current_addr = thread_cb_start
                    gdb.write(f"{Colors.GREEN}Reading threads from os_cb_sections (static allocation range: 0x{thread_cb_start:x}-0x{thread_cb_end:x}).{Colors.RESET}\n")
                    while current_addr < thread_cb_end:
                        try:
                            t_ptr = gdb.Value(current_addr).cast(thread_type.pointer())
                            t = t_ptr.dereference()
                            # Check for valid thread object ID and not INACTIVE state
                            if int(t['id']) == self.RTX_OBJ_ID_THREAD and int(t['state']) != self.thread_states[0x00][0]:
                                thread_address = int(t.address)
                                if thread_address not in seen_thread_addresses:
                                    seen_thread_addresses.add(thread_address)
                                    all_threads_data.append(self._format_thread_data(t))
                            current_addr += thread_size
                        except gdb.error as e:
                            gdb.write(f"{Colors.YELLOW}Warning: Error reading thread CB at 0x{current_addr:x} from os_cb_sections: {e}. Skipping to next possible block.{Colors.RESET}\n")
                            current_addr += thread_size
                    if all_threads_data:
                        gdb.write(f"{Colors.GREEN}Finished reading from os_cb_sections.{Colors.RESET}\n")
                else:
                    gdb.write(f"{Colors.YELLOW}Info: os_cb_sections for threads is empty, invalid range (0x{thread_cb_start:x}-0x{thread_cb_end:x}), or implausible. No threads found via static sections.{Colors.RESET}\n")
            except gdb.error as e:
                gdb.write(f"{Colors.YELLOW}Warning: Could not read thread control blocks from 'os_cb_sections' symbol: {e}. This is expected if objects are not statically allocated or if the symbol is not available. No threads found via static sections.{Colors.RESET}\n")


        if not all_threads_data:
            gdb.write("  (none)\n\n")
            UI.section_footer()
            return

        # Sort threads by state for consistent grouping
        all_threads_data.sort(key=lambda x: x["state"])

        # Group threads by state
        threads_by_state = {}
        for thread in all_threads_data:
            state = thread["state"]
            if state not in threads_by_state:
                threads_by_state[state] = []
            threads_by_state[state].append(thread)

        # Define a preferred order for states for display
        state_order_keys = [
            self.thread_states[0x02][0], # RUNNING
            self.thread_states[0x01][0], # READY
            self.thread_states[0x13][0], # WAIT_DELAY
            self.thread_states[0x53][0], # WAIT_MUTEX
            self.thread_states[0x63][0], # WAIT_SEMAPHORE
            self.thread_states[0x83][0], # WAIT_MESSAGE_GET
            self.thread_states[0x93][0], # WAIT_MESSAGE_PUT
            self.thread_states[0x43][0], # WAIT_EVENT_FLAGS
            self.thread_states[0x33][0], # WAIT_THREAD_FLAGS
            self.thread_states[0x23][0], # WAIT_JOIN
            self.thread_states[0x03][0], # BLOCKED (generic)
            self.thread_states[0x00][0], # INACTIVE
            self.thread_states[0x04][0], # TERMINATED
        ]
        state_order = [s for s in state_order_keys if s in threads_by_state]


        # Print threads, ordered by state
        for state_key in state_order:
            if state_key in threads_by_state: # Ensure the state actually has threads
                gdb.write(f"{Colors.CYAN}{state_key}:{Colors.RESET}\n")
                headers = ["Address", "ID", "Name", "State", "Prio", "SP", "Stack (Base/Size)", "Entry"]
                # Calculate column widths dynamically for better alignment
                col_widths = [
                    max(len(headers[0]), max(len(t["address"]) for t in threads_by_state[state_key])),
                    max(len(headers[1]), max(len(str(t["id"])) for t in threads_by_state[state_key])),
                    max(len(headers[2]), max(len(t["name"]) for t in threads_by_state[state_key])),
                    max(len(headers[3]), len(state_key)), # Use state_key length for state column
                    max(len(headers[4]), max(len(t["prio_str"]) for t in threads_by_state[state_key])),
                    max(len(headers[5]), max(len(t["sp"]) for t in threads_by_state[state_key])),
                    max(len(headers[6]), max(len(f"0x{t['stack_base']:x}/{t['stack_size']}") if isinstance(t['stack_base'], int) else f"{t['stack_base']}/{t['stack_size']}" for t in threads_by_state[state_key])), # Use formatted string for width calc, handle N/A
                    max(len(headers[7]), max(len(t["entry"]) for t in threads_by_state[state_key]))
                ]
                UI.table_header(headers)
                for t in threads_by_state[state_key]:
                    stack_base_str = f"0x{t['stack_base']:x}" if isinstance(t['stack_base'], int) else str(t['stack_base'])
                    UI.table_row([
                        t["address"],
                        str(t["id"]),
                        t["name"],
                        t["state"],
                        t["prio_str"],
                        t["sp"],
                        f"{stack_base_str}/{t['stack_size']}", # Corrected stack base format
                        t["entry"]
                    ], col_widths)
                gdb.write("\n")
        UI.section_footer()

    def _format_thread_data(self, t):
        """Helper to extract and format thread data."""
        thread_name = _cstr(t['name']) or "(unnamed)"
        stack_mem = "N/A"
        stack_size = "N/A"
        try:
            stack_mem = int(t['stack_mem']) if int(t['stack_mem']) != 0 else 0
            stack_size = int(t['stack_size'])
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error accessing stack info for thread at 0x{int(t.address):x}: {e}. Setting to N/A.{Colors.RESET}\n")

        entry = int(t['thread_addr'])
        sp = int(t['sp'])
        state_raw = int(t['state'])
        prio = int(t['priority'])
        tid = int(t['id'])

        # Get human-readable names
        state_str, _ = self.thread_states.get(state_raw, (f"UNKNOWN({state_raw})", Colors.RED))
        prio_str = self._get_enum_name(self.thread_priorities, prio)

        return {
            "id": f"0x{tid:x}", # FORMAT ID AS HEX
            "name": thread_name,
            "state": state_str,
            "prio": prio,
            "prio_str": prio_str,
            "sp": f"0x{sp:x}",
            "stack_base": stack_mem, # Keep as int for f-string formatting in table row
            "stack_size": stack_size,
            "entry": _symbol_at(entry, max_len=30), # Apply truncation for table display
            "address": f"0x{int(t.address):x}"
        }


    def show_timers(self):
        """Display timer information."""
        UI.section("Timers")

        timer_list_head = self.info["timer"]["list"]

        timers = []
        seen_timer_addresses = set()

        # Try to iterate through the linked list
        try:
            for t in self._iterate_timers(timer_list_head, "next"):
                timer_address = int(t.address)
                if timer_address not in seen_timer_addresses:
                    seen_timer_addresses.add(timer_address)
                    timers.append(t)
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error iterating timer list: {e}. Attempting to read from memory sections.{Colors.RESET}\n")
            # Fallback: Try to read from memory sections if iteration fails
            try:
                # os_cb_sections is an array of pointers
                cb_sections_array = gdb.parse_and_eval("os_cb_sections")
                # Timer is at indices 2,3
                timer_cb_start = int(cb_sections_array[2].dereference())
                timer_cb_end = int(cb_sections_array[3].dereference())

                # Add a more robust check for plausible memory ranges
                MAX_PLAUSIBLE_CB_SECTION_SIZE = 16 * 1024 * 1024 # 16 MB
                MIN_PLAUSIBLE_START_ADDR = 0x8000 # Avoid very low addresses that might be vectors/registers
                MAX_PLAUSIBLE_END_ADDR = 0x80000000 # A heuristic for typical 32-bit RAM upper bound

                if (timer_cb_start != 0 and timer_cb_end != 0 and
                        timer_cb_end > timer_cb_start and
                        (timer_cb_end - timer_cb_start) < MAX_PLAUSIBLE_CB_SECTION_SIZE and
                        timer_cb_start >= MIN_PLAUSIBLE_START_ADDR and
                        timer_cb_end < MAX_PLAUSIBLE_END_ADDR):

                    timer_type_gdb = gdb.lookup_type("osRtxTimer_t")
                    timer_size = timer_type_gdb.sizeof

                    current_addr = timer_cb_start
                    while current_addr < timer_cb_end:
                        try:
                            t_ptr = gdb.Value(current_addr).cast(timer_type_gdb.pointer())
                            t = t_ptr.dereference()
                            if int(t['id']) == self.RTX_OBJ_ID_TIMER: # Check for valid timer object ID
                                timer_address = int(t.address)
                                if timer_address not in seen_timer_addresses:
                                    seen_timer_addresses.add(timer_address)
                                    timers.append(t)
                            current_addr += timer_size
                        except gdb.error as e:
                            gdb.write(f"{Colors.YELLOW}Warning: Error reading timer CB at 0x{current_addr:x}: {e}. Skipping.{Colors.RESET}\n")
                            current_addr += timer_size
                else:
                    gdb.write(f"{Colors.YELLOW}Info: os_cb_sections for timers is empty, invalid range (0x{timer_cb_start:x}-0x{timer_cb_end:x}), or implausible. Falling back to linked lists.{Colors.RESET}\n")
            except gdb.error as e:
                gdb.write(f"{Colors.RED}Error: Failed to retrieve timer data from both linked list and memory sections: {e}{Colors.RESET}\n")


        if not timers:
            gdb.write("  (none)\n")
            UI.section_footer()
            return

        # Prepare data for table
        formatted_timer_rows = []
        for t in timers:
            formatted_timer_rows.append(self._format_timer_row(t))

        headers = ["ID", "Name", "State", "Type", "Period", "Remaining", "Callback", "Argument"]
        col_widths = [len(h) for h in headers]
        for row_data in formatted_timer_rows:
            for i, item in enumerate(row_data):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(item)))

        # Print header
        header_line = ""
        for i, h in enumerate(headers):
            header_line += f"{h:<{col_widths[i]}} "
            if i < len(headers) - 1:
                header_line += "| "
        gdb.write("\n" + _color(header_line, Colors.BOLD))
        gdb.write("\n" + "-" * (sum(col_widths) + len(headers) * 3 - 3)) # Adjust for separators

        # Print rows
        for row in formatted_timer_rows:
            row_str = ""
            for i, item in enumerate(row):
                row_str += f"{item:<{col_widths[i]}} "
                if i < len(row) - 1:
                    row_str += "| "
            gdb.write("\n" + row_str)
        gdb.write("\n")
        UI.section_footer()


    def _format_timer_row(self, t):
        """Helper to extract and format timer data into a list for table row."""
        tid = int(t['id'])
        name = _cstr(t['name']) or "(unnamed)"
        state_raw = int(t['state'])
        state_str, state_color = self.timer_states.get(state_raw, (f"UNKNOWN({state_raw})", Colors.RED))

        timer_type_raw = 0 # Default value
        try:
            # Access 'type' member directly
            if 'type' in t.type.fields():
                timer_type_raw = int(t['type'])
            else:
                gdb.write(f"{Colors.YELLOW}Warning: 'type' member not found in timer at 0x{int(t.address):x}. Defaulting type to One-shot.{Colors.RESET}\n")
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error reading timer type from timer at 0x{int(t.address):x}: {e}. Defaulting type to One-shot.{Colors.RESET}\n")

        type_str = self.timer_types.get(timer_type_raw, "Unknown")
        load = int(t['load'])
        tick = int(t['tick'])

        # Access finfo.func and finfo.arg directly
        cb = "N/A"
        arg = "N/A"
        try:
            if 'finfo' in t.type.fields():
                finfo_struct = t['finfo']
                if 'func' in finfo_struct.type.fields():
                    cb = _symbol_at(finfo_struct['func'], max_len=30)
                else:
                    gdb.write(f"{Colors.YELLOW}Warning: 'func' member not found in finfo for timer at 0x{int(t.address):x}.{Colors.RESET}\n")
                if 'arg' in finfo_struct.type.fields():
                    arg = f"0x{int(finfo_struct['arg']):x}"
                else:
                    gdb.write(f"{Colors.YELLOW}Warning: 'arg' member not found in finfo for timer at 0x{int(t.address):x}.{Colors.RESET}\n")
            else:
                gdb.write(f"{Colors.YELLOW}Warning: 'finfo' member not found for timer at 0x{int(t.address):x}.{Colors.RESET}\n")
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error accessing finfo for timer at 0x{int(t.address):x}: {e}.{Colors.RESET}\n")


        # Calculate remaining time
        remaining = "N/A"
        if state_raw == self.timer_states[0x02][0]:  # RUNNING
            try:
                kernel_tick = int(self.info['kernel']['tick'])
                if tick > kernel_tick:
                    remaining = str(tick - kernel_tick) + "ms"
                else:
                    remaining = "0ms" # Timer already expired or very close
            except gdb.error:
                pass # remaining stays "N/A"

        # Apply color for state
        state_display = _color(state_str, state_color) if UI_ENABLED else state_str

        return [
            str(tid),
            name,
            state_display,
            type_str,
            f"{load}ms",
            remaining,
            cb,
            arg
        ]

    def show_mutexes(self):
        """Display mutex information."""
        self._show_object_pool("Mutexes", "mutex", "osRtxMutex_t", self._format_mutex_row, self.RTX_OBJ_ID_MUTEX)

    def _format_mutex_row(self, ptr, obj):
        """Format single mutex into a list for table row."""
        mid = int(obj['id'])
        name = _cstr(obj['name']) or "(unnamed)"

        # Attributes
        attr = int(obj['attr'])
        attrs = []
        for bit, attr_name in self.mutex_attr.items():
            if attr & bit:
                attrs.append(attr_name)
        attr_str = ", ".join(attrs) if attrs else "None"

        # Owner and lock count
        owner = obj['owner_thread']
        lock_count = int(obj['lock'])

        owner_str = "--FREE--"
        if int(owner):
            try:
                owner_name = _cstr(owner.dereference()['name']) or "(unnamed)"
                owner_str = f"{owner_name}"
            except gdb.error:
                owner_str = f"0x{int(owner):x} (Error)"

        # Waiting threads count
        waiting_threads_count = self._get_waiting_threads_count(obj)
        waiting_str = str(waiting_threads_count)

        if UI_ENABLED:
            owner_display = _color(owner_str, Colors.GREEN if int(owner) else Colors.DIM)
        else:
            owner_display = owner_str

        return [
            str(mid),
            name,
            str(lock_count),
            owner_display,
            attr_str,
            waiting_str
        ]

    def show_semaphores(self):
        """Display semaphore information."""
        self._show_object_pool("Semaphores", "semaphore", "osRtxSemaphore_t", self._format_semaphore_row, self.RTX_OBJ_ID_SEMAPHORE)

    def _format_semaphore_row(self, ptr, obj):
        """Format single semaphore into a list for table row."""
        sid = int(obj['id'])
        name = _cstr(obj['name']) or "(unnamed)"
        tokens = int(obj['tokens'])
        max_tokens = int(obj['max_tokens'])

        # Check if binary semaphore
        sem_type = "Binary" if max_tokens == 1 else "Counting"

        # Waiting threads count
        waiting_threads_count = self._get_waiting_threads_count(obj)
        waiting_str = str(waiting_threads_count)

        # Token visualization
        token_display = f"{tokens}/{max_tokens}"
        if UI_ENABLED:
            if tokens == 0:
                token_color = Colors.RED
            elif tokens < max_tokens:
                token_color = Colors.YELLOW
            else:
                token_color = Colors.GREEN
            token_display = _color(token_display, token_color)

        return [
            str(sid),
            name,
            token_display,
            sem_type,
            waiting_str
        ]

    def show_event_flags(self):
        """Display event flags information."""
        self._show_object_pool("Event Flags", "event_flags", "osRtxEventFlags_t", self._format_event_flags_row, self.RTX_OBJ_ID_EVENTFLAGS)

    def _format_event_flags_row(self, ptr, obj):
        """Format single event flags object into a list for table row."""
        eid = int(obj['id'])
        name = _cstr(obj['name']) or "(unnamed)"
        flags = int(obj['event_flags'])

        # Format flags
        flags_str = f"0x{flags:08x}"
        if flags:
            set_bits = []
            for i in range(32):
                if flags & (1 << i):
                    set_bits.append(str(i))
            if len(set_bits) <= 4 and set_bits:
                flags_str += f" (bits: {','.join(set_bits)})"

        # Waiting threads count
        waiting_threads_count = self._get_waiting_threads_count(obj)
        waiting_str = str(waiting_threads_count)

        return [
            str(eid),
            name,
            flags_str,
            waiting_str
        ]

    def show_memory_pools(self):
        """Display memory pool information."""
        self._show_object_pool("Memory Pools", "memory_pool", "osRtxMemoryPool_t", self._format_memory_pool_row, self.RTX_OBJ_ID_MEMORYPOOL)

    def _format_memory_pool_row(self, ptr, obj):
        """Format single memory pool into a list for table row."""
        mid = int(obj['id'])
        name = _cstr(obj['name']) or "(unnamed)"

        block_size = "N/A"
        max_blocks = "N/A"
        used_blocks = "N/A"
        base = "N/A"
        lim = "N/A"

        try:
            # Access directly from osRtxMemoryPool_t
            if 'block_size' in obj.type.fields(): block_size = int(obj['block_size'])
            if 'max_blocks' in obj.type.fields(): max_blocks = int(obj['max_blocks'])
            if 'used_blocks' in obj.type.fields(): used_blocks = int(obj['used_blocks'])
            if 'block_base' in obj.type.fields(): base = int(obj["block_base"])
            if 'block_lim' in obj.type.fields(): lim = int(obj["block_lim"])
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error accessing memory pool info at 0x{int(obj.address):x} ({e}). Some fields may be N/A.{Colors.RESET}\n")

        # Usage visualization
        usage_display = f"{used_blocks}/{max_blocks}"
        if UI_ENABLED and isinstance(used_blocks, int) and isinstance(max_blocks, int) and max_blocks > 0:
            percent = (used_blocks * 100) // max_blocks
            if percent > 80:
                usage_display = _color(usage_display, Colors.RED)
            elif percent > 50:
                usage_display = _color(usage_display, Colors.YELLOW)
            else:
                usage_display = _color(usage_display, Colors.GREEN)

        # Handle formatting for base address and memory size, allowing for "N/A"
        base_str = f"0x{base:x}" if isinstance(base, int) else str(base)
        mem_size_str = f"{lim - base}B" if isinstance(lim, int) and isinstance(base, int) else "N/A"

        return [
            str(mid),
            name,
            usage_display,
            f"{block_size}B",
            base_str,
            mem_size_str
        ]

    def show_message_queues(self):
        """Display message queue information."""
        self._show_object_pool("Message Queues", "message_queue", "osRtxMessageQueue_t", self._format_message_queue_row, self.RTX_OBJ_ID_MESSAGEQUEUE)

    def _format_message_queue_row(self, ptr, obj):
        """Format single message queue into a list for table row."""
        qid = int(obj['id'])
        name = _cstr(obj['name']) or "(unnamed)"
        msg_count = "N/A"
        max_msgs = "N/A"
        msg_size = "N/A"

        try:
            # Access directly from osRtxMessageQueue_t
            if 'msg_count' in obj.type.fields(): msg_count = int(obj['msg_count'])
            if 'max_msgs' in obj.type.fields(): max_msgs = int(obj['max_msgs'])
            if 'msg_size' in obj.type.fields(): msg_size = int(obj['msg_size'])
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error accessing message queue info at 0x{int(obj.address):x} ({e}). Some fields may be N/A.{Colors.RESET}\n")


        # Messages visualization
        msg_display = f"{msg_count}/{max_msgs}"
        if UI_ENABLED and isinstance(msg_count, int) and isinstance(max_msgs, int) and max_msgs > 0:
            if msg_count == 0:
                msg_color = Colors.DIM
            elif msg_count == max_msgs:
                msg_color = Colors.RED
            else:
                msg_color = Colors.GREEN
            msg_display = _color(msg_display, msg_color)

        # Waiting threads count
        waiting_threads_count = self._get_waiting_threads_count(obj)
        waiting_str = str(waiting_threads_count)

        return [
            str(qid),
            name,
            msg_display,
            f"{msg_size}B",
            waiting_str
        ]

    def show_object_usage_counters(self):
        """Display memory pool usage statistics (renamed from show_memory_usage)."""
        UI.section("Object Memory Usage Counters")

        # Object usage table header
        headers = ["Object Type", "Alloc", "Free", "Max Used"]
        col_widths = [len(h) for h in headers]

        usage_vars = [
            ("Thread", "osRtxThreadMemUsage"),
            ("Timer", "osRtxTimerMemUsage"),
            ("EventFlags", "osRtxEventFlagsMemUsage"),
            ("Mutex", "osRtxMutexMemUsage"),
            ("Semaphore", "osRtxSemaphoreMemUsage"),
            ("MemoryPool", "osRtxMemoryPoolMemUsage"),
            ("MessageQueue", "osRtxMessageQueueMemUsage"),
        ]

        rows_data = []
        for label, sym in usage_vars:
            try:
                val = gdb.parse_and_eval(sym)
                alloc = int(val['cnt_alloc'])
                free = int(val['cnt_free'])
                max_used = int(val['max_used'])
                rows_data.append([label, str(alloc), str(free), str(max_used)])
            except gdb.error:
                rows_data.append([label, "N/A", "N/A", "N/A"])

        for row_data in rows_data:
            for i, item in enumerate(row_data):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(item)))

        UI.table_header(headers)
        for row in rows_data:
            UI.table_row(row, col_widths)
        gdb.write("\n")
        UI.section_footer()

    def show_post_init_config(self):
        """Display post-initialization configuration details."""
        UI.section("Post-Init Configuration")

        # Robin Timeout
        gdb.write(f"  Robin Timeout: {int(self.config['robin_timeout'])} ticks")
        if int(self.config['tick_freq']) > 0:
            gdb.write(f" ({int(self.config['robin_timeout'] * 1000 / self.config['tick_freq'])}ms)\n")
        else:
            gdb.write(" (N/A ms)\n")

        # Tick Handler
        tick_handler_sym = "N/A"
        try:
            if 'timer' in self.info.type.fields() and 'tick' in self.info['timer'].type.fields():
                tick_handler_sym = _symbol_at(int(self.info['timer']['tick']))
            else:
                gdb.write(f"{Colors.YELLOW}Warning: Timer tick handler info not found in osRtxInfo.timer.tick.{Colors.RESET}\n")
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error accessing timer tick handler: {e}.{Colors.RESET}\n")
        gdb.write(f"  Tick Handler: {tick_handler_sym}\n")

        # Error Handler
        error_handler_sym = "N/A"
        try:
            error_handler_sym = _symbol_at(int(gdb.parse_and_eval("osRtxErrorNotify")))
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error handler symbol osRtxErrorNotify not found: {e}.{Colors.RESET}\n")
        gdb.write(f"  Error Handler: {error_handler_sym}\n")

        # Idle Handler
        idle_handler_sym = "N/A"
        try:
            if 'idle' in self.info['thread'].type.fields():
                idle_thread_ptr = self.info['thread']['idle']
                if int(idle_thread_ptr) != 0:
                    idle_handler_sym = _symbol_at(int(idle_thread_ptr.dereference()['thread_addr']))
            else:
                gdb.write(f"{Colors.YELLOW}Warning: Idle thread info not found in osRtxInfo.thread.idle.{Colors.RESET}\n")
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error accessing idle handler: {e}.{Colors.RESET}\n")
        gdb.write(f"  Idle Handler: {idle_handler_sym}\n")
        gdb.write("\n")
        UI.section_footer()

    # New function to show detailed memory pool statistics (for internal RTX objects)
    def show_memory_pool_statistics(self):
        """Display detailed memory pool statistics for internal RTX objects."""
        UI.section("Memory Pool Statistics")

        # Define the internal memory pools to display
        # These correspond to the 'mpi' members in osRtxConfig_t
        internal_mp_info = [
            ("Thread", "thread"),
            ("Timer", "timer"),
            ("EventFlags", "event_flags"),
            ("Mutex", "mutex"),
            ("Semaphore", "semaphore"),
            ("MemoryPool", "memory_pool"), # This is for osMemoryPool objects themselves
            ("MessageQueue", "message_queue"), # This is for osMessageQueue objects themselves
        ]

        headers = ["Object Type", "Size", "Used/Max", "Limit", "Peak", "Failed Allocs"]
        rows_data = []

        for label, field_name in internal_mp_info:
            try:
                mp_info_ptr = self.config['mpi'][field_name]
                if int(mp_info_ptr) != 0:
                    mp_info = mp_info_ptr.dereference()
                    block_size = int(mp_info['block_size'])
                    max_blocks = int(mp_info['max_blocks'])
                    used_blocks = int(mp_info['used_blocks'])
                    peak_used = int(mp_info['peak_used'])
                    failed_allocs = int(mp_info['failed_allocs'])

                    rows_data.append([
                        label,
                        f"{block_size}B",
                        f"{used_blocks}/{max_blocks}",
                        str(max_blocks),
                        str(peak_used),
                        str(failed_allocs)
                    ])
                else:
                    rows_data.append([label, "N/A", "N/A", "N/A", "N/A", "N/A"])
            except gdb.error as e:
                rows_data.append([label, "N/A", "N/A", "N/A", "N/A", "N/A"])
                gdb.write(f"{Colors.YELLOW}Warning: Could not read internal memory pool '{label}': {e}{Colors.RESET}\n")


        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row_data in rows_data:
            for i, item in enumerate(row_data):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(item)))

        UI.table_header(headers)
        for row in rows_data:
            UI.table_row(row, col_widths)
        gdb.write("\n")
        UI.section_footer()


    # ------------------------------------------------------------------
    # Helpers for object enumeration and formatting
    # ------------------------------------------------------------------
    def _iterate_global_heap_objects(self, expected_obj_id, obj_type_gdb):
        """
        Iterates through the global dynamic memory (os_mem) to find RTX objects.
        This is used when objects are allocated from the main heap, not dedicated MPI pools.
        """
        objects = []
        try:
            os_mem_val = gdb.parse_and_eval("os_mem")
            mem_head_type = gdb.lookup_type("mem_head_t")
            mem_head_size = mem_head_type.sizeof

            # The first block starts after mem_head_t
            current_block_addr = int(os_mem_val.address) + mem_head_size

            mem_block_type = gdb.lookup_type("mem_block_t")
            mem_block_size = mem_block_type.sizeof

            # Use osRtxObject_t for generic object type
            os_object_type = gdb.lookup_type("osRtxObject_t").pointer() # Generic object type

            # Iterate through the linked list of memory blocks
            current_mem_block_ptr = gdb.Value(current_block_addr).cast(mem_block_type.pointer())

            # The list ends when next is NULL or we detect a loop
            visited_blocks = set()

            while int(current_mem_block_ptr) != 0 and int(current_mem_block_ptr) not in visited_blocks:
                visited_blocks.add(int(current_mem_block_ptr))
                try:
                    mem_block = current_mem_block_ptr.dereference()

                    # The actual RTX object starts immediately after the mem_block_t header
                    obj_addr = int(current_mem_block_ptr) + mem_block_size

                    # Cast to generic osRtxObject_t* to read the ID
                    generic_obj_ptr = gdb.Value(obj_addr).cast(os_object_type)
                    generic_obj = generic_obj_ptr.dereference()

                    # Check if the ID matches the expected object ID
                    if int(generic_obj['id']) == expected_obj_id:
                        # If ID matches, cast to the specific object type and add to list
                        specific_obj_ptr = gdb.Value(obj_addr).cast(obj_type_gdb)
                        objects.append((specific_obj_ptr, specific_obj_ptr.dereference()))

                    current_mem_block_ptr = mem_block['next']
                except gdb.error as e:
                    gdb.write(f"{Colors.YELLOW}Warning: Error traversing global heap at 0x{int(current_mem_block_ptr):x}: {e}. Stopping iteration.{Colors.RESET}\n")
                    break
        except gdb.error as e:
            gdb.write(f"{Colors.RED}Error: Failed to iterate global heap: {e}{Colors.RESET}\n")
        return objects


    def _show_object_pool(self, title, field_name_in_mpi, type_name, format_func, expected_obj_id):
        """
        Generic function to show object pool contents.
        Attempts to read from os_cb_sections first, then falls back to MPI,
        and finally iterates global heap if objects are dynamically allocated from there.
        """
        UI.section(title)

        objects_found = []
        obj_type_gdb = None
        try:
            obj_type_gdb = gdb.lookup_type(type_name).pointer()
        except gdb.error:
            gdb.write(_color(f"\nType '{type_name}' not found. Skipping {title}.\n", Colors.RED))
            UI.section_footer()
            return


        # Check OS_OBJ_MEM configuration for this specific object type
        # This is crucial to decide where to look for the control blocks
        obj_mem_enabled = False
        try:
            # Use gdb.lookup_symbol to check for macro existence more gracefully
            macro_symbol_name = f"OS_{field_name_in_mpi.upper()}_OBJ_MEM"
            # Check if the symbol exists and its value is 1
            sym_and_block = gdb.lookup_symbol(macro_symbol_name)
            if sym_and_block[0] and int(gdb.parse_and_eval(macro_symbol_name)) == 1:
                obj_mem_enabled = True
            else:
                obj_mem_enabled = False
        except gdb.error:
            obj_mem_enabled = False # Default to false if symbol not found or error


        # 1. Attempt to read from os_cb_sections (static allocations)
        sections_read_successfully = False
        try:
            cb_sections_array = gdb.parse_and_eval("os_cb_sections")
            start_addr = 0
            end_addr = 0

            # Determine the correct start/end addresses based on type_name
            # Array indices from rtx_lib.c:
            # 0,1: thread, 2,3: timer, 4,5: evflags, 6,7: mutex,
            # 8,9: semaphore, 10,11: mempool, 12,13: msgqueue
            if type_name == "osRtxThread_t":
                start_addr = int(cb_sections_array[0].dereference())
                end_addr = int(cb_sections_array[1].dereference())
            elif type_name == "osRtxTimer_t":
                start_addr = int(cb_sections_array[2].dereference())
                end_addr = int(cb_sections_array[3].dereference())
            elif type_name == "osRtxEventFlags_t":
                start_addr = int(cb_sections_array[4].dereference())
                end_addr = int(cb_sections_array[5].dereference())
            elif type_name == "osRtxMutex_t":
                start_addr = int(cb_sections_array[6].dereference())
                end_addr = int(cb_sections_array[7].dereference())
            elif type_name == "osRtxSemaphore_t":
                start_addr = int(cb_sections_array[8].dereference())
                end_addr = int(cb_sections_array[9].dereference())
            elif type_name == "osRtxMemoryPool_t":
                start_addr = int(cb_sections_array[10].dereference())
                end_addr = int(cb_sections_array[11].dereference())
            elif type_name == "osRtxMessageQueue_t":
                start_addr = int(cb_sections_array[12].dereference())
                end_addr = int(cb_sections_array[13].dereference())

            # Add a more robust check for plausible memory ranges
            MAX_PLAUSIBLE_CB_SECTION_SIZE = 16 * 1024 * 1024 # 16 MB
            MIN_PLAUSIBLE_START_ADDR = 0x8000 # Avoid very low addresses that might be vectors/registers
            MAX_PLAUSIBLE_END_ADDR = 0x80000000 # A heuristic for typical 32-bit RAM upper bound

            if (start_addr != 0 and end_addr != 0 and
                    end_addr > start_addr and
                    (end_addr - start_addr) < MAX_PLAUSIBLE_CB_SECTION_SIZE and
                    start_addr >= MIN_PLAUSIBLE_START_ADDR and
                    end_addr < MAX_PLAUSIBLE_END_ADDR):

                current_addr = start_addr
                obj_size = obj_type_gdb.target().sizeof
                while current_addr < end_addr:
                    try:
                        obj_ptr = gdb.Value(current_addr).cast(obj_type_gdb)
                        obj = obj_ptr.dereference()
                        if int(obj['id']) == expected_obj_id:
                            objects_found.append((obj_ptr, obj))
                        current_addr += obj_size
                    except gdb.error as e:
                        gdb.write(f"{Colors.YELLOW}Warning: Error reading {title} CB at 0x{current_addr:x} from sections: {e}. Skipping.{Colors.RESET}\n")
                        current_addr += obj_size
                if objects_found:
                    sections_read_successfully = True
            else:
                gdb.write(f"{Colors.YELLOW}Info: os_cb_sections for {title} is empty, invalid range (0x{start_addr:x}-0x{end_addr:x}), or implausible. Trying other allocation methods.{Colors.RESET}\n")
        except gdb.error:
            gdb.write(f"{Colors.YELLOW}Warning: Could not access 'os_cb_sections' for {title}. This is expected if objects are not statically allocated or if the symbol is not available. Trying other allocation methods.{Colors.RESET}\n")
            pass

        # 2. Try dedicated MPI pool (if OS_XXX_OBJ_MEM is enabled and sections didn't yield results)
        if not objects_found and obj_mem_enabled:
            try:
                ptr_mpi = self.config['mpi'][field_name_in_mpi]
                if ptr_mpi and int(ptr_mpi) != 0:
                    mp = ptr_mpi.dereference()
                    base = int(mp["block_base"])
                    count = int(mp["max_blocks"])
                    size = int(mp["block_size"])
                    used = int(mp["used_blocks"])

                    gdb.write(f"\nBlocks from dedicated MPI pool: {used}/{count} (block size: {size} bytes)\n")

                    for i in range(count):
                        obj_ptr = gdb.Value(base + i * size).cast(obj_type_gdb)
                        obj = obj_ptr.dereference()
                        if int(obj["id"]) == expected_obj_id:
                            objects_found.append((obj_ptr, obj))
                else:
                    gdb.write(_color(f"\nNo dedicated MPI pool initialized or found for {title.lower()} (ptr_mpi is NULL).{Colors.RESET}\n", Colors.YELLOW))
            except gdb.error as e:
                gdb.write(_color(f"\nError: Could not access dedicated MPI pool for {title} (member '{field_name_in_mpi}' not found or other GDB error): {e}\n", Colors.RED))

        # 3. Fallback to global heap iteration (if OS_XXX_OBJ_MEM is disabled or other methods failed)
        if not objects_found and not obj_mem_enabled:
            gdb.write(f"\nAttempting to find {title.lower()} objects in global dynamic memory (heap).\n")
            objects_found.extend(self._iterate_global_heap_objects(expected_obj_id, obj_type_gdb))

        if not objects_found:
            gdb.write(_color(f"\nNo active {title.lower()}s found.\n", Colors.YELLOW))
            UI.section_footer()
            return

        # Prepare headers based on the object type
        headers = []
        if field_name_in_mpi == "mutex":
            headers = ["ID", "Name", "Lock", "Owner", "Attributes", "Waiting Threads"]
        elif field_name_in_mpi == "semaphore":
            headers = ["ID", "Name", "Tokens (Cur/Max)", "Type", "Waiting Threads"]
        elif field_name_in_mpi == "event_flags":
            headers = ["ID", "Name", "Flags", "Waiting Threads"]
        elif field_name_in_mpi == "memory_pool":
            headers = ["ID", "Name", "Used/Max Blocks", "Block Size", "Memory Base", "Memory Size"]
        elif field_name_in_mpi == "message_queue":
            headers = ["ID", "Name", "Messages (Cur/Max)", "Msg Size", "Waiting Threads"]
        else:
            headers = ["ID", "Name", "Address", "Info"] # Generic fallback

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        formatted_rows_data = []
        for obj_ptr, obj in objects_found:
            row_data = format_func(obj_ptr, obj) # Call format_func to get the list of strings
            formatted_rows_data.append(row_data)
            for i, item in enumerate(row_data):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(item)))

        # Print header
        header_line = ""
        for i, h in enumerate(headers):
            header_line += f"{h:<{col_widths[i]}} "
            if i < len(headers) - 1:
                header_line += "| "
        gdb.write("\n" + _color(header_line, Colors.BOLD))
        gdb.write("\n" + "-" * (sum(col_widths) + len(headers) * 3 - 3)) # Adjust for separators

        # Print rows
        for row in formatted_rows_data:
            row_str = ""
            for i, item in enumerate(row):
                row_str += f"{item:<{col_widths[i]}} "
                if i < len(row) - 1:
                    row_str += "| "
            gdb.write("\n" + row_str)
        gdb.write("\n")
        UI.section_footer()

    def _get_waiting_threads_count(self, obj):
        """Counts threads in the thread_list of an object."""
        try:
            # Check if 'thread_list' field exists before accessing
            if 'thread_list' not in obj.type.fields():
                return "N/A (No list)"

            thread_list_head = obj["thread_list"]
            if int(thread_list_head) == 0:
                return 0

            count = 0
            current = thread_list_head
            visited = set()
            # Limit iteration to prevent infinite loops on corrupted lists
            max_iterations = 1000 # Arbitrary large number to prevent infinite loop
            while int(current) != 0 and int(current) not in visited and count < max_iterations:
                visited.add(int(current))
                count += 1
                # Check if 'thread_next' field exists before accessing
                if 'thread_next' not in current.dereference().type.fields():
                    gdb.write(f"{Colors.YELLOW}Warning: 'thread_next' member not found in thread object at 0x{int(current):x} while counting waiting threads. Stopping count.{Colors.RESET}\n")
                    return f"{count} (Partial/Error)"
                current = current.dereference()["thread_next"]
            if count >= max_iterations:
                gdb.write(f"{Colors.YELLOW}Warning: Reached max iterations ({max_iterations}) while counting waiting threads for object at 0x{int(obj.address):x}. List might be corrupted or very long.{Colors.RESET}\n")
                return f"{count}+ (Possible Loop)"
            return count
        except gdb.error as e:
            gdb.write(f"{Colors.YELLOW}Warning: Error counting waiting threads for object at 0x{int(obj.address):x}: {e}.{Colors.RESET}\n")
            return "N/A (Error)"

    def _iterate_threads(self, head, next_field):
        """Helper generator function to iterate through a linked list of threads.
        WARNING: This iteration method can lead to GDB crashes if the linked list
        is corrupted or contains invalid pointers. Robust error handling is attempted
        but cannot guarantee full crash prevention in all corruption scenarios.
        """
        t = head
        visited = set()
        max_iterations = 1000 # Prevent infinite loops for corrupted lists
        current_iteration = 0
        while int(t) != 0 and int(t) not in visited and current_iteration < max_iterations:
            visited.add(int(t))
            try:
                thr = t.dereference()
                yield thr
                # Safely get the next pointer, handle potential errors
                if next_field not in thr.type.fields():
                    gdb.write(f"{Colors.YELLOW}Warning: '{next_field}' member not found in thread object at 0x{int(t):x}. Stopping iteration.{Colors.RESET}\n")
                    break
                next_ptr = thr[next_field]
                if int(next_ptr) == 0: # Explicitly check for NULL next pointer
                    break
                t = next_ptr
                current_iteration += 1
            except gdb.error as e:
                gdb.write(f"{Colors.YELLOW}Warning: Error traversing thread list at 0x{int(t):x} (field '{next_field}'): {e}. Stopping iteration.{Colors.RESET}\n")
                break # Stop iteration if a link is invalid or field missing
        if current_iteration >= max_iterations:
            gdb.write(f"{Colors.YELLOW}Warning: Reached max iterations ({max_iterations}) while iterating thread list starting at 0x{int(head):x}. List might be corrupted or very long.{Colors.RESET}\n")


    def _iterate_timers(self, head, next_field):
        """Helper generator function to iterate through a linked list of timers."""
        t = head
        visited = set()
        max_iterations = 1000 # Prevent infinite loops for corrupted lists
        current_iteration = 0
        while int(t) != 0 and int(t) not in visited and current_iteration < max_iterations:
            visited.add(int(t))
            try:
                timer = t.dereference()
                yield timer
                # Safely get the next pointer, handle potential errors
                if next_field not in timer.type.fields():
                    gdb.write(f"{Colors.YELLOW}Warning: '{next_field}' member not found in timer object at 0x{int(t):x}. Stopping iteration.{Colors.RESET}\n")
                    break
                next_ptr = timer[next_field]
                if int(next_ptr) == 0: # Explicitly check for NULL next pointer
                    break
                t = next_ptr
                current_iteration += 1
            except gdb.error as e:
                gdb.write(f"{Colors.YELLOW}Warning: Error traversing timer list at 0x{int(t):x} (field '{next_field}'): {e}. Stopping iteration.{Colors.RESET}\n")
                break
        if current_iteration >= max_iterations:
            gdb.write(f"{Colors.YELLOW}Warning: Reached max iterations ({max_iterations}) while iterating timer list starting at 0x{int(head):x}. List might be corrupted or very long.{Colors.RESET}\n")


    def show_all(self):
        """Show complete RTX5 RTOS state."""
        UI.header("RTX5 RTOS Complete Status")

        self.show_kernel_info()
        self.show_kernel_config()
        self.show_system_info() # This will contain Idle Thread, Timer Thread, System Handlers
        self.show_memory_pool_statistics() # New detailed memory pool stats
        self.show_object_usage_counters() # Renamed from show_memory_usage
        self.show_post_init_config() # New section for post-init config

        self.show_threads()
        self.show_timers()
        self.show_mutexes()
        self.show_semaphores()
        self.show_event_flags()
        self.show_memory_pools() # This is for user-defined memory pools (osMemoryPool)
        self.show_message_queues()

        gdb.write(f"\n\n{_color('Use individual rtx5-* commands for specific views', Colors.GRAY)}\n")


class Rtx5Command(gdb.Command):
    """Base class for RTX5 commands."""

    def __init__(self, name):
        super().__init__(name, gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        # Check UI support
        _check_ui_support()

        # Clear screen
        if UI_ENABLED:
            gdb.write("\033[2J\033[H")

        rtx = Rtx5Awareness()
        if rtx.load_symbols():
            self.handle(rtx)


class Rtx5AllCommand(Rtx5Command):
    """Display complete RTX5 state."""

    def __init__(self):
        super().__init__("rtx5-all")

    def handle(self, rtx):
        rtx.show_all()


class Rtx5KernelCommand(Rtx5Command):
    """Display kernel state and configuration."""

    def __init__(self):
        super().__init__("rtx5-kernel")

    def handle(self, rtx):
        UI.header("RTX5 Kernel Information")
        rtx.show_kernel_info()
        rtx.show_kernel_config()
        rtx.show_system_info()


class Rtx5ThreadsCommand(Rtx5Command):
    """Display thread information."""

    def __init__(self):
        super().__init__("rtx5-threads")

    def handle(self, rtx):
        UI.header("RTX5 Threads")
        rtx.show_threads()


class Rtx5TimersCommand(Rtx5Command):
    """Display timer information."""

    def __init__(self):
        super().__init__("rtx5-timers")

    def handle(self, rtx):
        UI.header("RTX5 Timers")
        rtx.show_timers()


class Rtx5MutexesCommand(Rtx5Command):
    """Display mutex information."""

    def __init__(self):
        super().__init__("rtx5-mutexes")

    def handle(self, rtx):
        UI.header("RTX5 Mutexes")
        rtx.show_mutexes()


class Rtx5SemaphoresCommand(Rtx5Command):
    """Display semaphore information."""

    def __init__(self):
        super().__init__("rtx5-semaphores")

    def handle(self, rtx):
        UI.header("RTX5 Semaphores")
        rtx.show_semaphores()


class Rtx5EventsCommand(Rtx5Command):
    """Display event flags information."""

    def __init__(self):
        super().__init__("rtx5-events")

    def handle(self, rtx):
        UI.header("RTX5 Event Flags")
        rtx.show_event_flags()


class Rtx5MemPoolsCommand(Rtx5Command):
    """Display memory pool information."""

    def __init__(self):
        super().__init__("rtx5-mempools")

    def handle(self, rtx):
        UI.header("RTX5 Memory Pools")
        rtx.show_memory_pools()


class Rtx5QueuesCommand(Rtx5Command):
    """Display message queue information."""

    def __init__(self):
        super().__init__("rtx5-queues")

    def handle(self, rtx):
        UI.header("RTX5 Message Queues")
        rtx.show_message_queues()


class Rtx5MemoryCommand(Rtx5Command):
    """Display memory usage statistics."""

    def __init__(self):
        super().__init__("rtx5-memory")

    def handle(self, rtx):
        UI.header("RTX5 Memory Usage")
        rtx.show_object_usage_counters()


# Register all commands
Rtx5AllCommand()
Rtx5KernelCommand()
Rtx5ThreadsCommand()
Rtx5TimersCommand()
Rtx5MutexesCommand()
Rtx5SemaphoresCommand()
Rtx5EventsCommand()
Rtx5MemPoolsCommand()
Rtx5QueuesCommand()
Rtx5MemoryCommand()

# Print welcome message
_check_ui_support()
if UI_ENABLED:
    gdb.write(f"{_color('✓ RTX5 Enhanced Awareness Loaded', Colors.BRIGHT_GREEN)}\n")
    gdb.write(f"{_color('Available commands:', Colors.CYAN)}\n")
    commands = [
        ('rtx5-all', 'Show complete RTOS state'),
        ('rtx5-kernel', 'Show kernel state & config'),
        ('rtx5-threads', 'List all threads'),
        ('rtx5-timers', 'List all timers'),
        ('rtx5-mutexes', 'List all mutexes'),
        ('rtx5-semaphores', 'List all semaphores'),
        ('rtx5-events', 'List all event flags'),
        ('rtx5-mempools', 'List memory pools'),
        ('rtx5-queues', 'List message queues'),
        ('rtx5-memory', 'Show memory statistics')
    ]
    for cmd, desc in commands:
        gdb.write(f"  • {_color(cmd, Colors.BRIGHT_YELLOW):<20} - {desc}\n")
else:
    gdb.write("RTX5 Enhanced Awareness Loaded\n")
    gdb.write("Available commands:\n")
    gdb.write("  rtx5-all        - Show complete RTOS state\n")
    gdb.write("  rtx5-kernel     - Show kernel state & config\n")
    gdb.write("  rtx5-threads    - List all threads\n")
    gdb.write("  rtx5-timers     - List all timers\n")
    gdb.write("  rtx5-mutexes    - List all mutexes\n")
    gdb.write("  rtx5-semaphores - List all semaphores\n")
    gdb.write("  rtx5-events     - List all event flags\n")
    gdb.write("  rtx5-mempools   - List memory pools\n")
    gdb.write("  rtx5-queues     - List message queues\n")
    gdb.write("  rtx5-memory     - Show memory statistics\n")

gdb.write("\n")
