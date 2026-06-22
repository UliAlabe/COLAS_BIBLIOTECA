import threading
import tkinter as tk
from tkinter import ttk, messagebox

from simulacion import simular_sistema


class VentanaSimulacion:
    """
    Interfaz gráfica principal del simulador.

    Contiene el panel de parámetros, dos pestañas (vector de estado y auditoría Euler)
    y los atajos de teclado para copiar datos a Excel.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Eventos Discretos UTN - Frontend Tkinter + SimPy + Euler")
        self.root.geometry("1500x800")

        self.vars = {}
        self.btn_iniciar = None
        self.construir_panel_parametros()

        # Panel de resultados (etiquetas de métricas al terminar la simulación)
        self.panel_res = ttk.Frame(self.root, padding=5)
        self.panel_res.pack(fill=tk.X)

        self.lbl_res1 = ttk.Label(self.panel_res, text="Esperando ejecución...", font=("Arial", 11, "bold"))
        self.lbl_res1.pack()
        self.lbl_res2 = ttk.Label(self.panel_res, text="")
        self.lbl_res2.pack()

        # Notebook con dos pestañas: vector de estado y auditoría Euler
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Pestaña 1: Vector de Estado
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="Vector de Estado Principal")

        self.scroll_y_1 = ttk.Scrollbar(self.tab1, orient=tk.VERTICAL)
        self.scroll_x_1 = ttk.Scrollbar(self.tab1, orient=tk.HORIZONTAL)

        self.tree_principal = ttk.Treeview(self.tab1, show="headings",
                                           yscrollcommand=self.scroll_y_1.set,
                                           xscrollcommand=self.scroll_x_1.set,
                                           selectmode="extended")

        self.scroll_y_1.config(command=self.tree_principal.yview)
        self.scroll_x_1.config(command=self.tree_principal.xview)

        self.scroll_y_1.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_x_1.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_principal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Pestaña 2: Auditoría Euler
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="Auditoría Ecuaciones Euler")

        self.scroll_y_2 = ttk.Scrollbar(self.tab2, orient=tk.VERTICAL)

        self.tree_euler = ttk.Treeview(self.tab2, show="headings",
                                       yscrollcommand=self.scroll_y_2.set,
                                       selectmode="extended")

        self.scroll_y_2.config(command=self.tree_euler.yview)
        self.scroll_y_2.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_euler.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Atajos globales: Ctrl+A selecciona todo, Ctrl+C copia a portapapeles
        self.root.bind("<Control-a>", self.seleccionar_todo)
        self.root.bind("<Control-c>", self.copiar_a_excel)

        ttk.Label(
            self.root,
            text="Atajos: Seleccioná las filas de la tabla activa (o Ctrl+A) y presioná Ctrl+C para llevarlas a Excel"
        ).pack(side=tk.BOTTOM)

    def construir_panel_parametros(self):
        """Construye el panel superior con todos los campos de entrada de parámetros."""
        panel = ttk.LabelFrame(self.root, text="Panel de Parámetros y Validaciones", padding=10)
        panel.pack(fill=tk.X, padx=10, pady=5)

        configs = [
            ("Lógica de Corte y Visual.", [
                ("Max. Llegadas (N)", "limite_iteraciones", 100000),
                ("Simular hasta min. (X)", "tiempo_simulacion", 100000),
                ("Mostrar desde min. (j)", "desde_reloj", 0),
                ("Cant. filas a mostrar (i)", "filas_mostrar", 100),
                ("Capacidad Max", "capacidad", 20),
                ("Paso Euler (h)", "paso_euler", 0.1)
            ]),
            ("Probabilidades (%)", [
                ("% Pedir Libro", "prob_pedir", 45),
                ("% Devolver Libro", "prob_devolver", 45),
                ("% Consultar", "prob_consultar", 10),
                ("% Se Queda a Leer", "prob_queda", 40),
                ("Llegadas (Cte)", "t_llegada", 4.0)
            ]),
            ("Tiempos de Atención (min)", [
                ("Media Pedir Exp(-)", "media_pedir", 6.0),
                ("Unif. Dev A", "unif_dev_a", 1.5),
                ("Unif. Dev B", "unif_dev_b", 2.5),
                ("Unif. Cons A", "unif_cons_a", 2.0),
                ("Unif. Cons B", "unif_cons_b", 5.0),
                ("Unif. Pág A", "unif_pag_a", 100),
                ("Unif. Pág B", "unif_pag_b", 350),
            ]),
            ("Constantes Integración K", [
                ("K (Pág < 200)", "k1", 100),
                ("K (Pág < 300)", "k2", 90),
                ("K (Pág >= 300)", "k3", 70)
            ])
        ]

        col_offset = 0
        for seccion, campos in configs:
            ttk.Label(panel, text=seccion, font=("Arial", 9, "bold"), foreground="darkblue").grid(
                row=0, column=col_offset, columnspan=2, pady=2
            )
            row_idx = 1
            for label_text, var_name, default_val in campos:
                ttk.Label(panel, text=label_text).grid(row=row_idx, column=col_offset, sticky=tk.W, padx=5)
                entry = ttk.Entry(panel, width=8)
                entry.insert(0, str(default_val))
                entry.grid(row=row_idx, column=col_offset + 1, padx=5, pady=2)
                self.vars[var_name] = entry
                row_idx += 1
            col_offset += 2

        btn_frame = ttk.Frame(panel)
        btn_frame.grid(row=1, column=col_offset, rowspan=5, padx=20)
        self.btn_iniciar = ttk.Button(btn_frame, text="▶ INICIAR MOTOR SIMPY",
                                      command=self.ejecutar_simulacion, width=25)
        self.btn_iniciar.pack(ipady=10)

    def obtener_parametros(self):
        """
        Lee y valida los valores ingresados en el panel de parámetros.
        Devuelve un dict con todos los parámetros o None si hay errores.
        """
        try:
            tiempo_simulacion   = float(self.vars['tiempo_simulacion'].get())
            limite_iteraciones  = int(self.vars['limite_iteraciones'].get())
            desde_reloj         = float(self.vars['desde_reloj'].get())
            filas_mostrar       = int(self.vars['filas_mostrar'].get())
            paso_euler          = float(self.vars['paso_euler'].get())
            capacidad           = int(self.vars['capacidad'].get())
            t_llegada           = float(self.vars['t_llegada'].get())
            p_pedir             = float(self.vars['prob_pedir'].get())
            p_dev               = float(self.vars['prob_devolver'].get())
            p_cons              = float(self.vars['prob_consultar'].get())
            p_queda             = float(self.vars['prob_queda'].get())
            m_pedir             = float(self.vars['media_pedir'].get())
            u_dev_a             = float(self.vars['unif_dev_a'].get())
            u_dev_b             = float(self.vars['unif_dev_b'].get())
            u_cons_a            = float(self.vars['unif_cons_a'].get())
            u_cons_b            = float(self.vars['unif_cons_b'].get())
            u_pag_a             = float(self.vars['unif_pag_a'].get())
            u_pag_b             = float(self.vars['unif_pag_b'].get())
            k1                  = float(self.vars['k1'].get())
            k2                  = float(self.vars['k2'].get())
            k3                  = float(self.vars['k3'].get())
        except ValueError:
            messagebox.showerror("Error", "Ingresaste texto donde va un número.")
            return None

        errores = []

        if tiempo_simulacion <= 0:
            errores.append("X (tiempo a simular) debe ser > 0.")
        if limite_iteraciones <= 0:
            errores.append("N (máx. llegadas) debe ser > 0.")
        if filas_mostrar <= 0:
            errores.append("i (cant. filas a mostrar) debe ser > 0.")
        if desde_reloj < 0:
            errores.append("j (mostrar desde min.) debe ser >= 0.")
        if desde_reloj >= tiempo_simulacion:
            errores.append("j (mostrar desde min.) debe ser menor que X (tiempo a simular).")
        if paso_euler <= 0:
            errores.append("h (paso Euler) debe ser > 0.")
        if capacidad <= 0:
            errores.append("Capacidad máxima debe ser > 0.")
        if t_llegada <= 0:
            errores.append("Llegadas (Cte) debe ser > 0.")
        if abs(p_pedir + p_dev + p_cons - 100.0) > 0.01:
            errores.append("Las probabilidades (% Pedir + % Devolver + % Consultar) deben sumar exactamente 100%.")
        if not (0 <= p_queda <= 100):
            errores.append("% Se Queda a Leer debe estar entre 0% y 100%.")
        if m_pedir <= 0:
            errores.append("Media Pedir Exp(-) debe ser > 0.")
        if u_dev_a >= u_dev_b:
            errores.append("Unif. Dev: A debe ser menor que B.")
        if u_cons_a >= u_cons_b:
            errores.append("Unif. Cons: A debe ser menor que B.")
        if u_pag_a >= u_pag_b:
            errores.append("Unif. Pág: A debe ser menor que B.")
        if k1 <= 0:
            errores.append("K (Pág < 200) debe ser > 0.")
        if k2 <= 0:
            errores.append("K (Pág < 300) debe ser > 0.")
        if k3 <= 0:
            errores.append("K (Pág >= 300) debe ser > 0.")

        if errores:
            messagebox.showerror("Error de validación", "\n".join(errores))
            return None

        return {
            'tiempo_simulacion':  tiempo_simulacion,
            'limite_iteraciones': limite_iteraciones,
            'desde_reloj':        desde_reloj,
            'filas_mostrar':      filas_mostrar,
            'paso_euler':         paso_euler,
            'capacidad':          capacidad,
            't_llegada':          t_llegada,
            'p_pedir':            p_pedir / 100.0,
            'p_dev':              p_dev / 100.0,
            'p_queda':            p_queda / 100.0,
            'm_pedir':            m_pedir,
            'u_dev_a':            u_dev_a,
            'u_dev_b':            u_dev_b,
            'u_cons_a':           u_cons_a,
            'u_cons_b':           u_cons_b,
            'u_pag_a':            u_pag_a,
            'u_pag_b':            u_pag_b,
            'k1': k1,
            'k2': k2,
            'k3': k3
        }

    def ejecutar_simulacion(self):
        """
        Lanza la simulación en un hilo separado para no bloquear la UI.
        Deshabilita el botón mientras corre y lo vuelve a habilitar al terminar.
        """
        params = self.obtener_parametros()
        if not params:
            return

        self.btn_iniciar.config(state="disabled")
        self.lbl_res1.config(text="Simulando... por favor esperá.")
        self.lbl_res2.config(text="")

        def correr_en_segundo_plano():
            resultado = simular_sistema(params)
            # root.after garantiza que la actualización de widgets ocurra en el hilo principal de Tkinter
            self.root.after(0, lambda: self.mostrar_resultados(resultado))

        threading.Thread(target=correr_en_segundo_plano, daemon=True).start()

    def mostrar_resultados(self, resultado):
        """Recibe el resultado de la simulación y carga ambas tablas en la UI."""
        cols_prin, datos_prin, cols_eul, datos_eul, p_rechazos, p_permanencia = resultado

        self.lbl_res1.config(
            text=f"Promedio de permanencia: {p_permanencia:.2f} min | "
                 f"Filas Vector Estado: {len(datos_prin)} | Filas Euler: {len(datos_eul)}"
        )
        self.lbl_res2.config(text=f"Porcentaje de rechazos global (Fin Simulación): {p_rechazos:.2f}%")

        # Carga Tabla Principal (Pestaña 1)
        self.tree_principal.delete(*self.tree_principal.get_children())
        self.tree_principal["columns"] = cols_prin

        for col in cols_prin:
            self.tree_principal.heading(col, text=col)
            # Ancho de columna según el tipo de dato que contiene
            if "_ID" in col:
                w = 40
            elif "Emp" in col:
                w = 110
            elif "Fin Atenc" in col:
                w = 85
            elif "Próx Llegada" in col:
                w = 85
            elif "Fila" in col or "Leyendo" in col or "Cola" in col:
                w = 60
            elif "% Rech" in col:
                w = 85
            elif "Acum Perm" in col:
                w = 85
            elif "Evento" in col:
                w = 320
            elif "RND" in col:
                w = 70
            elif "Tipo Atenc" in col:
                w = 100
            elif "T. Atenc" in col:
                w = 70
            elif "¿Se Queda?" in col:
                w = 75
            elif "Páginas" in col or "Valor K" in col:
                w = 65
            elif "T. Lectura" in col:
                w = 75
            else:
                w = 80
            self.tree_principal.column(col, width=w, anchor=tk.CENTER, stretch=False)

        for fila in datos_prin:
            self.tree_principal.insert("", tk.END, values=fila)

        # Carga Tabla Euler (Pestaña 2)
        self.tree_euler.delete(*self.tree_euler.get_children())
        self.tree_euler["columns"] = cols_eul

        for col in cols_eul:
            self.tree_euler.heading(col, text=col)
            if "Entidad" in col:
                w = 180
            elif "Iteración" in col:
                w = 80
            elif "Reloj" in col:
                w = 100
            elif "Estado" in col:
                w = 130
            else:
                w = 120
            self.tree_euler.column(col, width=w, anchor=tk.CENTER, stretch=False)

        for fila in datos_eul:
            self.tree_euler.insert("", tk.END, values=fila)

        self.btn_iniciar.config(state="normal")

    def seleccionar_todo(self, event):
        """Selecciona todas las filas de la tabla que esté activa en la pestaña actual."""
        tab_id = self.notebook.select()
        if self.notebook.index(tab_id) == 0:
            self.tree_principal.selection_set(self.tree_principal.get_children())
        else:
            self.tree_euler.selection_set(self.tree_euler.get_children())
        return "break"

    def copiar_a_excel(self, event):
        """
        Copia al portapapeles las filas seleccionadas (o todas si no hay selección)
        de la tabla activa, en formato TSV listo para pegar en Excel.
        """
        tab_id = self.notebook.select()
        tree_activo = self.tree_principal if self.notebook.index(tab_id) == 0 else self.tree_euler

        seleccion = tree_activo.selection()
        if not seleccion:
            seleccion = tree_activo.get_children()

        texto = "\t".join([tree_activo.heading(c)["text"] for c in tree_activo["columns"]]) + "\n"
        for item in seleccion:
            texto += "\t".join(str(v) for v in tree_activo.item(item, "values")) + "\n"

        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.root.update()

        # Feedback visual breve en el título de la ventana
        titulo = self.root.title()
        self.root.title("¡Filas copiadas! Listas para pegar en Excel (Ctrl+V)")
        self.root.after(2000, lambda: self.root.title(titulo))

        return "break"
