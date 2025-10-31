# el-ultimo-ayllu
*El Último Ayllu* es una simulación estratégica tipo colony simulator ambientada en los Andes bolivianos.  
El jugador lidera una pequeña colonia de bolivianitos que debe sobrevivir, recolectar recursos, construir defensas y resistir oleadas de enemigos conocidos como Ponchos Rojos.

El proyecto está desarrollado íntegramente en *Python 3.10* utilizando *Pygame 2.6.1, con un enfoque en **IA distribuida, **planificación de tareas por prioridad (heap)* y *simulación autónoma de agentes*.

---

## 📖 Tabla de contenidos
1. [Características principales](#características-principales)
2. [Arquitectura del sistema](#arquitectura-del-sistema)
3. [Requisitos](#requisitos)
4. [Instalación](#instalación)
---

## 🌄 Características principales

- 🌱 *Simulación de colonia andina* con enanos trabajadores (“bolivianitos”) con oficios y energía.  
- ⚒️ *Sistema de planificación de tareas (Planner)* con prioridades dinámicas.  
- 🗺️ *Mapa procedural* con recursos (bosques, minas, granjas, agua, ríos).  
- 🏰 *Construcciones interactivas:* muros, torres y hospitales.  
- ⚔️ *Oleadas de enemigos* generadas por el EventManager, con jefes cada 10 rondas.  
- 💀 *IA de combate y defensa* (guardias, torres con proyectiles, milicia).  
- 🕒 *Ciclo día/noche*, partículas visuales y panel lateral con scroll.  
- 🦙 *Fauna autómata (llamas)* que puede ser cazada para obtener comida.  

---

## 🧩 Arquitectura del sistema

| Módulo | Archivo | Responsabilidad principal |
|--------|----------|---------------------------|
| *main.py* | Ciclo principal del juego, render y entrada del usuario. |
| *world.py* | Generación del mapa, recursos y pathfinding A*. |
| *actors.py* | Definición de actores (colonos, enemigos, llamas). |
| *planner.py* | Planificador de tareas con prioridades (heap). |
| *events.py* | Sistema de eventos y oleadas. |
 //////////////////////////////////////////////

 ## 🧰 Requisitos

### Software
- *Python* ≥ 3.10  
- *Pygame* ≥ 2.6.1  
- (Opcional) Librerías estándar: os, math, heapq, random, collections

### Hardware recomendado
| Requisito | Mínimo | Recomendado |
|------------|---------|-------------|
| CPU | Intel Core i3 | Intel Core i5 o superior |
| RAM | 2 GB | 4 GB o más |
| GPU | Integrada compatible con OpenGL 2.0 | Dedicada (GT 1030 o superior) |
| Resolución | 1280×720 | 1920×1080 |
| Almacenamiento | 200 MB libres | 500 MB libres |

---

## ⚙️ Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/lucianoherpanam/el-ultimo-ayllu
   cd el-ultimo-ayllu
