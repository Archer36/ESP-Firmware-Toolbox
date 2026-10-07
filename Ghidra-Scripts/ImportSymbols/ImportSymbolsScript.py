# ## ###
#  IP: GHIDRA
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Ported from Ghidra's legacy ImportSymbolsScript.py for PyGhidra.
#
# Imports a text file containing one symbol definition per line:
#     symbol_name address function_or_label
#
# The final field is optional: `f` creates or renames a function, while `l`
# creates a label. Addresses use any form accepted by Ghidra's Go To dialog.
# @author unknown; legacy script edited by matedealer; PyGhidra port by Archer36
# @category Data
# @runtime PyGhidra
#

from ghidra.program.model.symbol import SourceType


def get_input_path():
    """Use a script argument when present; otherwise prompt in the GUI."""
    arguments = getScriptArgs()
    if arguments:
        return arguments[0]
    return askFile("Select a symbol map", "Import symbols").getAbsolutePath()


def parse_symbol_line(line, line_number):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    fields = stripped.split()
    if len(fields) < 2 or len(fields) > 3:
        printerr("Skipping malformed line {}: {}".format(line_number, stripped))
        return None

    name, address_text = fields[:2]
    symbol_type = fields[2].lower() if len(fields) == 3 else "l"
    if symbol_type not in ("f", "l"):
        printerr("Skipping line {} with unknown symbol type '{}': {}".format(
            line_number, symbol_type, stripped
        ))
        return None

    return name, address_text, symbol_type


def run():
    if currentProgram is None:
        printerr("No current program")
        return

    input_path = get_input_path()
    function_manager = currentProgram.getFunctionManager()
    labels_created = 0
    functions_created = 0
    functions_renamed = 0
    skipped = 0

    with open(input_path, encoding="utf-8") as symbol_file:
        for line_number, line in enumerate(symbol_file, start=1):
            if monitor.isCancelled():
                println("Import cancelled")
                break

            parsed = parse_symbol_line(line, line_number)
            if parsed is None:
                continue

            name, address_text, symbol_type = parsed
            address = toAddr(address_text)
            if address is None:
                printerr("Skipping line {} with invalid address '{}': {}".format(
                    line_number, address_text, name
                ))
                skipped += 1
                continue

            try:
                if symbol_type == "f":
                    function = function_manager.getFunctionAt(address)
                    if function is None:
                        createFunction(address, name)
                        functions_created += 1
                    else:
                        function.setName(name, SourceType.USER_DEFINED)
                        functions_renamed += 1
                else:
                    createLabel(address, name, False)
                    labels_created += 1
            except Exception as error:
                printerr("Skipping {} at {}: {}".format(name, address, error))
                skipped += 1

    println(
        "Imported symbols from {}: {} labels, {} functions created, {} functions renamed, {} skipped".format(
            input_path, labels_created, functions_created, functions_renamed, skipped
        )
    )


run()
