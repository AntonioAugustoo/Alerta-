import os
import logging
from flask import Flask, request, jsonify, render_template
from datetime import datetime

# Desativa logs pesados do Flask (GET/POST)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configura os caminhos para acessar corretamente a pasta Frontend
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, 
            template_folder=os.path.join(FRONTEND_DIR, 'templates'),
            static_folder=os.path.join(FRONTEND_DIR, 'static'))

# --- VARIÁVEL GLOBAL PARA O RESET ---
reset_agendado = False

# Armazena os últimos logs em memória
MAX_LOGS = 50
logs_memoria = [
    {"hora": datetime.now().strftime('%H:%M:%S'), "tipo": "INFO", "msg": "Servidor web iniciado. Aguardando dados do sensor..."}
]

def add_log(tipo, msg):
    hora = datetime.now().strftime('%H:%M:%S')
    logs_memoria.insert(0, {"hora": hora, "tipo": tipo, "msg": msg})
    if len(logs_memoria) > MAX_LOGS:
        logs_memoria.pop()

# Rota para o frontend principal
@app.route('/')
def index():
    return render_template('index.html')

# Retorna os logs mais recentes (usado pelo JS no frontend)
@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify(logs_memoria), 200

# >>> NOVA ROTA: Acionada pelo botão do Frontend <<<
@app.route('/api/trigger-reset', methods=['POST'])
def trigger_reset():
    global reset_agendado
    reset_agendado = True
    add_log("COMANDO", "🔄 Botão pressionado! Ordem de RESET enviada para a placa.")
    print("\n👆 Comando de RESET ativado pelo Frontend!\n")
    return jsonify({"status": "success", "message": "Reset agendado"}), 200

# Rota para o Checkpoint (Ping de funcionamento)
@app.route('/api/checkpoint', methods=['POST'])
def checkpoint():
    data = request.json
    msg = f"ID: {data.get('checkpoint')} | Hora no ESP: {data.get('timestamp')}"
    print(f"--- Checkpoint [{datetime.now().strftime('%H:%M:%S')}] ---")
    print(msg)
    return jsonify({"status": "success", "message": "Checkpoint recebido"}), 200

# Rota para os Dados do Sensor e Alertas
@app.route('/api/sensor', methods=['POST'])
def sensor_data():
    global reset_agendado
    data = request.json
    status = data.get('status', 'DESCONHECIDO')
    acc = data.get('accMagnitude')
    cp = data.get('checkpoint')
    
    # Destacar se houver queda
    if "QUEDA" in status.upper():
        print("\n" + "!"*40)
        print(f"🚨 ALERTA DE QUEDA: {status} 🚨")
        print(f"Aceleração: {acc} m/s²")
        print("!"*40 + "\n")
        add_log("ALERTA", f"🚨 QUEDA DETECTADA: {status} | Aceleração: {acc} m/s²")
    else:
        print(f"LOG [{cp}]: {status} (Acc: {acc})")
        add_log("INFO", f"Status: {status}")

    # >>> LÓGICA DE RESPOSTA DO RESET <<<
    resposta = {"status": "success", "reset": False}
    if reset_agendado:
        resposta["reset"] = True
        reset_agendado = False # Desliga para não ficar resetando em loop
        print("\n🔄 AVISANDO ESP32 PARA REINICIAR...\n")

    return jsonify(resposta), 200

if __name__ == '__main__':
    # threaded=True permite lidar com o ESP32 e o navegador ao mesmo tempo
    # debug=False deixa o servidor mais rápido (menos peso no terminal)
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)