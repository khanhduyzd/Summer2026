from flask import Flask, render_template_string
from datetime import datetime
import json
import os

app = Flask(__name__)

# These files are created/updated by 1summer_project.py
STATUS_FILE = "status.json"

# Default values shown before the first valid radio message arrives
DEFAULT_STATUS = {
    "radio": {
        "node_id": "No message yet",
        "node_status": "unknown",
        "last_message_time": "No message yet",
        "battery_voltage": 0.0,
        "ack_status": "none",
        "pedestrian_count": 0,
        "a": 0,
        "b": 0,
        "c": 0,
        "d": 0,
        "e": 0
    },
    "rpi": {
        "receiver_id": "RPI_01",
        "rpi_status": "online",
        "serial_port": "/dev/serial0",
        "baud_rate": 9600,
        "upload_status": "none",
        "last_update": "No update yet"
    }
}

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>RPI Radio Dashboard</title>
    <meta http-equiv="refresh" content="5">

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f2f2f2;
            margin: 30px;
        }

        h1 {
            text-align: center;
            color: #222222;
        }

        .section {
            background: white;
            max-width: 900px;
            margin: 20px auto;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 0 8px #cccccc;
        }

        h2 {
            margin-top: 0;
            border-bottom: 2px solid #dddddd;
            padding-bottom: 8px;
            color: #333333;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            background: #eeeeee;
            width: 35%;
        }

        th, td {
            border: 1px solid #cccccc;
            padding: 10px;
        }

        .online, .awake, .success, .sent {
            color: green;
            font-weight: bold;
        }

        .sleep {
            color: yellow;
            font-weight: bold;
        }

        .down, .failed {
            color: red;
            font-weight: bold;
        }

        .unknown, .none {
            color: gray;
            font-weight: bold;
        }

    </style>
</head>

<body>
    <h1>RPI Radio Dashboard</h1>

    <div class="section">
        <h2> Node / Transmitter Status</h2>

        <table>
            <tr>
                <th>Node ID</th>
                <td>{{ status.radio.node_id }}</td>
            </tr>

            <tr>
                <th>Node Status</th>
                <td class="{{ status.radio.node_status }}">
                    {{ status.radio.node_status }}
                </td>
            </tr>

            <tr>
                <th>Last Message Time</th>
                <td>{{ status.radio.last_message_time }}</td>
            </tr>

            <tr>
                <th>Battery Voltage</th>
                <td>{{ "%.2f"|format(status.radio.battery_voltage) }} V</td>
            </tr>

            <tr>
                <th>ACK Status</th>
                <td class="{{ status.radio.ack_status }}">
                    {{ status.radio.ack_status }}
                </td>
            </tr>

            <tr>
                <th>Pedestrian Count</th>
                <td>{{ status.radio.pedestrian_count }}</td>
            </tr>

            <tr>
                <th>Survey Counts</th>
                <td>
                    A={{ status.radio.a }},
                    B={{ status.radio.b }},
                    C={{ status.radio.c }},
                    D={{ status.radio.d }},
                    E={{ status.radio.e }}
                </td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2> Raspberry Pi Status</h2>

        <table>
            <tr>
                <th>Receiver ID</th>
                <td>{{ status.rpi.receiver_id }}</td>
            </tr>

            <tr>
                <th>RPI Status</th>
                <td class="{{ status.rpi.rpi_status }}">
                    {{ status.rpi.rpi_status }}
                </td>
            </tr>

            <tr>
                <th>Serial Port</th>
                <td>{{ status.rpi.serial_port }}</td>
            </tr>

            <tr>
                <th>Baud Rate</th>
                <td>{{ status.rpi.baud_rate }}</td>
            </tr>

            <tr>
                <th>Database Upload Status</th>
                <td class="{{ status.rpi.upload_status }}">
                    {{ status.rpi.upload_status }}
                </td>
            </tr>

            <tr>
                <th>Last Dashboard Update</th>
                <td>{{ status.rpi.last_update }}</td>
            </tr>

            <tr>
                <th>Page Refresh Time</th>
                <td>{{ current_time }}</td>
            </tr>
        </table>
    </div>

</body>
</html>
"""


def read_status():
    """
    Reads status.json.
    If status.json does not exist yet or has an error,
    return default values.
    """

    if not os.path.exists(STATUS_FILE):
        return DEFAULT_STATUS

    try:
        with open(STATUS_FILE, "r") as file:
            return json.load(file)
  
        if "radio" not in status:
            status["radio"] = DEFAULT_STATUS["radio"]

        if "rpi" not in status:
            status["rpi"] = DEFAULT_STATUS["rpi"]

        # Fill in missing radio fields
        for key, value in DEFAULT_STATUS["radio"].items():
            if key not in status["radio"]:
                status["radio"][key] = value

        # Fill in missing rpi fields
        for key, value in DEFAULT_STATUS["rpi"].items():
            if key not in status["rpi"]:
                status["rpi"][key] = value

        return status

    except Exception:
        return DEFAULT_STATUS

@app.route("/")
def dashboard():
    status = read_status()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template_string(
        HTML_PAGE,
        status=status,
        current_time=current_time
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
