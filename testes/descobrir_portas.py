"""Utilitário de diagnóstico para listar portas seriais detectadas no computador."""

import serial.tools.list_ports


portas = serial.tools.list_ports.comports()

print("Portas seriais encontradas:")
print()

for porta in portas:
    print(f"Porta: {porta.device}")
    print(f"Descrição: {porta.description}")
    print()