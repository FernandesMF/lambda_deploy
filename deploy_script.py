"""
Script de automação para o deploy do lambda de preprocessamento.

O objetivo é automatizar a geração do pacote .zip que será subido para a nuvem aws, com
o código para o lambda.

As etapas para gerar esse arquivo são as seguintes:
    1- dado o arquivo .py que vai ser executado (entry point da aplicação), encontrar as
       dependências dele (externas/bibliotecas python e internas/módulos ion_rec_sys)
    2- encontrar e agregar as dependências das dependências internas recursivamente (as
       externas conseguem ser tratadas corretamente pelo pip)
    3- fazer instalação local das dependências externas que não estiverem disponíveis
       para a execução dos lambdas na aws
    4- fazer soft links dos arquivos de dependência interna (imitar a estrutura de
       diretórios e colocar os arquivos __init__.py)
    5- chamar o script makefile para gerar o zip
"""


import re
from typing import List, Set, TypeVar
import pathlib as pl
from os import symlink
from subprocess import check_call, run
from sys import executable


FILE_TO_BE_EXECUTED: str = "lambda_execution_file.py"
MAX_ITERATIONS: int = 100
INTERNAL_LIBRARY = "my_awesome_library"
PREFIX_UNTIL_INT_LIB = "../"
LOCAL_PACKAGING_DIRECTORY = "./packaging_area"
AWS_LIBRARIES_LIST = "aws_lambda_libs_py_3.6.txt"
T = TypeVar("T")


# TODO: unit test
def main() -> None:
    """Fluxo principal de execução, coordena as etapas"""

    internal_dependencies_processed = set()
    internal_dependencies_unprocessed = {FILE_TO_BE_EXECUTED}
    external_dependencies = set()

    find_dependencies_recursively(
        internal_dependencies_processed,
        internal_dependencies_unprocessed,
        external_dependencies
    )
    assert internal_dependencies_unprocessed == set(), "Há dependências internas não-processadas."
    print("Dependências internas:")
    print(internal_dependencies_processed)
    print("Dependências externas:")
    print(external_dependencies)

    print("Criando links simbólicos para as dependências internas")
    internal_dependencies_processed.remove(FILE_TO_BE_EXECUTED)
    create_links_to_int_dependencies(
        internal_dependencies_processed
    )

    print("Fazendo instalação local das dependências externas")
    install_non_aws_ext_dependencies(
        external_dependencies
    )

    run(["make"])


# TODO: unit test
def find_dependencies_recursively(
    internal_dependencies_processed: Set[str],
    internal_dependencies_unprocessed: Set[str],
    external_dependencies: Set[str]
) -> None:
    """Chama o processamento de dependências recursivamente"""

    i = 0
    while internal_dependencies_unprocessed and i < MAX_ITERATIONS:

        process_internal_dependency(
            internal_dependencies_processed,
            internal_dependencies_unprocessed,
            external_dependencies,
            for_pick(internal_dependencies_unprocessed)
        )
        i += 1
        assert i <= MAX_ITERATIONS, "Número máximo de iterações atingido."


# TODO: unit test
def for_pick(set_to_pick_from: Set[T]) -> T:
    """Retorna um elemento do conjunto"""
    # https://stackoverflow.com/questions/59825/how-to-retrieve-an-element-from-a-set-without-removing-it

    for element in set_to_pick_from:
        break
    return element


# TODO: unit test
def process_internal_dependency(
    internal_dependencies_processed: Set[str],
    internal_dependencies_unprocessed: Set[str],
    external_dependencies: Set[str],
    current_dependency: str
) -> None:
    """Processa uma dependência individualmente"""

    import_lines = get_import_lines(current_dependency)

    [external_deps, internal_deps] = sort_dependencies(import_lines)

    external_dependencies.update(external_deps)
    internal_dependencies_unprocessed.update(internal_deps)
    internal_dependencies_processed.update([current_dependency])
    internal_dependencies_unprocessed.remove(current_dependency)


# TODO: unit test
def get_import_lines(file_path: str) -> List[str]:
    """Retorna as linhas de import do arquivo"""

    simple_import = re.compile("^import \S+\n")
    simple_import_as = re.compile("^import \S+ as \S+\n")
    from_import = re.compile("^from \S+ import \S+\n")
    from_import_as = re.compile("^from \S+ import \S+ as \S+\n")

    import_lines = []
    with open(file_path, "r") as f:

        line = f.readline()

        while line:

            si_match = simple_import.match(line)
            sia_match = simple_import_as.match(line)
            fi_match = from_import.match(line)
            fia_match = from_import_as.match(line)

            if si_match or sia_match or fi_match or fia_match:
                import_lines.append(line)

            line = f.readline()

    return import_lines


# TODO: unit test
def sort_dependencies(import_lines: List[str]) -> List[List[str]]:
    """Separa as dependências de import_lines em internas e externas"""

    external_dependencies = []
    internal_dependencies = []

    while import_lines:

        line = import_lines.pop(0)
        match = compute_match(line)
        library_split = match.group("library").split(".")

        if INTERNAL_LIBRARY in line:  # internal dependency
            module_path = PREFIX_UNTIL_INT_LIB + "/".join(library_split) + ".py"
            internal_dependencies.append(module_path)

        else:  # external dependency
            library = library_split[0]
            external_dependencies.append(library)

    return [external_dependencies, internal_dependencies]


# TODO: unit test
def compute_match(line: str) -> re.Match:
    """Retorna um objeto match com grupos 'library', 'submodule' e 'nickname' dependendo
    do tipo de import que foi feito na linha 'line'"""

    simple_import = re.compile("^import (?P<library>\S+)\n")
    simple_import_as = re.compile("^import (?P<library>\S+) as (?P<nickname>\S+)\n")
    from_import = re.compile("^from (?P<library>\S+) import (?P<submodule>\S+)\n")
    from_import_as = re.compile(
        "^from (?P<library>\S+) import (?P<submodule>\S+) as (?P<nickname>\S+)\n"
    )

    si_match = simple_import.match(line)
    sia_match = simple_import_as.match(line)
    fi_match = from_import.match(line)
    fia_match = from_import_as.match(line)

    num_matches = bool(si_match) + bool(sia_match) + bool(fi_match) + bool(fia_match)
    assert num_matches == 1, "Número inesperado de matches"

    if si_match:
        return si_match
    elif sia_match:
        return sia_match
    elif fi_match:
        return fi_match
    elif fia_match:
        return fia_match


# TODO: unit test
def create_links_to_int_dependencies(internal_dependencies: Set[str]) -> None:
    """Cria a estrutura de diretórios com os links simbólicos para as dependências
    internas"""

    for dependency in internal_dependencies:
        replicate_directory_structure(dependency)
        create_symbolic_link(dependency)


# TODO: unit test
def replicate_directory_structure(dependency: str) -> None:
    """Replica a estrutura de diretórios de uma dependência interna e coloca os arquivos
    init"""

    local_packaging_path = pl.Path(LOCAL_PACKAGING_DIRECTORY + "/" + INTERNAL_LIBRARY)
    library_path = pl.Path(PREFIX_UNTIL_INT_LIB + INTERNAL_LIBRARY)
    dependency_path = pl.Path(dependency)

    traveled_parts = []
    untraveled_parts = list(set(dependency_path.parent.parts) - set(library_path.parts))

    current_path = local_packaging_path
    if not pl.Path.is_dir(current_path):
        pl.Path.mkdir(current_path)
    init_path = current_path.joinpath("__init__.py")
    if not pl.Path.is_file(init_path):
        init_path.open("w")

    while untraveled_parts:
        next_part = untraveled_parts[0]
        current_path = current_path.joinpath(next_part)
        if not pl.Path.is_dir(current_path):
            pl.Path.mkdir(current_path)
        init_path = current_path.joinpath("__init__.py")
        if not pl.Path.is_file(init_path):
            init_path.open("w")
        traveled_parts.append(next_part)
        untraveled_parts.remove(next_part)


# TODO: unit test
def create_symbolic_link(file: str) -> None:
    """Cria um link simbólico para a dependência internas"""

    local_packaging_path = pl.Path(LOCAL_PACKAGING_DIRECTORY)
    file_path = pl.Path(file)

    dest_path = pl.Path.joinpath(local_packaging_path, *file_path.parts[1:])
    if pl.Path.is_file(dest_path):
        return

    up_steps = len(file_path.parts)
    up_prefix = ["../"] * up_steps
    up_path = pl.Path(*up_prefix)
    point_path = pl.Path.joinpath(up_path, *file_path.parts[1:])

    symlink(point_path, dest_path)


# TODO: unit test
def install_non_aws_ext_dependencies(external_dependencies: Set[str]) -> None:
    """Chama o pip para instalar as dependências que não estiverem no contexto de execução
    de lambdas na aws"""
    #https://pip.pypa.io/en/stable/user_guide/#using-pip-from-your-program

    libs_not_in_aws = non_aws_libraries(external_dependencies)
    check_call(
        [executable, '-m', 'pip', 'install', *libs_not_in_aws, '--target', LOCAL_PACKAGING_DIRECTORY]
    )


# TODO: unit test
def non_aws_libraries(external_dependencies: Set[str]) -> Set[str]:
    """Retorna as dependências que não são disponibilizadas pela aws"""

    non_available_libs = external_dependencies
    non_available_libs.remove("boto3")  # boto3 is always supposed to be included in aws context, right?
    library_re = re.compile("^(?P<libname>[^.\s]+).?(?P<rest>\S*)\n")

    with open(AWS_LIBRARIES_LIST, "r") as lib_file:
        line = lib_file.readline()
        while line:
            if ("#" not in line):
                libname = library_re.match(line).group("libname")
                if libname in non_available_libs:
                    non_available_libs.remove(libname)
            line = lib_file.readline()

    return non_available_libs


if __name__ == "__main__":
    main()
