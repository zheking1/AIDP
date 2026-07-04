import re
from typing import List

FORBIDDEN_COMMANDS = ["rm ", "dd ", "mkfs", "wget ", "curl ", "nc ", "netcat "]
DANGEROUS_CHARS = [";", "&&", "||", "|", "`", "$("]
DANGEROUS_IMPORTS = ["os.system", "subprocess.", "eval(", "exec("]


def validate_path(path: str) -> bool:
    if ".." in path:
        return False
    if path.startswith("/"):
        return False
    for ch in DANGEROUS_CHARS:
        if ch in path:
            return False
    return True


def validate_command(cmd: str) -> bool:
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden in cmd:
            return False
    for ch in DANGEROUS_CHARS:
        if ch in cmd:
            return False
    return True


def validate_code(code: str) -> bool:
    for imp in DANGEROUS_IMPORTS:
        if imp in code:
            return False
    return True


def sanitize_input(text: str) -> str:
    return re.sub(r'[<>"\';]', '', text)
