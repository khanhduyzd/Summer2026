import serial
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

# -----------------------------
# Serial / radio settings
# -----------------------------
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 9600

# -----------------------------
# API settings
# -----------------------------
API_KEY = "GardenSecret2026"

PEDESTRIAN_API_URL = "https://faridfarahmand.net/CEI/api_pedestrian.php"
SURVEY_API_URL = "https://faridfarahmand.net/CEI/api_survey.php"

# -----------------------------
# Dashboard files
# These files are read by dashboard.py
# -----------------------------
STATUS_FILE = "status.json"

# -----------------------------
# Acknowledgement password
# This is sent back after a valid message is received
# -----------------------------
ACK_PASSWORD = "LED"

# -----------------------------
# Transmitter health monitoring
# -----------------------------
# Transmitter should send one message every hour while awake.
EXPECTED_INTERVAL_SECONDS = 60 * 60

# Missing 3 messages in a row means possible problem.
MAX_MISSED_MESSAGES = 3

# We use 4 hours as the warning timeout:
# 1 expected message/hour + 3 missed messages = about 3 hours.
OFFLINE_TIMEOUT_SECONDS = EXPECTED_INTERVAL_SECONDS * MAX_MISSED_MESSAGES

last_awake_message_time = None
transmitter_awake = False
problem_notified = False
last_node_id = None
        
def update_dashboard_status(node_id, pedestrian_count, a, b, c, d, e, mode, battery_voltage, ack_status, upload_status):
    """
    Writes the latest radio and Raspberry Pi status to status.json.
    The dashboard.py webpage reads status.json and displays:
    - radio/node status
    - RPI status
    - latest data values
    - battery voltage
    - ACK status
    """

    if mode == 1:
        node_status = "awake"
    else:
        node_status = "sleep"

    status = {
        "radio": {
            "node_id": node_id,
            "node_status": node_status,
            "last_message_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "battery_voltage": battery_voltage,
            "ack_status": ack_status,
            "pedestrian_count": pedestrian_count,
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "e": e
        },
        "rpi": {
            "receiver_id": "RPI_01",
            "rpi_status": "online",
            "baud_rate": BAUD_RATE,
            "upload_status": upload_status,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    with open(STATUS_FILE, "w") as file:
        json.dump(status, file, indent=4)

def parse_combined_message(raw_message):
    """
    Expected message format:
        Gate_01, 09, A, B, C, D, E, mode, battery_code
    """
    raw_message = raw_message.strip()
    raw_message = raw_message.replace("\x00", "")

    # Remove optional Meshtastic prefix.
    if ":" in raw_message:
        raw_message = raw_message.split(":", 1)[1].strip()

    parts = [part.strip() for part in raw_message.split(",")]

    if len(parts) != 9:
        raise ValueError("Message must have 9 fields: node_id, pedestrian_count, a, b, c, d, e, mode, battery_code"  )

    node_id = parts[0]

    if not node_id:
        raise ValueError("node_id is empty")
    try:
        pedestrian_count = int(parts[1])
        a = int(parts[2])
        b = int(parts[3])
        c = int(parts[4])
        d = int(parts[5])
        e = int(parts[6])
        mode = int(parts[7])
        battery_code = int(parts[8])
        
    except ValueError:
        raise ValueError("pedestrian_count, survey values, mode, and battery_code must be integers")
        
    if mode not in [0, 1]:
        raise ValueError("mode must be 0 for sleep or 1 for awake")
        
    return node_id, pedestrian_count, a, b, c, d, e, mode, battery_code

def send_acknowledgement(serial_connection):
    #Sends the secret ACK password back to the transmitter.
    serial_connection.write((ACK_PASSWORD + "\n").encode("utf-8"))
    serial_connection.flush()
    print(f"ACK password sent")
    
def post_json(api_url, payload):
    #Sends JSON data to one API endpoint.

    json_data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        api_url,
        data=json_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.status
            response_body = response.read().decode("utf-8", errors="replace")

            if 200 <= status_code < 300:
                return True, status_code, response_body
            else:
               return False, status_code, response_body

    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        return False, error.code, response_body

    except urllib.error.URLError as error:
        return False, None, str(error)

def upload_pedestrian_count(node_id, pedestrian_count):
    """ Uploads pedestrian count. JSON format:
            "node_id": "Gate_01",
            "count": 9
    """
    payload = {
        "node_id": node_id,
        "count": pedestrian_count
    }
    return post_json(PEDESTRIAN_API_URL, payload)


def upload_survey_counts(node_id, a, b, c, d, e):
    """ Uploads survey option counts. JSON format:
            "node_id": "Gate_01",
            "a": 1,  "b": 2,   "c": 3,  "d": 4, "e": 5
    """
    payload = {"node_id": node_id,  "a": a,   "b": b, "c": c, "d": d,  "e": e }
    return post_json(SURVEY_API_URL, payload)

def notify_transmitter_problem(node_id):
    """
    This function notifies that the transmitter may have a problem.
    Right now, it only prints a warning.
    Later, this can be changed to send an email, text message,
    Slack message, or another API alert.
    """

    timestamp = datetime.now().isoformat(timespec="seconds")

    log_message("\n================ WARNING ================")
    log_message(f"[{timestamp}] Possible transmitter problem detected.")
    log_message(f"Node: {node_id}")
    log_message("Reason: No awake message received for too long.")
    log_message("=========================================\n")

def check_transmitter_health():
    """
    Checks if the transmitter has missed too many expected messages.
    If transmitter is sleeping, this function does nothing.
    If transmitter is awake and no message is received for too long,
    it prints a warning.
    """

    global last_awake_message_time
    global transmitter_awake
    global problem_notified
    global last_node_id

    if not transmitter_awake:
        return

    if last_awake_message_time is None:
        return

    elapsed_time = time.time() - last_awake_message_time

    if elapsed_time > OFFLINE_TIMEOUT_SECONDS and not problem_notified:
        notify_transmitter_problem(last_node_id)
        problem_notified = True

def process_message(serial_connection, raw_message):
    """ Handles one received radio message.
    Order:
        1. Receive message
        2. Check message format
        3. If valid, send the ACK password
        4. Update transmitter awake/sleep status
        5. Upload pedestrian count
        6. Upload survey counts.
    """
    
    global last_awake_message_time
    global transmitter_awake
    global problem_notified
    global last_node_id
    raw_message = raw_message.strip()

    # Ignore empty messages
    if not raw_message:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"\n[{timestamp}] Received message: {raw_message}")

    try:
        node_id, pedestrian_count, a, b, c, d, e, mode, battery_code = parse_combined_message(raw_message)
        battery_voltage = (1.024*4095)/battery_code
    except ValueError:
        # Wrong format, so do nothing and do not send ACK
        return

    # Send ACK only after the message format is valid
    send_acknowledgement(serial_connection)
    
    # Update transmitter awake/sleep status
    last_node_id = node_id
    if mode == 1:
        transmitter_awake = True
        last_awake_message_time = time.time()
        problem_notified = False
        log_message("Transmitter status: AWAKE")

    elif mode == 0:
        transmitter_awake = False
        last_awake_message_time = None
        problem_notified = False
        log_message("Transmitter status: SLEEP")
    
    # Upload pedestrian count
    ped_success, ped_status, ped_response = upload_pedestrian_count(
        node_id,
        pedestrian_count
    )

    if ped_success:
        log_message(f"Pedestrian upload successful.")
    else:
        log_message("Pedestrian upload failed.")
        log_message(f"HTTP status: {ped_status}")
        log_message(f"Server response/error: {ped_response}")
      
  # Upload survey counts
    survey_success, survey_status, survey_response = upload_survey_counts(node_id, a, b, c, d, e )

    if survey_success:
        log_message(f"Survey upload successful.")
    else:
        log_message("Survey upload failed.")
        log_message(f"HTTP status: {survey_status}")
        log_message(f"Server response/error: {survey_response}")
        
  # Decide upload status for dashboard
    if ped_success and survey_success:
        upload_status = "success"
    else:
        upload_status = "failed"

  # Update dashboard files
    update_dashboard_status(
        node_id,
        pedestrian_count,
        a,
        b,
        c,
        d,
        e,
        mode,
        battery_voltage,
        "sent",
        upload_status
    )
    
    log_message(f"Battery voltage recorded: {battery_voltage:.2f} V")
 

def main():
    serial_connection = serial.Serial(
        SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=0.1
    )

    buffer = ""
    last_data_time = None

    try:
        while True:
            if serial_connection.in_waiting > 0:
                data = serial_connection.read(serial_connection.in_waiting)

                text = data.decode("utf-8", errors="replace")
                text = text.replace("\r", "\n")

                buffer += text
                last_data_time = time.time()

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    process_message(serial_connection, line)

            # If message arrives without newline, process after 1 second
            if buffer.strip() and last_data_time is not None:
                if time.time() - last_data_time > 1.0:
                    process_message(serial_connection, buffer)
                    buffer = ""
                    last_data_time = None
                    
            # Check whether awake transmitter has missed too many messages
            check_transmitter_health()
            
            time.sleep(0.05)
          
    except KeyboardInterrupt:
        print("Program stopped by user.")

    finally:
        serial_connection.close()
        print("Serial port closed.")
if __name__ == "__main__":
    main()


