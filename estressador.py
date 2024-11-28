import time
import psutil
import ctypes
import numpy as np
from threading import Thread
import tkinter as tk
from tkinter import ttk, scrolledtext

class Estressador:
    def __init__(self, root):
        self.root = root
        self.root.title("Estressador de Memória")

        self.monitorando = False
        self.thread_monitor = None
        self.thread_estressar = None
        self.lista_blocos = [] 

        ttk.Label(root, text="Estressador de Memória", font=("Arial", 16)).pack(pady=10)

        self.label_memoria = ttk.Label(root, text="Memória livre: 0 MB (0%)", font=("Arial", 12))
        self.label_memoria.pack(pady=5)

        input_porcentagem_memoria = ttk.Frame(root)
        input_porcentagem_memoria.pack(pady=5)
        ttk.Label(input_porcentagem_memoria, text="Porcentagem de memória a alocar:").grid(row=0, column=0, padx=5)
        self.valor_porcentagem = ttk.Entry(input_porcentagem_memoria, width=10)
        self.valor_porcentagem.grid(row=0, column=1, padx=5)

        self.botao_iniciar = ttk.Button(root, text="Iniciar", command=self.toggle_processamento)
        self.botao_iniciar.pack(pady=10)

        ttk.Label(root, text="Logs de Alocação:").pack(anchor="w", padx=10)
        self.console_alocacao = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
        self.console_alocacao.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.console_alocacao.bind("<Key>", lambda e: "break")

        ttk.Label(root, text="Logs de Monitoramento:").pack(anchor="w", padx=10)
        self.console_monitoramento = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD)
        self.console_monitoramento.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.console_monitoramento.bind("<Key>", lambda e: "break")

    def atualizar_memoria_livre(self):
        # psutil.virtual_memory() chama GlobalMemoryStatusEx para obter informacoes detalhadas da memoria do sistema
        informacoes_memoria = psutil.virtual_memory()
        memoria_livre_mb = int(informacoes_memoria.available / (1024 ** 2))
        memoria_total_mb = int(informacoes_memoria.total / (1024 ** 2))
        porcentagem_livre = (memoria_livre_mb / memoria_total_mb) * 100
        self.label_memoria.config(text=f"Memória livre: {memoria_livre_mb} MB ({porcentagem_livre:.2f}%)")

    def monitorar_memoria(self):
        # psutil.Process() utiliza chamadas nativas de API do Windows como OpenProcess para acessar informacoes do processo atual
        processo = psutil.Process()
        while self.monitorando:
            # Chamadas repetidas a GlobalMemoryStatusEx para atualização da memória.
            informacoes_memoria = psutil.virtual_memory()
            memoria_livre_mb = int(informacoes_memoria.available / (1024 ** 2))
            memoria_total_mb = int(informacoes_memoria.total / (1024 ** 2))
            porcentagem_livre = (memoria_livre_mb / memoria_total_mb) * 100

            # process.memory_info() chama GetProcessMemoryInfo do Windows para obter detalhes de uso de memoria pelo processo atual
            memoria_processo = processo.memory_info().rss / (1024 ** 2)

            self.console_monitoramento.insert(tk.END,
                f"Memória do Sistema Livre: {memoria_livre_mb} MB ({porcentagem_livre:.2f}%), "
                f"Memória do Programa: {memoria_processo:.2f} MB\n")
            self.console_monitoramento.see(tk.END)

            time.sleep(1)
            self.root.after(100, self.atualizar_memoria_livre)

    def estressar_memoria(self, percentual):
        # psutil.virtual_memory() chama GlobalMemoryStatusEx para obter a memória disponivel no sistema
        informacoes_memoria = psutil.virtual_memory()
        memoriaLivre = informacoes_memoria.available
        memoria_a_utilizar = int((percentual / 100) * memoriaLivre)
        memoria_por_bloco = 10 * 1024 * 1024  # Bloco de 10 MB
        memoria_alocada = 0

        try:
            while self.monitorando and memoria_alocada < memoria_a_utilizar:
                tamanho_bloco = min(memoria_por_bloco, memoria_a_utilizar - memoria_alocada)
                # np.random.randint usa alocação dinâmica com malloc.
                bloco = np.random.randint(0, 256, size=tamanho_bloco, dtype=np.uint8).tobytes()
                self.lista_blocos.append(bloco)
                memoria_alocada += len(bloco)

                # ctypes.create_string_buffer chama HeapAlloc ou VirtualAlloc dependendo da implementacao.
                endereco = ctypes.addressof(ctypes.create_string_buffer(len(bloco)))
                valores_iniciais = list(bloco[:10])

                self.console_alocacao.insert(tk.END,
                    f"Memória Alocada: {int(memoria_alocada / (1024 ** 2))} MB\n"
                    f"Memória Livre Restante: {int(psutil.virtual_memory().available / (1024 ** 2))} MB\n"
                    f"Endereço do Bloco Atual: {hex(endereco)}\n"
                    f"Primeiros 10 Valores no Bloco: {valores_iniciais}\n\n")
                self.console_alocacao.see(tk.END)

                time.sleep(0.1)

            if self.monitorando:
                self.console_alocacao.insert(tk.END, "Memória alocada conforme solicitado.\n")
                self.console_alocacao.see(tk.END)

        except MemoryError:
            self.console_alocacao.insert(tk.END, "Erro: Memória insuficiente.\n")
            self.console_alocacao.see(tk.END)

    def liberar_memoria(self):
        # Limpa a lista de blocos liberando memoria alocada.
        self.lista_blocos.clear()
        self.console_alocacao.insert(tk.END, "Memória liberada com sucesso.\n")
        self.console_alocacao.see(tk.END)

    def toggle_processamento(self):
        if not self.monitorando:
            self.monitorando = True
            self.botao_iniciar.config(text="Parar")

            try:
                percentual = float(self.valor_porcentagem.get())
                if percentual <= 0 or percentual > 100:
                    raise ValueError("Porcentagem inválida.")
            except ValueError:
                self.console_alocacao.insert(tk.END, "Erro: Informe uma porcentagem válida (1-100).\n")
                self.console_alocacao.see(tk.END)
                self.monitorando = False
                self.botao_iniciar.config(text="Iniciar")
                return

            # Criação de threads usa CreateThread no Windows.
            self.thread_monitor = Thread(target=self.monitorar_memoria, daemon=True)
            self.thread_estressar = Thread(target=self.estressar_memoria, args=(percentual,), daemon=True)
            self.thread_monitor.start()
            self.thread_estressar.start()
        else:
            self.monitorando = False
            self.liberar_memoria()
            self.botao_iniciar.config(text="Iniciar")
            self.console_monitoramento.insert(tk.END, "Monitoramento interrompido.\n")
            self.console_monitoramento.see(tk.END)

def main():
    root = tk.Tk()
    app = Estressador(root)
    app.atualizar_memoria_livre()
    root.mainloop()

if __name__ == "__main__":
    main()
