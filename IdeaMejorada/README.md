# Sistema de Gestión de Taller de Motos AKT

Implementación base en Flask con:

- Login por rol (`admin`, `recepcionista`, `mecanico`)
- Gestión de motos (ingreso, asignación exclusiva, liberación, estados)
- Dashboard administrador con métricas y gráficos
- Chat general en tiempo real con Socket.IO
- Base SQLite local y datos semilla

## Requisitos

- Python 3.11+

## Ejecución

1. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar la app:

   ```bash
   python app.py
   ```

3. Abrir en navegador:

   - `http://localhost:5000`

## Usuarios semilla

- `admin / admin123`
- `recep1 / recep123`
- `recep2 / recep123`
- `mec1 / mec123` ... `mec6 / mec123`
