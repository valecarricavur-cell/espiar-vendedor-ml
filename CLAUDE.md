# AgenciaML — Instrucciones para Claude

Este repositorio es el sistema de agentes de AgenciaML, una agencia de e-commerce argentina.

## Archivo de identidad
Antes de generar cualquier contenido, leer siempre `agencia.md` para respetar
el tono, estilo y lineamientos de la agencia.

---

## Triggers — palabras clave que activan cada agente

### "Espía" o "Espia"
Correr el agente de espionaje ML:
```
python3 espiar_vendedor.py todoairelibregd --carpeta TODOAIRELIBRE
```
Luego abrir el HTML generado.

### "Marketing [tema]"
1. Leer `agencia.md`
2. Generar en el chat (sin script externo):
   - 3 ideas de contenido concretas para el tema
   - Guion TikTok completo (hook 0-3s / desarrollo / CTA)
   - Caption Instagram listo para copiar + 10 hashtags
   - Plan de acción en 3 pasos para ejecutar esta semana
   - 1 consejo clave que marque la diferencia
3. Guardar el resultado en `reportes_ml/AgenciaML/marketing_{slug}_{fecha}.md`

### "Guion [tema]"
1. Leer `agencia.md`
2. Generar guion completo para que el dueño se grabe:
   - Formato: TikTok/Reels (60-90 seg)
   - Hook impactante (frase exacta para decir en cámara)
   - Desarrollo punto por punto (qué decir, cómo moverse)
   - Cierre con CTA claro
   - Notas de dirección (tono, energía, gestos sugeridos)
3. Guardar en `reportes_ml/AgenciaML/guion_{slug}_{fecha}.md`

### "Carrusel [tema]"
(Requiere GEMINI_API_KEY — pendiente de implementar)
Generar estructura del carrusel + textos por slide mientras tanto.

### "Espia web [URL]"
Correr análisis de competencia externa sobre esa URL.
(Pendiente de implementar)

---

## Reglas generales
- Siempre leer `agencia.md` antes de generar contenido
- Todo en español argentino, tono directo y práctico
- Guardar siempre los resultados en `reportes_ml/AgenciaML/`
- Notificar con sonido al terminar cada tarea
