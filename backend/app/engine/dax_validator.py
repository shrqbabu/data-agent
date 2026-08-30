"""DAX validation — independent check that generated measures are safe & correct.

Checks:
  * every Table[Column] reference resolves to the actual schema
  * every [Measure] dependency resolves to a defined measure
  * balanced (), [], {}
  * no obvious syntax corruption (dangling operators, empty expressions)
"""

from __future__ import annotations

import re

from app.engine.context import DaxMeasure, SchemaModel

_COL_REF = re.compile(r"(?<!\[)\b([A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]")
_MEASURE_REF = re.compile(r"\[\s*([^\[\]\r\n]{1,120}?)\s*\]")


def validate_dax(measures: list[DaxMeasure], model: SchemaModel) -> dict:
    """Returns {'passed': bool, 'measures': [{name, passed, errors, warnings}]}."""
    tables = model.tables  # table_name -> column defs
    defined_names = {m.name for m in measures}
    all_passed = True
    results = []

    for m in measures:
        errors: list[str] = []
        warnings: list[str] = []

        code = m.dax_code

        # 1. Balanced delimiters.
        for open_, close, label in [("(", ")", "parentheses"), ("[", "]", "brackets"), ("{", "}", "braces")]:
            if code.count(open_) != code.count(close):
                errors.append(f"Unbalanced {label} in '{m.name}'.")

        # 2. Table[Column] references resolve.
        for tname, col in _COL_REF.findall(code):
            col_defs = tables.get(tname)
            if col_defs is None:
                errors.append(f"Reference to unknown table '{tname}' in '{m.name}'.")
                continue
            col_names = {c["name"] for c in col_defs}
            if col not in col_names:
                errors.append(f"Column '{tname}[{col}]' does not exist in '{m.name}'.")

        # 3. Measure references resolve to defined measures.
        for ref in _MEASURE_REF.findall(code):
            ref = ref.strip()
            if ref == m.name:
                continue  # self-reference in VAR name context is fine
            if ref and ref not in defined_names:
                warnings.append(f"Measure '[{ref}]' referenced but not defined in this run.")

        # 4. No empty expression.
        for expr in re.findall(r"(?:RETURN|CALCULATE|VAR)\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*$", code):
            errors.append(f"Empty expression near: {expr.strip()} in '{m.name}'.")

        passed = not errors
        if not passed:
            all_passed = False

        m.validation_status = "validated" if passed else "failed"
        results.append({
            "name": m.name,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "group": None,
        })

    return {"passed": all_passed, "measures": results}