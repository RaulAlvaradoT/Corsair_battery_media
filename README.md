# Corsair Battery Level

**Monitor de batería en la bandeja del sistema para auriculares inalámbricos Corsair, con soporte de botón multimedia en modelos compatibles.**

![Plataforma](https://img.shields.io/badge/plataforma-Windows%2010%2F11-0078D6)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![Licencia](https://img.shields.io/badge/licencia-MIT-green)

Proyecto **de código abierto** hecho para la comunidad. Si tienes unos auriculares Corsair inalámbricos y te gustaría ver el nivel de batería sin abrir iCUE, esta herramienta es para ti. Nació de una necesidad real, se mantiene abierta y **cualquiera puede contribuir**.

---

## Índice

- [Descripción](#descripción)
- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Compilación](#compilación)
- [Dispositivos compatibles](#dispositivos-compatibles)
- [Cómo funciona](#cómo-funciona)
- [Soporte del botón Modo](#soporte-del-botón-modo)
- [Solución de problemas](#solución-de-problemas)
- [Contribuir](#contribuir)
- [Licencia](#licencia)
- [Aviso legal](#aviso-legal)

---

## Descripción

Muestra el **nivel de batería** y el estado de tus auriculares Corsair inalámbricos como un icono en la bandeja del sistema de Windows, sin necesidad de abrir iCUE para consultarlo. En los modelos que lo permiten, además convierte el botón físico **Modo** en la tecla multimedia **Play/Pause**.

La aplicación:

- Funciona **sin privilegios de administrador**.
- Usa **pywinusb** (Python puro) para hablar con el dispositivo, sin compiladores ni dependencias nativas.
- Se distribuye como un único `.exe` sin ventana de consola y con instalador opcional.

---

## Características

- **Nivel de batería en la bandeja**: porcentaje y estado (Conectado / Cargando / Carga completa / Batería baja / Desconectado).
- **Icono dinámico** según el nivel (10% … 90%, 100%) con iconos propios para carga y desconexión.
- **Aviso de batería baja** al llegar al 10%.
- **Icono de "lleno" y aviso para desconectar** cuando la carga se completa.
- **Reconexión automática** al desconectar y reconectar el dispositivo.
- **Menú de bandeja** con *Refresh device*, *Start with Windows* (activar/desactivar) y *Exit*.
- **Arranque automático** opcional en Windows.
- **Botón Modo → Play/Pause** en los modelos que emiten un evento HID para él (ver [Soporte del botón Modo](#soporte-del-botón-modo)).

---

## Requisitos

- **Windows 10 / 11**
- **Python 3.10 o superior** (solo si vas a ejecutar o compilar desde el código fuente)
- Unos **auriculares Corsair inalámbricos compatibles** (ver [Dispositivos compatibles](#dispositivos-compatibles))

---

## Instalación

### Opción 1 — Instalador (recomendada para usuarios)

1. Descarga `CorsairBatteryLevel-Setup.exe` desde la sección de *Releases*.
2. Ejecútalo y elige si quieres **arrancar con Windows** y crear un **acceso directo** (ambos opcionales).
3. La aplicación se instala, aparece en el menú Inicio y se abre automáticamente.

El instalador pide permisos de administrador solo para instalar en `Program Files`; **la aplicación en sí no necesita administrador**.

### Opción 2 — Desde el código fuente

```bash
git clone https://github.com/TU_USUARIO/corsair-battery-level.git
cd corsair-battery-level

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

---

## Uso

Una vez en marcha, verás el icono en la bandeja del sistema (junto al reloj). Al pasar el ratón por encima se muestra el nivel y el estado, por ejemplo:

```
Corsair VOID ELITE Wireless: Connected (61%)
Corsair VOID ELITE Wireless: Charging (~61%)
Corsair VOID ELITE Wireless: Fully charged (100%)
```

Con el botón derecho se abre el menú:

| Ítem | Acción |
|---|---|
| **Refresh device** | Reconecta el dispositivo (útil si cambió de estado). |
| **Start with Windows** | Activa o desactiva el arranque automático para el usuario actual. |
| **Exit** | Cierra la aplicación. |

---

## Compilación

El script `build.ps1` crea (o repara) el entorno virtual, instala las dependencias, compila el ejecutable y, si Inno Setup está instalado, genera el instalador:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Usa `-SkipInstaller` para compilar solo el ejecutable.

**Prerrequisitos de compilación:**

- **Python 3.10 o superior** con *"Add python.exe to PATH"* marcado ([python.org](https://www.python.org/downloads/windows/)).
- **Inno Setup 6** (opcional, solo para el instalador) — [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php).

### Compilación manual

Ejecutable con PyInstaller (usa el `app.spec` incluido):

```bash
python -m PyInstaller --noconfirm app.spec
```

El ejecutable se genera en `dist\CorsairBatteryLevel.exe`.

> El `app.spec` empaqueta la carpeta `icons/` dentro del `.exe` y desactiva la ventana de consola. El ejecutable **no** lleva manifest de elevación, así que arranca en silencio y se autoinicia sin pedir UAC.

Instalador con Inno Setup (después de compilar el ejecutable):

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\CorsairBatteryLevel.iss
```

El instalador se genera en `dist\CorsairBatteryLevel-Setup.exe`.

---

## Dispositivos compatibles

| PID | Modelo |
|---|---|
| `0x0A38` | HS70 Wireless |
| `0x0A4F` | HS70 PRO Wireless |
| `0x1B27` / `0x0A2B` | VOID Wireless |
| `0x0A14` / `0x0A16` / `0x0A1A` | VOID PRO Wireless |
| `0x0A55` / `0x0A51` | **VOID ELITE Wireless** ✓ probado |
| `0x0A3E` / `0x0A40` / `0x0A42` / `0x0A44` / `0x0A5C` / `0x0A64` | Virtuoso RGB Wireless |

> ¿Tu modelo no está en la lista? Añadir un PID es trivial: edita el diccionario `KNOWN_PIDS` en `app.py` y abre un *Pull Request*. Si reporta de forma distinta, cuéntalo en un *issue*.

---

## Cómo funciona

`CorsairApp` abre la interfaz HID principal de los auriculares con **pywinusb**, registra un callback de datos y entra en el bucle de eventos de `pystray`, con un único hilo monitor en segundo plano:

| Componente | Qué hace |
|---|---|
| `_find_device` / `_open` | Recorre las interfaces HID de Corsair y abre la que expone el reporte de batería (`0xC9`), instalando el handler de datos. |
| callback de datos (`_on_report`) | Recibe los reportes de entrada con id `100`. Si `data[1] == 1` dispara `keyboard.send("play/pause")` (botón Modo); si no, lee la batería: `data[2]` es el porcentaje (los valores por encima de `128` se normalizan restando `128`) y `data[4]` el estado del dispositivo. |
| hilo `device-monitor` | Envía la petición de batería `[0xC9, 0x64]` cada 30 s y cada 2 s comprueba que el dispositivo siga conectado, reconectando automáticamente si no. |

Todo el estado compartido está protegido por un `threading.Lock`. Si se desconecta el headset, se libera el handle y el hilo monitor reintenta hasta que el dispositivo vuelve.

---

## Soporte del botón Modo

No todos los modelos Corsair exponen el botón Modo por HID. Este proyecto se validó en el **VOID Elite Wireless (`0x0A55`)**, donde:

- El dispositivo reporta el **estado de batería/carga** en su colección vendor (`usage page 0xFFC5`) cada ~30 s.
- La **rueda de volumen** aparece como un dispositivo consumer control (`usage page 0x0C`).
- El **botón Modo no emite ningún reporte HID** — ni el HID crudo ni la Raw Input de Windows lo ven; iCUE lo procesa por software.

Por eso, en el VOID Elite Wireless la app no puede convertir el botón Modo en Play/Pause por sí sola: **allí Play/Pause requiere tener iCUE abierto** (es iCUE quien traduce el botón). El monitor de batería funciona igual, con o sin iCUE.

En modelos que *sí* reportan el botón como `[100, 1]` en la interfaz vendor, la app dispara `play/pause` por sí misma. Si tu modelo usa otra firma, la detección está en `_on_report` en `app.py`.

---

## Solución de problemas

### La carga siempre marca 100% / salta a lleno

Mientras el cable de carga está conectado, el VOID Elite Wireless reporta `228` (= 100%) en el campo de batería sin importar el nivel real — un quirk del firmware (verificado por HID crudo). Por eso la app muestra una estimación (`Charging (~último % conocido)`) en vez de ese 100% falso, y solo marca **lleno** cuando el dispositivo reporta el estado de carga completa.

### El botón Modo no hace nada sin iCUE

En el VOID Elite Wireless el botón Modo **no se expone por HID**. Es iCUE quien convierte el botón en una tecla multimedia, así que:

- **Si quieres Play/Pause:** mantén iCUE abierto. El monitor de batería funciona junto a él.
- **Si solo quieres la batería:** puedes deshabilitar el arranque de iCUE y poner los servicios Corsair en *Manual*. La batería sigue funcionando, pero el botón Modo dejará de mandar Play/Pause.

### La batería no se actualiza

- Asegúrate de que los auriculares estén encendidos y conectados por su dongle inalámbrico.
- Usa **Refresh device** en el menú de la bandeja para forzar una reconexión.

---

## Contribuir

¡Toda ayuda es bienvenida! Este es un proyecto de la comunidad y cualquier aporte suma:

1. Haz un **fork** del repositorio.
2. Crea una rama descriptiva: `git checkout -b feature/mi-aporte`.
3. Realiza tus cambios y pruébalos.
4. Abre un **Pull Request** explicando qué añades o corriges.

Formas de aportar:

- **Añadir nuevos modelos**: agrega su PID a `KNOWN_PIDS` en `app.py`.
- **Reportar errores**: abre un *issue* con tu modelo, versión de Windows y una descripción del problema.
- **Mejorar la documentación** o traducirla.
- **Compartir el proyecto** con quien pueda necesitarlo.

---

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

## Aviso legal

Este es un proyecto **no oficial** y no está afiliado ni respaldado por Corsair. Los nombres de productos y marcas mencionados pertenecen a sus respectivos propietarios. Úsalo bajo tu propia responsabilidad.
