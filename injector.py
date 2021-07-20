import module.pyinjector as pyinjector

pid = 15608 # ID процесса (меняется после каждого перезапуска игры/пограммы)
dll_name = 'cheat.dll' # Название .dll

pyinjector.inject(pid, dll_name)