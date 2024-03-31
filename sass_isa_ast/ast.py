#!/usr/bin/env python

# SPDX-FileCopyrightText: 2020 - 2024 University of Rochester
#
# SPDX-License-Identifier: MIT

__author__ = "Benjamin Valpey"
__date__ = "Tue 05 Mar 2024 01:44:32 PM EST"
__license__ = "LGPL-3.0-or-later"
__copyright__ = "2020-2024 University of Rochester"

import re
import typing as _typ
from collections import defaultdict as _defaultdict

__all__ = [
    "Register",
    "CC_Register",
    "HexImmediate",
    "RegAddress",
    "ConstantAccess",
    "PredicateRegister",
    "BranchLabel",
    "Branch",
    "Instruction",
    "Statement",
    "Barrier",
    "UnaryOp",
    "FloatImmediate",
    "DecImmediate",
    "SReg",
    "NamedDependencyBarrier",
    "Simulator_function_name",
    "TextureDimensionOperand",
    "TextureComponentOperand",
    "argument_to_object",
]

from abc import ABC as _ABC, abstractmethod as _abstractmethod

# ruff: noqa: D107, D101, D105

_REGISTER_PATTERN = re.compile(r"((?<=\.)((?P<selector>H[01]|B[0-3]|64)|(?P<CC>CC)))(.reuse)?$")


class Reg(_ABC):
    """Abstract base class for a register or predicate register."""

    @property
    @_abstractmethod
    def v(self) -> str:
        """Return the string representation of the term."""
        pass

    @property
    @_abstractmethod
    def num(self) -> int:
        """Return the register or predicate register num.

        -1 should resolve to the constant register, RZ for Registers and PT for PredicateRegisters.
        """


class Register(Reg):
    """SASS Register, e.g. R1 R2 R3."""

    selector: str | None
    CC: bool | None

    def __init__(self, symbol: str, regType=None):
        """Initialize a Register object."""
        self._v = symbol.split(".")[0]

        matches = m.groupdict() if (m := _REGISTER_PATTERN.search(symbol)) is not None else {}
        self.selector = matches.get("selector")
        self.CC = bool(matches.get("CC"))
        self.reuse = bool(matches.get("reuse"))
        self._num = -1 if self._v == "RZ" else int(self._v[1:])

    @property
    def num(self):
        """Return the register number, or -1 if RZ."""
        return self._num

    @property
    def v(self) -> str | int:
        """Return the register value."""
        return self._v

    def __str__(self):
        """Return a string representation of the Register object."""
        return self.v

    def __eq__(self, other):
        return isinstance(other, Register) and (self.v, self.selector, self.CC) == (other.v, other.selector, other.CC)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.v, self.selector, self.CC))


class CC_Register:
    def __init__(self, symbol: str):
        self.condition: _typ.Optional[str]
        args = symbol.split(".")
        self.v = args[0]
        if len(args) > 1:
            self.condition = args[1]
        else:
            self.condition = None

    def __str__(self):
        return f'{self.v}{"." + self.condition if self.condition is not None else ""}'

    def __eq__(self, other):
        return isinstance(other, CC_Register)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.v)


class HexImmediate:
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text


class RegAddress():
    def __init__(self, text):
        self.offset: _typ.Optional[_typ.Union[HexImmediate, UnaryOp]]
        self.base: _typ.Union[Register, HexImmediate]
        noBracket = text.replace("[", "").replace("]", "")
        if "+" in noBracket:
            base = argument_to_object(noBracket[: noBracket.find("+")])
            offset = argument_to_object(noBracket[noBracket.find("+") + 1 :])
            assert isinstance(offset, HexImmediate) or (
                isinstance(offset, UnaryOp) and isinstance(offset.argument, HexImmediate)
            ), "offset of RegAddress must be a HexImmediate or UnaryOp on HexImmediate"
            self.offset = offset
        else:
            self.offset = None
            base = argument_to_object(noBracket)
        assert isinstance(base, Register) or isinstance(
            base, HexImmediate
        ), f"Base of RegAddress must be a Register or HexImmediate, have {type(base).__name__}"
        self.base = base
        self.text = text.replace("[", "").replace("]", "")

    def __str__(self):
        return self.text


class ConstantAccess():
    def __init__(self, bank: HexImmediate, offset: RegAddress, selector: str):
        self.bank: HexImmediate = bank
        self.offset: RegAddress = offset
        self.selector: str = selector


class PredicateRegister(Reg):
    def __init__(self, v):
        self.v: str = v
        self.type: str = "Bool"
        self._num = -1 if self.v == "PT" else int(self.v[1:])
    
    @property
    def num(self):
        """Return the register number, or -1 if PT."""
        return self._num
    
    @property
    def v(self) -> str:
        """Return the register value."""
        return self._v

    def __str__(self):
        return self.v

    def __eq__(self, other):
        return isinstance(other, PredicateRegister) and self.v == other.v

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.v)


class BranchLabel():
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class Branch():
    def __init__(self, text: str, dest: _typ.Union[str, HexImmediate]):
        self.dest: _typ.Union[str, HexImmediate] = dest
        self.text: str = text


class Instruction():
    def __init__(self, text: str):
        text = text.replace("] [", "][")
        if "@" in text:
            text = re.sub(r"@!?P[TN\d]\s", "", text)
        self.text: str = text
        self.arguments: list = []
        try:
            text = text.replace(", ", " ")
            text = re.sub(r"\s{2,}", " ", text)
            self.sass_instruction: str = text.replace(", ", " ").split()[0].replace(" ", "")
        except IndexError:
            print(text)
            raise
        for a in text.replace(", ", " ").split()[1:]:
            self.arguments.append(argument_to_object(a))
        # It may not be the best idea to parse here, but I want this logic to be attached to the class
        if ".CC" in text or self.text == "IMNMX.XHI":
            self.sass_instruction += "CC"

    def __str__(self):
        return self.text


class Statement():
    def __init__(self, label, text, instr: _typ.Optional[Instruction] = None):
        # remove any commas from different representations
        text = text.replace("] [", "][")
        self.label: str = label
        self.text = text
        # parse line into AST
        self.predicated: bool = "@" in text
        self.inverted: bool = "@!" in text
        try:
            self.predReg = (
                PredicateRegister(text.replace(", ", " ").split()[0][2 if self.inverted else 1 :]) if self.predicated else None
            )
        except:
            raise ValueError("Unable to parse: " + str(text))
        self.instruction: Instruction = Instruction(text) if instr is None else instr

    def __str__(self):
        return f"{self.label}: {self.text}"

    __repr__ = __str__


class Barrier:
    def __init__(self, text):
        self.text: str = text


class UnaryOp():
    """Unary operation on a term. !, ~, -, |, -|.

    ! = logical not
    ~ = bitwise not
    - = negation
    | = absolute value
    -| = negation of absolute value
    """

    def __init__(self, op: str, text: str):
        if op not in ["|", "-", "!", "~", "-|"]:
            raise ValueError
        self.operation: str = op
        self.argument = argument_to_object(text)
        self.h1: bool = "H1" in text

    def __str__(self):
        if self.operation == "|":
            return "|" + str(self.argument) + "|"
        elif self.operation == "-|":
            return "-|" + str(self.argument) + "|"
        else:
            return self.operation + str(self.argument)


class FloatImmediate(object):
    def __init__(self, v):
        self.v: str = "-" + v[:-4] if v.endswith(".NEG") else v
        self.negated: bool = v.endswith(".NEG")

    def __str__(self):
        return self.v


class DecImmediate(object):
    def __init__(self, v):
        self.v: str = v

    def __str__(self):
        return self.v


class SReg(object):
    def __init__(self, v):
        self.v: str = v

    def __str__(self):
        return self.v


class NamedDependencyBarrier(object):
    def __init__(self, v):
        self.v: str = v

    def __str__(self):
        return self.v


class Simulator_function_name(object):
    def __init__(self, v):
        self.v: str = v

    def __str__(self):
        return self.v


class TextureDimensionOperand(object):
    def __init__(self, v):
        self.v: str = v

    def __str__(self):
        return self.v


class TextureComponentOperand(object):
    def __init__(self, v):
        self.v: str = v

    def __str__(self):
        return self.v


def argument_to_object(
    arg: str,
):
    # get rid of .reuse.  It doesn't help us
    arg = arg.replace(".reuse", "")
    named_depbar_pattern = re.compile(r"^SB\d+")
    sreg_pattern = re.compile(r"^SR_\w+")
    address_pattern = re.compile(r"^\[(0x[0-9a-f]+|RZ|R\d+(\.64)?)(\+-?0x[0-9a-f]+|R\d+)?\]$")
    const_mem_pattern = re.compile(r"^c\[([^]]+)]\s*(\[[^]]+\])\.?(H1|B0|B1|B2|B3)?")
    float_pattern = re.compile(r"\d+\.NEG|\d+\.\d+e-?\d+(\.NEG)?$|^[+-]INF$|^\+QNAN$")
    dec_pattern = re.compile(r"(?<!R|#|P)\b\d+$")
    jcal_fun_pattern = re.compile(r"^__fun_[^,\s]+")
    texture_dimension_pattern = re.compile(r"^[12]D$")
    texture_component_pattern = re.compile(r"^(R|G|A|RG|RA|RGB|RGA|RGBA)$")
    if type(arg) != str:
        raise TypeError
    depmatch = named_depbar_pattern.search(arg)
    amatch = address_pattern.search(arg)
    cmatch = const_mem_pattern.search(arg)
    fmatch = float_pattern.search(arg)
    dmatch = dec_pattern.search(arg)
    sreg_match = sreg_pattern.search(arg)
    jcal_fun_match = jcal_fun_pattern.search(arg)
    texture_dim_match = texture_dimension_pattern.search(arg)
    texture_com_match = texture_component_pattern.search(arg)
    if texture_dim_match is not None:
        return TextureDimensionOperand(arg)
    elif texture_com_match is not None:
        return TextureComponentOperand(arg)
    if jcal_fun_match is not None:
        return Simulator_function_name(arg)
    if depmatch is not None:
        return NamedDependencyBarrier(arg)
    if sreg_match is not None:
        return SReg(arg)
    elif cmatch is not None:
        return ConstantAccess(
            argument_to_object(cmatch.group(1)),
            argument_to_object(cmatch.group(2)),
            cmatch.group(3),
        )
    elif arg.count("|") == 2:
        if arg.startswith("-|"):
            return UnaryOp("-|", arg.replace("|", "").replace("-", ""))
        return UnaryOp("|", arg.replace("|", ""))
    elif arg[0] == "!":
        return UnaryOp("!", arg.lstrip("!"))
    elif arg[0] == "~":
        return UnaryOp("~", arg.strip("~"))
    elif arg[0] == "-" and "-INF" not in arg:
        return UnaryOp("-", arg.lstrip("-"))
    elif arg[0:2] == "CC":
        return CC_Register(arg)
    elif arg[0] == "R":
        return Register(arg)
    elif arg[0] == "P":
        return PredicateRegister(arg)
    elif arg[0:2] == "0x":
        return HexImmediate(arg)
    elif arg[0] == "{":
        return Barrier(arg)
    elif fmatch is not None:
        return FloatImmediate(arg)
    elif dmatch is not None:
        return DecImmediate(arg)
    elif amatch is not None:
        return RegAddress(arg)
    else:
        raise ValueError(f"[sass_ast.py]: Unable to parse {arg}")
