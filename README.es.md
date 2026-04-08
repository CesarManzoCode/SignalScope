<div align="center">

<h1>⚡ SignalScope</h1>

<p><strong>Elimina el ruido. Muestra lo que importa.</strong></p>

<p>
  SignalScope es una herramienta de inteligencia orientada a la terminal que obtiene contenido de fuentes técnicas,
  lo filtra según tus intereses y utiliza el LLM de tu elección para clasificar, resumir
  y entregarte únicamente las señales que merecen tu atención — en Markdown limpio.
</p>

<br/>

<p>
  <a href="./README.md">🌐 English Version</a>
</p>

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/Licencia-MIT-22c55e?style=flat-square)
![LLM Support](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Anthropic%20%7C%20Ollama-a855f7?style=flat-square)
![Status](https://img.shields.io/badge/Estado-Activo-blue?style=flat-square)

</div>

---

## Qué Hace

Cada día, decenas de artículos técnicos, publicaciones e hilos compiten por tu atención.
SignalScope se conecta a tus fuentes configuradas, obtiene el contenido más reciente y lo pasa por un
pipeline que filtra por tema, puntúa por relevancia y clasifica cada elemento como `critical`,
`important` u `optional` — para que sepas exactamente dónde mirar primero.

El resultado es un reporte Markdown estructurado, guardado localmente, listo para leer.

---

## Cómo Funciona

```
Fuentes → Investigación → Filtro → LLM → Reporte Clasificado
```

1. **Sources** — Los proveedores de datos registrados (ej. Hacker News) se consultan de forma concurrente.
2. **Research** — Los elementos en bruto se obtienen de forma asíncrona mediante HTTP.
3. **Filter** — Los elementos se reducen según tus tecnologías y temas configurados.
4. **LLM** — Cada elemento se envía al proveedor elegido (OpenAI, Anthropic u Ollama) para su resumen y clasificación de prioridad.
5. **Output** — Un archivo `.md` limpio se guarda en `/output/` con todos los elementos clasificados y formateados.

---

## Proveedores LLM soportados

| Proveedor | Requiere Clave | Local |
|-----------|:--------------:|:-----:|
| OpenAI    |       ✅        |   ❌   |
| Anthropic |       ✅        |   ❌   |
| Ollama    |       ❌        |   ✅   |

---

## Niveles de Prioridad

Cada elemento procesado por el LLM recibe una de tres etiquetas de prioridad:

| Nivel       | Significado                                                                          |
|-------------|--------------------------------------------------------------------------------------|
| `critical`  | Requiere atención inmediata — cambios críticos, exploits activos, incidentes mayores |
| `important` | Muy relevante para tu trabajo — vale la pena leerlo hoy                              |
| `optional`  | Informativo o experimental — léelo cuando tengas tiempo                              |

Las reglas de prioridad se ajustan automáticamente según el `mode` que configures (`dev` o `security`).

---

## Guía de Instalación y Uso

### Requisitos Previos

- Python **3.11** o superior
- Gestor de paquetes `pip`
- Una clave API de OpenAI o Anthropic (no requerida para Ollama)

---

### Linux / macOS

**1. Clona el repositorio**

```bash
git clone https://github.com/CesarManzoCode/SignalScope.git
cd SignalScope
```

**2. Crea y activa un entorno virtual**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Instala las dependencias**

```bash
pip install -r requirements.txt
```

**4. Configura las variables de entorno**

```bash
cp .env.example .env
```

Abre `.env` con tu editor y completa tus claves API:

```bash
nano .env
# o
code .env
```

**5. Configura tus preferencias**

Edita `src/config/user_config.json` según tus intereses:

```bash
nano src/config/user_config.json
```

**6. Ejecuta SignalScope**

```bash
cd src
python main.py
```

---

### Windows

**1. Clona el repositorio**

```powershell
git clone https://github.com/CesarManzoCode/SignalScope.git
cd SignalScope
```

**2. Crea y activa un entorno virtual**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

> Si obtienes un error de política de ejecución, ejecuta primero:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**3. Instala las dependencias**

```powershell
pip install -r requirements.txt
```

**4. Configura las variables de entorno**

```powershell
copy .env.example .env
notepad .env
```

**5. Configura tus preferencias**

```powershell
notepad src\config\user_config.json
```

**6. Ejecuta SignalScope**

```powershell
cd src
python main.py
```

---

### Referencia de Configuración

`src/config/user_config.json` controla qué obtiene SignalScope y cómo se comporta:

```json
{
  "mode": "dev",
  "llm": {
    "provider": "openai"
  },
  "technologies": ["python", "ai", "backend"],
  "topics": ["security", "llms"],
  "sources": {
    "include": [],
    "exclude": []
  },
  "priority": {
    "prefer_high_score": true,
    "prefer_recent": true
  },
  "output": {
    "format": "markdown"
  }
}
```

| Campo               | Opciones                              | Descripción                                             |
|---------------------|---------------------------------------|---------------------------------------------------------|
| `mode`              | `"dev"`, `"security"`                 | Ajusta las reglas de prioridad del LLM según tu caso    |
| `llm.provider`      | `"openai"`, `"anthropic"`, `"ollama"` | Qué backend de LLM utilizar                             |
| `technologies`      | Cualquier lista de strings            | Palabras clave para filtrar contenido por stack técnico |
| `topics`            | Cualquier lista de strings            | Temas de interés (ej. `"security"`, `"llms"`)           |
| `prefer_high_score` | `true` / `false`                      | Priorizar contenido con alta puntuación de la comunidad |
| `prefer_recent`     | `true` / `false`                      | Favorecer elementos publicados recientemente            |
| `output.format`     | `"markdown"`                          | Formato de salida (Markdown es el valor por defecto)    |

---

### Referencia de Variables de Entorno

`.env` controla el acceso a las API:

```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OLLAMA_URL=http://localhost:11434
DEFAULT_MODEL=gpt-4.1-mini
```

> Para Ollama, no se requiere clave API. Solo asegúrate de que el servidor de Ollama esté corriendo localmente antes de ejecutar SignalScope.

---

## Salida

Cada ejecución guarda un archivo Markdown estructurado en el directorio `output/`.
Cada elemento incluye un **Resumen**, **Puntos Clave**, **Detalles** y su **Prioridad** asignada.

```
output/
└── example.md
```

---

## Estructura del Proyecto

```
SignalScope/
├── src/
│   ├── main.py                        # Punto de entrada
│   ├── config/
│   │   ├── user_config.json           # Preferencias del usuario
│   │   ├── user_config.py             # Cargador de configuración
│   │   ├── prompts/                   # Constructores de prompts para el LLM
│   │   └── protocols/                 # Lógica de clasificación de prioridad
│   ├── core/
│   │   └── types/                     # Tipos de dominio (RawItem, FinalItem, etc.)
│   ├── infrastructure/
│   │   ├── llm_clients/               # Adaptadores de OpenAI, Anthropic, Ollama
│   │   └── sources/                   # Clientes de fuentes de datos (Hacker News, etc.)
│   ├── modules/
│   │   ├── source_selector/           # Selecciona fuentes activas desde la config
│   │   ├── research/                  # Obtención asíncrona de datos
│   │   ├── filter/                    # Pipeline de filtrado de contenido
│   │   ├── llm/                       # Orquestación del LLM
│   │   └── converter/                 # Conversión de formato de salida
│   └── formatters/
│       └── markdown_formatter.py      # Formateador de salida Markdown
├── output/                            # Reportes generados
├── .env.example                       # Plantilla de variables de entorno
├── requirements.txt
└── README.md
```

---

## Licencia

Distribuido bajo la Licencia MIT. Consulta [`LICENSE`](./LICENSE) para más detalles.
