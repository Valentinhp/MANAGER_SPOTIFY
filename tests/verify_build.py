"""Comprueba que el ejecutable incluye código actual y excluye credenciales."""
from pathlib import Path
from types import CodeType
from PyInstaller.archive.readers import CArchiveReader

def signature(code):
    if isinstance(code,CodeType):
        return (code.co_code,tuple(signature(c) for c in code.co_consts),code.co_names,
                code.co_varnames,code.co_argcount,code.co_flags)
    return code

def main():
    archive=CArchiveReader('dist/SpotyVManager.exe')
    for name in archive.toc:
        assert name.replace('\\','/').split('/')[-1] not in ('.env','.cache'),f'Archivo privado incluido: {name}'
    pyz=archive.open_embedded_archive(next(name for name in archive.toc if name.endswith('.pyz')))
    assert 'openai' in pyz.toc, 'Falta el SDK de OpenAI en el ejecutable'
    assert not any(module == 'anthropic' or module.startswith('anthropic.') for module in pyz.toc), 'El ejecutable conserva el SDK anterior'
    count=0
    for module in pyz.toc:
        if module=='src':path=Path('src/__init__.py')
        elif module.startswith('src.'):
            path=Path(module.replace('.','/')+'.py')
            if not path.exists():path=Path(module.replace('.','/')) / '__init__.py'
        else:continue
        bundled=pyz.extract(module)
        current=compile(path.read_bytes(),bundled.co_filename,'exec',dont_inherit=True)
        assert signature(bundled)==signature(current),f'El ejecutable contiene código anterior: {module}'
        count+=1
    print(f'Ejecutable verificado: {count} módulos actuales; sin archivos .env ni .cache')

if __name__=='__main__':main()
