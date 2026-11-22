# assembler.py
# Hack assembler for Nand to Tetris I - Capstone Part B
# K = 47
#
# Usage:  python assembler.py Prog.asm
# Output: Prog.hack (one 16-bit binary instruction per line)
#
# Extra feature for K = 47 (K mod 3 = 2):
#   - a wrong line gives a clear message with its line number
#     (e.g. "Line 7: invalid instruction 'D=Q'") instead of a crash
#   - a warning is printed when the same label is defined twice

import os
import re
import sys

# ---------- tables ----------

COMP = {
    # a = 0
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101", "!A": "0110001",
    "-D": "0001111", "-A": "0110011", "D+1": "0011111", "A+1": "0110111",
    "D-1": "0001110", "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    # a = 1 (same operations with M instead of A)
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111",
    "M-1": "1110010", "D+M": "1000010", "D-M": "1010011", "M-D": "1000111",
    "D&M": "1000000", "D|M": "1010101",
}

# Commutative forms are also legal in the official assembler (A+D, M&D ...)
for _key in list(COMP):
    if len(_key) == 3 and _key[1] in "+&|" and _key[0].isalpha():
        COMP.setdefault(_key[2] + _key[1] + _key[0], COMP[_key])
COMP.setdefault("1+D", COMP["D+1"])
COMP.setdefault("1+A", COMP["A+1"])
COMP.setdefault("1+M", COMP["M+1"])

JUMP = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

PREDEFINED = {"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
              "SCREEN": 16384, "KBD": 24576}
for i in range(16):
    PREDEFINED["R" + str(i)] = i

SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


class AsmError(Exception):
    """a problem in one source line"""


# ---------- helpers ----------

def clean(line):
    """remove the comment and all white space from one line"""
    if "//" in line:
        line = line[:line.index("//")]
    return "".join(line.split())


def dest_bits(dest):
    """d1 d2 d3 = A D M; any order is accepted (MD, DM, AM, ADM ...)"""
    if dest and (set(dest) - set("ADM") or len(set(dest)) != len(dest)):
        raise AsmError("invalid destination '%s'" % dest)
    return "".join("1" if letter in dest else "0" for letter in "ADM")


def encode_a(value):
    return "0" + format(value, "015b")


def encode_c(line):
    dest, comp, jump = "", line, ""
    if "=" in comp:
        dest, comp = comp.split("=", 1)
    if ";" in comp:
        comp, jump = comp.split(";", 1)
    if comp not in COMP:
        raise AsmError("invalid instruction '%s'" % line)
    if jump not in JUMP:
        raise AsmError("invalid jump '%s'" % jump)
    return "111" + COMP[comp] + dest_bits(dest) + JUMP[jump]


# ---------- the two readings ----------

def first_reading(path):
    """drop comments / blank lines, record label addresses.
    returns (instructions, labels, ok); instructions = [(line_no, text)]"""
    instructions = []
    labels = {}
    ok = True
    with open(path) as f:
        for number, raw in enumerate(f, start=1):
            line = clean(raw)
            if line == "":
                continue
            if line.startswith("("):
                if not line.endswith(")") or not SYMBOL_RE.match(line[1:-1]):
                    print("Line %d: invalid label '%s'" % (number, line))
                    ok = False
                    continue
                name = line[1:-1]
                if name in labels:
                    print("Warning: line %d: label '%s' is already defined "
                          "(first at address %d); the new address %d is used"
                          % (number, name, labels[name], len(instructions)))
                labels[name] = len(instructions)
            else:
                instructions.append((number, line))
    return instructions, labels, ok


def second_reading(instructions, labels):
    """turn every instruction into 16 bits; collect the errors"""
    symbols = dict(PREDEFINED)
    symbols.update(labels)
    next_var = 16
    out, ok = [], True
    for number, line in instructions:
        try:
            if line[0] == "@":
                name = line[1:]
                if name == "":
                    raise AsmError("invalid instruction '@' (address missing)")
                if name.isdigit():
                    value = int(name)
                    if value > 32767:
                        raise AsmError("address %d does not fit in 15 bits" % value)
                elif SYMBOL_RE.match(name):
                    if name not in symbols:
                        symbols[name] = next_var
                        next_var += 1
                    value = symbols[name]
                else:
                    raise AsmError("invalid instruction '%s'" % line)
                out.append(encode_a(value))
            else:
                out.append(encode_c(line))
        except AsmError as err:
            print("Line %d: %s" % (number, err))
            ok = False
    return out, ok


def main():
    if len(sys.argv) < 2:
        print("usage: python assembler.py Prog.asm")
        return 1
    src = sys.argv[1]
    if not os.path.isfile(src):
        print("Error: file '%s' not found" % src)
        return 1

    instructions, labels, ok1 = first_reading(src)
    binary, ok2 = second_reading(instructions, labels)
    if not (ok1 and ok2):
        print("Assembly failed - no .hack file written.")
        return 1

    target = os.path.splitext(src)[0] + ".hack"
    with open(target, "w") as f:
        f.write("\n".join(binary) + "\n")
    print("%s -> %s  (%d instructions)" % (src, target, len(binary)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
