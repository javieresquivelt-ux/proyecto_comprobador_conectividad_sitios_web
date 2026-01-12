# import utilidades
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import filedialog
import ipaddress
import subprocess
import platform
import socket
import csv

# ----------------- LÓGICA COMÚN -----------------

def construir_url(url_cruda, protocolo):
    """
    Construye una URL completa a partir de una dirección parcial y un protocolo.
    """
    url_cruda = url_cruda.strip()
    if url_cruda.startswith("http://") or url_cruda.startswith("https://"):
        return url_cruda
    if protocolo == "http":
        return "http://" + url_cruda
    else:
        return "https://" + url_cruda

def mensaje_por_codigo(codigo):
    """
    Devuelve un mensaje descriptivo según el rango del código HTTP recibido.
    """
    if 200 <= codigo < 300:
        return "Éxito: el sitio respondió correctamente."
    elif 300 <= codigo < 400:
        return "Redirección: la URL puede haber sido movida o redirigida."
    elif 400 <= codigo < 500:
        return "Error del cliente: revisa la dirección o tus permisos."
    elif 500 <= codigo < 600:
        return "Error del servidor: el sitio tiene problemas internos."
    else:
        return "Código HTTP no estándar o poco común."

def es_ipv4(texto):
    """
    Indica si el texto representa una dirección IPv4 válida.
    """
    try:
        ipaddress.IPv4Address(texto)
        return True
    except ipaddress.AddressValueError:
        return False

def entrada_parece_valida(texto):
    """
    Validación rápida de la dirección ingresada (IP v4 o dominio sencillo).
    """
    texto = texto.strip()
    if not texto:
        return False
    if es_ipv4(texto):
        return True
    if texto.isdigit():
        return False
    if "." not in texto:
        return False
    return True

# ----------------- LÓGICA HTTP/HTTPS -----------------

def comprobar_http_https(direccion, tipo_prueba):
    """
    Comprueba la conectividad HTTP/HTTPS hacia una dirección.
    Muestra detalle en el Text y un resumen en el label.
    """
    protocolo = tipo_prueba

    limpiar_text_resultado()

    if not entrada_parece_valida(direccion):
        label_resultado.config(
            text="Dirección inválida. Escribe un dominio (www.ejemplo.com) o una IP (8.8.8.8)."
        )
        return

    url = construir_url(direccion, protocolo)

    label_resultado.config(
        text=f"Comprobando {url} usando {protocolo.upper()}..."
    )
    ventana.update_idletasks()

    text_resultado.config(state="normal")
    try:
        respuesta = urllib.request.urlopen(url, timeout=5)
        codigo = respuesta.getcode()
        info = mensaje_por_codigo(codigo)

        linea1 = f"URL: {url}\n"
        linea2 = f"Método: {protocolo.upper()} | Código: {codigo} | Detalle: {info}\n"
        text_resultado.insert("end", linea1)
        text_resultado.insert("end", linea2, "ok")

        label_resultado.config(
            text=f"{url} → {codigo} ({info})"
        )
    except urllib.error.HTTPError as e:
        info = mensaje_por_codigo(e.code)
        linea1 = f"URL: {url}\n"
        linea2 = f"Error HTTP {protocolo.upper()} | Código: {e.code} | Detalle: {info}\n"
        text_resultado.insert("end", linea1)
        text_resultado.insert("end", linea2, "fail")

        label_resultado.config(
            text=f"{url} → Error HTTP {e.code} ({info})"
        )
    except urllib.error.URLError as e:
        mensaje = (
            f"No se pudo conectar usando {protocolo.upper()} (timeout o DNS).\n"
            f"Detalle técnico: {e.reason}\n"
        )
        text_resultado.insert("end", f"URL: {url}\n")
        text_resultado.insert("end", mensaje, "fail")

        label_resultado.config(
            text=f"{url} → No se pudo conectar ({e.reason})"
        )
    except Exception as e:
        texto = f"Ocurrió un error inesperado: {e}\n"
        text_resultado.insert("end", texto, "fail")
        label_resultado.config(text="Ocurrió un error inesperado.")
    finally:
        text_resultado.config(state="disabled")

# ----------------- LÓGICA PING -----------------

def hacer_ping(host):
    """
    Ejecuta un ping sencillo al host indicado.
    """
    sistema = platform.system().lower()
    if "windows" in sistema:
        comando = ["ping", "-n", "1", "-w", "3000", host]
    else:
        comando = ["ping", "-c", "1", "-W", "3", host]

    try:
        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        exito = (resultado.returncode == 0)
        if exito:
            return True, "Ping exitoso: el host respondió."
        else:
            return False, "Ping fallido: el host no respondió."
    except FileNotFoundError:
        return False, "Comando 'ping' no encontrado en el sistema."
    except Exception as e:
        return False, f"Error al ejecutar ping: {e}"

def comprobar_ping_unico(direccion):
    """
    Comprueba conectividad básica haciendo ping a una sola dirección.
    Muestra resultado en el Text y resumen en el label.
    """
    limpiar_text_resultado()

    if not entrada_parece_valida(direccion):
        label_resultado.config(
            text="Dirección inválida para ping. Escribe un dominio o una IP válida."
        )
        return

    label_resultado.config(
        text=f"Haciendo ping a {direccion}..."
    )
    ventana.update_idletasks()

    exito, mensaje = hacer_ping(direccion)

    text_resultado.config(state="normal")
    linea = f"{direccion} → {mensaje}\n"
    tag = "ok" if exito else "fail"
    text_resultado.insert("end", linea, tag)
    text_resultado.config(state="disabled")

    label_resultado.config(text=f"{direccion} → {mensaje}")

def comprobar_ping_rango(ip_inicio_str, ip_fin_str):
    """
    Comprueba conectividad haciendo ping a un rango de IPs IPv4.
    Detalle en el Text, resumen en el label.
    """
    limpiar_text_resultado()

    try:
        ip_inicio = ipaddress.IPv4Address(ip_inicio_str.strip())
        ip_fin = ipaddress.IPv4Address(ip_fin_str.strip())
    except ipaddress.AddressValueError:
        label_resultado.config(
            text="IP inicio o IP fin inválidas. Escribe IPv4 válidas (ej: 192.168.1.10)."
        )
        return

    if ip_inicio > ip_fin:
        label_resultado.config(
            text="El rango es inválido: IP inicio es mayor que IP fin."
        )
        return

    cantidad = int(ip_fin) - int(ip_inicio) + 1
    if cantidad > 256:
        label_resultado.config(
            text=f"Rango demasiado grande ({cantidad} IPs). Máximo permitido: 256."
        )
        return

    label_resultado.config(
        text=f"Haciendo ping al rango {ip_inicio} - {ip_fin} ({cantidad} IPs)..."
    )
    ventana.update_idletasks()

    respuestas_ok = 0
    respuestas_fail = 0

    text_resultado.config(state="normal")

    for ip_int in range(int(ip_inicio), int(ip_fin) + 1):
        ip_actual = str(ipaddress.IPv4Address(ip_int))
        exito, mensaje = hacer_ping(ip_actual)

        if exito:
            respuestas_ok += 1
            tag = "ok"
        else:
            respuestas_fail += 1
            tag = "fail"

        linea = f"{ip_actual} → {mensaje}\n"
        text_resultado.insert("end", linea, tag)
        text_resultado.see("end")
        ventana.update_idletasks()

    text_resultado.config(state="disabled")

    resumen = (
        f"Rango {ip_inicio} - {ip_fin} ({cantidad} IPs). "
        f"Respondieron: {respuestas_ok} · No respondieron: {respuestas_fail}."
    )
    label_resultado.config(text=resumen)

# ----------------- LÓGICA TCP (SSH/FTP/SFTP/Telnet) -----------------

def probar_puerto(host, puerto, timeout=3):
    """
    Intenta abrir una conexión TCP a host:puerto con un timeout corto.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            resultado = sock.connect_ex((host, puerto))
            if resultado == 0:
                return True, f"Puerto {puerto} abierto (conexión posible)."
            else:
                return False, f"Puerto {puerto} cerrado o inaccesible."
    except Exception as e:
        return False, f"Error al comprobar el puerto {puerto}: {e}"

def comprobar_tcp(direccion, servicio):
    """
    Comprueba la conectividad TCP hacia un servicio típico (SSH, FTP, SFTP, Telnet).
    Muestra detalle en el Text y resumen en el label.
    """
    limpiar_text_resultado()

    if not entrada_parece_valida(direccion):
        label_resultado.config(
            text="Dirección inválida. Escribe un dominio o una IP válida."
        )
        return

    puertos = {
        "ssh": 22,
        "ftp": 21,
        "sftp": 22,
        "telnet": 23,
    }

    puerto = puertos.get(servicio)
    if puerto is None:
        label_resultado.config(text="Servicio TCP desconocido.")
        return

    label_resultado.config(
        text=f"Comprobando servicio {servicio.upper()} en {direccion}:{puerto}..."
    )
    ventana.update_idletasks()

    exito, mensaje = probar_puerto(direccion, puerto)

    text_resultado.config(state="normal")
    linea1 = f"Host: {direccion}\n"
    linea2 = f"Servicio: {servicio.upper()} | Puerto: {puerto} | Resultado: {mensaje}\n"
    tag = "ok" if exito else "fail"
    text_resultado.insert("end", linea1)
    text_resultado.insert("end", linea2, tag)
    text_resultado.config(state="disabled")

    label_resultado.config(
        text=f"{direccion}:{puerto} ({servicio.upper()}) → {mensaje}"
    )

# ----------------- EXPORTAR Y LIMPIAR -----------------

def exportar_csv():
    """
    Exporta el contenido del Text de resultados a un archivo CSV.

    Intenta soportar estos formatos de línea:
        - "<host> → <mensaje>"
        - "Host: X" + "Servicio: ... Resultado: Y"
        - "URL: X" + "Método: ... Detalle: Y"
    """
    contenido = text_resultado.get("1.0", "end").strip()
    if not contenido:
        label_resultado.config(text="No hay resultados para exportar.")
        return

    lineas = contenido.splitlines()
    filas = []
    i = 0

    while i < len(lineas):
        linea = lineas[i]

        # Formato genérico con flecha: "host → mensaje"
        if "→" in linea:
            host, mensaje = linea.split("→", 1)
            filas.append([host.strip(), mensaje.strip()])
            i += 1
            continue

        # Bloque TCP: "Host: X" y luego "Servicio: ... Resultado: Y"
        if linea.startswith("Host:"):
            host = linea.replace("Host:", "").strip()
            mensaje = ""
            if i + 1 < len(lineas):
                siguiente = lineas[i + 1]
                if "Resultado:" in siguiente:
                    # Ejemplo: "Servicio: SSH | Puerto: 22 | Resultado: Puerto cerrado..."
                    partes = siguiente.split("Resultado:", 1)
                    mensaje = partes[1].strip()
                else:
                    mensaje = siguiente.strip()
                i += 2
            else:
                i += 1
            filas.append([host, mensaje])
            continue

        # Bloque HTTP/HTTPS: "URL: X" y luego detalle
        if linea.startswith("URL:"):
            host = linea.replace("URL:", "").strip()
            mensaje = ""
            if i + 1 < len(lineas):
                mensaje = lineas[i + 1].strip()
                i += 2
            else:
                i += 1
            filas.append([host, mensaje])
            continue

        # Cualquier otra línea se ignora para exportación
        i += 1

    if not filas:
        label_resultado.config(text="No se encontraron líneas válidas para exportar.")
        return

    ruta = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("Archivo CSV", "*.csv"), ("Todos los archivos", "*.*")],
        title="Guardar resultados"
    )
    if not ruta:
        return

    try:
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["host", "mensaje"])
            writer.writerows(filas)
        label_resultado.config(text=f"Resultados exportados a: {ruta}")
    except Exception as e:
        label_resultado.config(text=f"Error al exportar CSV: {e}")

def limpiar_todo():
    """
    Limpia el resumen y el resultado detallado y
    devuelve el modo PING a 'IP única'.
    """
    limpiar_text_resultado()
    label_resultado.config(
        text="Resultados limpiados. Ingresa una dirección y ejecuta una nueva prueba."
    )

    # Volver a modo PING de IP única
    modo_ping_var.set("unico")
    actualizar_modo_ping()

# ----------------- CONTROLADOR PRINCIPAL -----------------

def comprobar():
    """
    Punto de entrada único para el botón 'Comprobar'.
    """
    tipo = tipo_prueba_var.get()
    servicio_tcp = servicio_tcp_var.get()
    modo_ping = modo_ping_var.get()

    if tipo in ("http", "https"):
        direccion = entry_url.get().strip()
        comprobar_http_https(direccion, tipo)
    elif tipo == "ping":
        if modo_ping == "unico":
            direccion = entry_url.get().strip()
            comprobar_ping_unico(direccion)
        else:
            ip_inicio_str = entry_ip_inicio.get().strip()
            ip_fin_str = entry_ip_fin.get().strip()
            comprobar_ping_rango(ip_inicio_str, ip_fin_str)
    elif tipo == "tcp":
        direccion = entry_url.get().strip()
        comprobar_tcp(direccion, servicio_tcp)
    else:
        label_resultado.config(text="Tipo de prueba desconocido.")

def actualizar_estado_servicios_tcp():
    """
    Habilita o deshabilita los botones de servicio TCP
    según el tipo de prueba seleccionado.
    """
    tipo = tipo_prueba_var.get()
    estado = "normal" if tipo == "tcp" else "disabled"

    for rb in (radio_ssh, radio_ftp, radio_sftp, radio_telnet):
        rb.config(state=estado)

def actualizar_modo_ping():
    """
    Habilita o deshabilita los campos de rango de IP
    según el modo de ping seleccionado (único o rango).
    """
    modo = modo_ping_var.get()
    if modo == "unico":
        entry_ip_inicio.config(state="disabled")
        entry_ip_fin.config(state="disabled")
    else:
        entry_ip_inicio.config(state="normal")
        entry_ip_fin.config(state="normal")

def limpiar_text_resultado():
    """
    Limpia el contenido del widget de texto de resultados detallados.
    """
    text_resultado.config(state="normal")
    text_resultado.delete("1.0", "end")
    text_resultado.config(state="disabled")

# ----------------- GUI -----------------

ventana = tk.Tk()
ventana.title("Comprobador de conectividad - Proyecto Conquer")
ventana.geometry("900x500")

# Campo Dirección general
label_url = tk.Label(ventana, text="Dirección (dominio o IP):")
label_url.pack()

entry_url = tk.Entry(ventana, width=40)
entry_url.pack()

# Selector de tipo de prueba
tipo_prueba_var = tk.StringVar(value="https")

frame_tipo = tk.Frame(ventana)
frame_tipo.pack(pady=5)

label_tipo = tk.Label(frame_tipo, text="Tipo de prueba:")
label_tipo.pack(side="left")

radio_tipo_http = tk.Radiobutton(
    frame_tipo,
    text="HTTP",
    variable=tipo_prueba_var,
    value="http",
    command=actualizar_estado_servicios_tcp
)
radio_tipo_http.pack(side="left")

radio_tipo_https = tk.Radiobutton(
    frame_tipo,
    text="HTTPS",
    variable=tipo_prueba_var,
    value="https",
    command=actualizar_estado_servicios_tcp
)
radio_tipo_https.pack(side="left")

radio_tipo_ping = tk.Radiobutton(
    frame_tipo,
    text="PING",
    variable=tipo_prueba_var,
    value="ping",
    command=actualizar_estado_servicios_tcp
)
radio_tipo_ping.pack(side="left")

radio_tipo_tcp = tk.Radiobutton(
    frame_tipo,
    text="TCP (SSH/FTP/SFTP/Telnet)",
    variable=tipo_prueba_var,
    value="tcp",
    command=actualizar_estado_servicios_tcp
)
radio_tipo_tcp.pack(side="left")

# Selector de modo de ping (único / rango)
modo_ping_var = tk.StringVar(value="unico")

frame_ping = tk.Frame(ventana)
frame_ping.pack(pady=5)

label_modo_ping = tk.Label(frame_ping, text="Modo PING:")
label_modo_ping.pack(side="left")

radio_ping_unico = tk.Radiobutton(
    frame_ping,
    text="IP única (usa Dirección)",
    variable=modo_ping_var,
    value="unico",
    command=actualizar_modo_ping
)
radio_ping_unico.pack(side="left")

radio_ping_rango = tk.Radiobutton(
    frame_ping,
    text="Rango de IPs",
    variable=modo_ping_var,
    value="rango",
    command=actualizar_modo_ping
)
radio_ping_rango.pack(side="left")

# Campos para rango de IPs
frame_rango = tk.Frame(ventana)
frame_rango.pack(pady=5)

label_ip_inicio = tk.Label(frame_rango, text="IP inicio:")
label_ip_inicio.pack(side="left")

entry_ip_inicio = tk.Entry(frame_rango, width=15)
entry_ip_inicio.pack(side="left", padx=5)

label_ip_fin = tk.Label(frame_rango, text="IP fin:")
label_ip_fin.pack(side="left")

entry_ip_fin = tk.Entry(frame_rango, width=15)
entry_ip_fin.pack(side="left", padx=5)

# Inicialmente, deshabilitar los campos de rango (modo por defecto: único)
entry_ip_inicio.config(state="disabled")
entry_ip_fin.config(state="disabled")

# Selector de servicio TCP
servicio_tcp_var = tk.StringVar(value="ssh")

frame_servicio = tk.Frame(ventana)
frame_servicio.pack(pady=5)

label_servicio = tk.Label(frame_servicio, text="Servicio TCP:")
label_servicio.pack(side="left")

radio_ssh = tk.Radiobutton(
    frame_servicio,
    text="SSH",
    variable=servicio_tcp_var,
    value="ssh"
)
radio_ssh.pack(side="left")

radio_ftp = tk.Radiobutton(
    frame_servicio,
    text="FTP",
    variable=servicio_tcp_var,
    value="ftp"
)
radio_ftp.pack(side="left")

radio_sftp = tk.Radiobutton(
    frame_servicio,
    text="SFTP",
    variable=servicio_tcp_var,
    value="sftp"
)
radio_sftp.pack(side="left")

radio_telnet = tk.Radiobutton(
    frame_servicio,
    text="Telnet",
    variable=servicio_tcp_var,
    value="telnet"
)
radio_telnet.pack(side="left")

# Estado inicial: deshabilitar grupo TCP si tipo no es tcp
actualizar_estado_servicios_tcp()

# Botones de acción
frame_botones = tk.Frame(ventana)
frame_botones.pack(pady=5)

boton = tk.Button(frame_botones, text="Comprobar", command=comprobar)
boton.pack(side="left", padx=5)

boton_exportar = tk.Button(frame_botones, text="Exportar CSV", command=exportar_csv)
boton_exportar.pack(side="left", padx=5)

boton_limpiar = tk.Button(frame_botones, text="Limpiar", command=limpiar_todo)
boton_limpiar.pack(side="left", padx=5)

# Resultado resumen
label_resultado = tk.Label(
    ventana,
    text="Ingresa una dirección, elige tipo de prueba y presiona Comprobar.",
    justify="left"
)
label_resultado.pack(pady=5)

# Resultado detallado (para todos los tipos de prueba)
frame_text = tk.Frame(ventana)
frame_text.pack(fill="both", expand=True, padx=10, pady=5)

# Scrollbar vertical
scrollbar_resultado = tk.Scrollbar(frame_text, orient="vertical")
scrollbar_resultado.pack(side="right", fill="y")

text_resultado = tk.Text(
    frame_text,
    height=10,
    width=100,
    state="disabled",
    yscrollcommand=scrollbar_resultado.set
)
text_resultado.pack(side="left", fill="both", expand=True)

scrollbar_resultado.config(command=text_resultado.yview)

# Configurar tags para estilos
text_resultado.tag_configure("ok", foreground="green")
text_resultado.tag_configure("fail", foreground="red", font=("TkDefaultFont", 9, "bold"))

ventana.mainloop()