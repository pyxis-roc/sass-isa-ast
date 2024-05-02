# sass-isa-ast
An ast library for NVIDIA's SASS instruction set, designed for the ROCetta project.

# Pre-requisites
Requires Python 3.8 or greater.

# installation

Install via pip:
```
pip install git+https://github.com/pyxis-roc/sass-isa-ast.git@1.0.1
```

# Usage

This library constructs an AST when given a line of SASS disassembly obtained from
[cuobjdump](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html#cuobjdump). It is recommended to use this
library in conjunction with the `gen_xlat_metadata.py` script provided by [harmonv](https://github.com/pyxis-roc/harmonv).
This will produce a yaml file from a GPU program that includes a list of each line in the disassembly.
Each line can then be parsed by this library.

To convert a line of disassembly into an AST, provide a label (usually the instruction's address) along with the string text of the dissassembly to the ``Statement`` constructor, as follows:

```python
from sass_isa_ast import ast as sass_ast

# The label / text for the disassembly must be available to use this library.
label, text = ...
stmt = sass_ast.Statement(addr, sass_line)

# Access the underlying instruction
instr = stmt.instruction
# Access the instruction's operands
operands = stmt.instruction.arguments
# Check the predicate guard
is_predicated = stmt.instruction.predicated
```


# Limitations
This library has been tested to work with Maxwell, Pascal, and Volta architectures (sm_55, sm_61, sm_70).
New features introduced in architectures after Volta, such as uniform registers, are currently not supported.
Note that VLIW instruction sequences are treated as two distinct statements.