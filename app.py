from flask import Flask, send_from_directory, request, jsonify
import os, json
from datetime import datetime
from urllib.parse import parse_qs

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_proxy(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return "File not found", 404


@app.route('/save_result', methods=['POST', 'OPTIONS'])
def save_result():
    # --- CORS / preflight ---
    if request.method == 'OPTIONS':
        resp = jsonify({"status": "ok"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        resp.headers.add("Access-Control-Allow-Headers", "Content-Type")
        resp.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return resp

    raw = request.get_data(as_text=True) or ""
    content_type = request.headers.get('Content-Type', 'N/A')
    
    print("--- Petición Recibida ---")
    print(f"Content-Type: {content_type}")
    print(f"Body: {raw[:500]}...")
    print("--------------------------")
    
    data = None

    # Lógica de Parseo
    if request.form and "sessionJSON" in request.form:
        print("Parseo exitoso (Caso 2: request.form['sessionJSON'])")
        data = json.loads(request.form["sessionJSON"])
    elif raw:
        try:
            parsed = parse_qs(raw)
            if "sessionJSON" in parsed:
                print("Parseo exitoso (Caso 3: parse_qs(raw)['sessionJSON'])")
                data = json.loads(parsed["sessionJSON"][0])
        except Exception:
             pass # Ignorar si parse_qs falla

    if data is None and raw:
        try:
            data = json.loads(raw) # Intentar leer el body crudo como JSON
            print("Parseo exitoso (Caso 4: json.loads(raw))")
        except json.JSONDecodeError:
            pass 

    if data is None:
        print("❌ PARSEO FALLIDO: No se pudieron extraer datos.")
        resp = jsonify({"status": "error", "reason": "no data received or bad format"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp, 400

    # -----------------------------------------------------------------
    # ¡AQUÍ ESTÁ EL CAMBIO IMPORTANTE!
    # Guardado en Disco Persistente (en lugar de 'results/')
    # -----------------------------------------------------------------
    
    # Esta es la ruta exacta que pusiste en el "Mount Path"
    SAVE_PATH = "/var/data/results"
    
    try:
        os.makedirs(SAVE_PATH, exist_ok=True) # Crea la carpeta si no existe
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(SAVE_PATH, f"result_{ts}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ ¡ÉXITO PERSISTENTE! Resultado guardado en {filename}")
    
    except Exception as e:
        print(f"❌ ERROR AL GUARDAR EN DISCO PERSISTENTE: {e}")
        resp = jsonify({"status": "error", "reason": f"Fallo al escribir en disco: {e}"})
        return resp, 500
    
    # -----------------------------------------------------------------
    # Fin del cambio
    # -----------------------------------------------------------------

    resp = jsonify({"status": "ok"})
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp